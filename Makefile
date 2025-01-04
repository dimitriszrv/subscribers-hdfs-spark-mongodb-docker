# Makefile
# using Docker Compose version v2.30.3-desktop.1
# and Ubuntu 24.04

.PHONY: hdfs-setup spark-setup run-spark run-query build up remove stop logs

# build and start containers
build:
	docker compose up -d --build

# start containers
up:
	docker compose up -d

# remove containers
remove:
	docker compose down

# stop containers
stop:
	docker compose stop

# show logs
logs:
	docker compose logs -f

# setup hdfs directories
hdfs-setup:
	docker cp csv_files/cvas_data_transactions.csv namenode:cvas_data_transactions.csv
	docker cp csv_files/subscribers.csv namenode:subscribers.csv
	docker exec -it namenode bash -c "hdfs dfs -mkdir -p /data/input_files; hdfs dfs -mkdir -p /data/output_files; hdfs dfs -chmod -R 777 /data/output_files; hdfs dfs -put cvas_data_transactions.csv subscribers.csv /data/input_files/"

# setup spark environment
spark-setup:
	docker exec -it spark-master bash -c "pip install pymongo"

# run spark job
run-spark:
	docker cp parser/script.py spark-master:/opt/bitnami/spark/script.py
	docker exec -it spark-master bash -c "spark-submit --master spark://spark-master:7077 --packages org.mongodb.spark:mongo-spark-connector_2.12:3.0.1 /opt/bitnami/spark/script.py"

# run query
run-query:
	docker cp parser/query_parquet_transactions.py spark-master/:/opt/bitnami/spark/query_parquet_transactions.py
	docker cp parser/query.sql spark-master/:/opt/bitnami/spark/query.sql
	docker exec -it spark-master bash -c "spark-submit --master spark://spark-master:7077 /opt/bitnami/spark/query_parquet_transactions.py"