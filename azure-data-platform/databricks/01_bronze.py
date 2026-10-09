# Databricks notebook source
# MAGIC %md
# MAGIC # 01 - Bronze: raw landing -> Delta (as-is + audit columns)

# COMMAND ----------
from pyspark.sql import functions as F

dbutils.widgets.text("storage_account", "")
dbutils.widgets.text("dataset", "sample_orders")

account = dbutils.widgets.get("storage_account")
dataset = dbutils.widgets.get("dataset")

landing_path = f"abfss://landing@{account}.dfs.core.windows.net/{dataset}/*/*.csv"
bronze_path = f"abfss://bronze@{account}.dfs.core.windows.net/{dataset}"

# COMMAND ----------
# Read everything as strings: bronze keeps data exactly as received.
raw = (
    spark.read.option("header", True)
    .option("inferSchema", False)
    .csv(landing_path)
    .withColumn("_ingested_at", F.current_timestamp())
    .withColumn("_source_file", F.input_file_name())
)

# COMMAND ----------
raw.write.format("delta").mode("append").save(bronze_path)
print(f"Bronze rows written: {raw.count()}")
