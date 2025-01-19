import os
from pymongo import MongoClient
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, date_format, concat_ws, to_date
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DateType, TimestampType, DecimalType

# mongoDB connection settings
mongo_uri = "mongodb://root:root@mongodb:27017"
database = "subscribersDB"
collection = "subscribers"
auth = "?authSource=admin"

# connect to mongoDB
client = MongoClient(mongo_uri)

# check if the database & collection exists
if database in client.list_database_names():
    print(f"Database '{database}' exists...")
else:
    print(f"Database '{database}' does not exist...")
    db = client[database]
    db.create_collection(collection)
    print(f"Database '{database}' & collection '{collection}' created...")

# close the connection
client.close()

# mongoDB configuration
# using database: subscribersDB, collection: subscribers
mongo_conf = mongo_uri + "/" + database + "." + collection + auth

# create spark session
spark = SparkSession.builder \
    .appName("subs") \
    .master("spark://spark-master:7077") \
    .config("spark.mongodb.input.uri", mongo_conf) \
    .config("spark.mongodb.output.uri", mongo_conf) \
    .getOrCreate()

# log level to WARN to suppress INFO messages
spark.sparkContext.setLogLevel("WARN")

# define subscribers schema
subscribers_schema = StructType([
    StructField("subscriber_id", StringType(), True),
    StructField("activation_date", DateType(), True),
])

# load subscribers
subscribers = spark.read.csv("hdfs://namenode:9000/data/input_files/subscribers.csv",
                             schema=subscribers_schema,
                             header=False)

# dropping na values & formating date to yyyyMMdd
subscribers = subscribers.na.drop()
subscribers = subscribers.withColumn("activation_date", date_format(col("activation_date"), "yyyyMMdd"))
subscribers = subscribers.withColumn(
    "row_key",
    concat_ws("_",
              col("subscriber_id"),
              col("activation_date"))
)

# rearrange columns
subscribers_to_mongo = subscribers.select("row_key",
                                          col("subscriber_id").alias("sub_id"),
                                          col("activation_date").alias("act_dt"))

# save subscribers to mongoDB
# as mongoDB using date storage format is ISODate
# couldn't store act_id as DateType ISODate
# so stored as StringType() with yyyyMMdd
subscribers_to_mongo.write.format("mongo") \
    .mode("overwrite") \
    .option("spark.mongodb.output.uri", mongo_conf) \
    .save()

# define transactions schema
transactions_schema = StructType([
    StructField("timestamp", TimestampType(), True),
    StructField("subscriber_id", StringType(), True),
    StructField("amount", DecimalType(10, 4), True),
    StructField("channel", StringType(), True),
])

# load transactions
transactions = spark.read.csv("hdfs://namenode:9000/data/input_files/cvas_data_transactions.csv",
                              schema=transactions_schema,
                              header=False)

# drop na & row from transactions with value ***
transactions = transactions.na.drop()
transactions = transactions.where(col("channel") != "***")
# transactions = transactions.withColumn("timestamp", date_format(col("timestamp"), "yyyyMMdd"))

# get subscribers (from mongoDB)
subscribers_from_mongo = spark.read.format("mongo") \
    .option("spark.mongodb.input.uri", mongo_conf) \
    .load() \
    .select(col("sub_id"), col("act_dt").alias("activation_date"))

# join transactions with subscribers from mongoDB
result = transactions.join(
    subscribers_from_mongo,
    transactions.subscriber_id == subscribers_from_mongo.sub_id,
    "inner"
).select(
    col("timestamp"),
    col("subscriber_id").alias("sub_id"),
    col("amount"),
    col("channel"),
    col("activation_date")
)

# write parquet result to hdfs, data/output_files
result.write.format("parquet") \
    .mode("overwrite") \
    .save("hdfs://namenode:9000/data/output_files/parquet_transactions")

spark.stop()
print("Result parquet file persisted at 'hdfs://namenode:9000/data/output_files/parquet_transactions'...\nCompleted...")