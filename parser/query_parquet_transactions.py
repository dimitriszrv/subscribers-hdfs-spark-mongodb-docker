from pyspark.sql import SparkSession

# create spark session
spark = SparkSession.builder \
    .appName("subs") \
    .master("spark://spark-master:7077") \
    .getOrCreate()

# log level to WARN to suppress INFO messages
spark.sparkContext.setLogLevel("WARN")

# load parquet_transactions file
df = spark.read.parquet("hdfs://namenode:9000/data/output_files/parquet_transactions")
df.createOrReplaceTempView("transactions")

# load the query from the file
with open("query.sql", "r") as file:
    query = file.read()

result = spark.sql(query)
result.show()