# Databricks notebook source
# MAGIC %md
# MAGIC # 02 - Silver: cleaned, typed, de-duplicated

# COMMAND ----------
from pyspark.sql import functions as F
from pyspark.sql.window import Window

dbutils.widgets.text("storage_account", "")
dbutils.widgets.text("dataset", "sample_orders")

account = dbutils.widgets.get("storage_account")
dataset = dbutils.widgets.get("dataset")

bronze_path = f"abfss://bronze@{account}.dfs.core.windows.net/{dataset}"
silver_path = f"abfss://silver@{account}.dfs.core.windows.net/{dataset}"

# COMMAND ----------
bronze = spark.read.format("delta").load(bronze_path)

silver = (
    bronze
    .withColumn("order_id", F.col("order_id").cast("int"))
    .withColumn("quantity", F.col("quantity").cast("int"))
    .withColumn("unit_price", F.col("unit_price").cast("double"))
    .withColumn("order_date", F.to_date("order_date", "yyyy-MM-dd"))
    # Data quality: drop rows missing key fields or with invalid numbers
    .dropna(subset=["order_id", "customer_id", "quantity", "unit_price", "order_date"])
    .filter((F.col("quantity") > 0) & (F.col("unit_price") > 0))
    # De-duplicate on business key, keeping the most recently ingested record
    .withColumn(
        "_rn",
        F.row_number().over(
            Window.partitionBy("order_id").orderBy(F.col("_ingested_at").desc())
        ),
    )
    .filter("_rn = 1")
    .drop("_rn")
    .withColumn("total_amount", F.round(F.col("quantity") * F.col("unit_price"), 2))
)

# COMMAND ----------
silver.write.format("delta").mode("overwrite").save(silver_path)
print(f"Silver rows written: {silver.count()}")
