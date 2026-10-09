# Databricks notebook source
# MAGIC %md
# MAGIC # 03 - Gold: business-level aggregates for BI

# COMMAND ----------
from pyspark.sql import functions as F

dbutils.widgets.text("storage_account", "")
dbutils.widgets.text("dataset", "sample_orders")

account = dbutils.widgets.get("storage_account")
dataset = dbutils.widgets.get("dataset")

silver_path = f"abfss://silver@{account}.dfs.core.windows.net/{dataset}"
gold_base = f"abfss://gold@{account}.dfs.core.windows.net"

silver = spark.read.format("delta").load(silver_path)

# COMMAND ----------
daily_sales = (
    silver.groupBy("order_date")
    .agg(
        F.countDistinct("order_id").alias("orders"),
        F.sum("quantity").alias("units_sold"),
        F.round(F.sum("total_amount"), 2).alias("revenue"),
    )
    .orderBy("order_date")
)

sales_by_category_country = (
    silver.groupBy("category", "country")
    .agg(
        F.countDistinct("order_id").alias("orders"),
        F.round(F.sum("total_amount"), 2).alias("revenue"),
    )
    .orderBy(F.desc("revenue"))
)

top_customers = (
    silver.groupBy("customer_id")
    .agg(
        F.countDistinct("order_id").alias("orders"),
        F.round(F.sum("total_amount"), 2).alias("lifetime_value"),
    )
    .orderBy(F.desc("lifetime_value"))
)

# COMMAND ----------
for name, df in {
    "daily_sales": daily_sales,
    "sales_by_category_country": sales_by_category_country,
    "top_customers": top_customers,
}.items():
    df.write.format("delta").mode("overwrite").save(f"{gold_base}/{name}")
    print(f"Gold table written: {name} ({df.count()} rows)")
