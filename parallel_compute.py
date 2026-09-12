import time
import config as cfg

def build_joined(spark):
    sales = spark.read.option("header", True).option("inferSchema", True).csv(str(cfg.FILES["sales"]))
    customers = spark.read.option("header", True).option("inferSchema", True).csv(str(cfg.FILES["customers"]))
    stores = spark.read.option("header", True).option("inferSchema", True).csv(str(cfg.FILES["stores"]))
    skus = spark.read.option("header", True).option("inferSchema", True).csv(str(cfg.FILES["skus"]))

    from pyspark.sql import functions as F

    customers = customers.withColumnRenamed("cust_id", "customer_id").withColumnRenamed("city", "customer_city")
    stores = stores.withColumnRenamed("city", "store_city")

    w = (
        sales.join(customers, on="customer_id", how="left")
             .join(stores, on="store_id", how="left")
             .join(skus, on="sku_id", how="left")
    )
    return w

def compute_parallel(spark, partition_key, num_partitions):
    from pyspark.sql import functions as F

    start = time.perf_counter()
    w = build_joined(spark)

    prepared = w.withColumn(
        partition_key,
        F.coalesce(F.col(partition_key).cast("string"), F.lit("MISSING"))
    )

    result = (
        prepared.repartition(num_partitions, partition_key)
        .groupBy(partition_key)
        .agg(
            F.count("*").alias("transaction_count"),
            F.sum("quantity").alias("total_quantity"),
            F.sum("total_value").alias("revenue_total"),
            F.avg("total_value").alias("revenue_mean"),
        )
        .orderBy(partition_key)
    )

    # Materialize the complete computation for fair timing.
    rows = result.collect()
    elapsed = time.perf_counter() - start
    return rows, elapsed

def main():
    import json
    cfg.ensure_directories()
    strategy = json.loads((cfg.RESULTS_DIR / "partition_strategy.json").read_text(encoding="utf-8"))
    key = strategy["selected_partition_key"]
    spark = cfg.build_spark()
    try:
        rows, elapsed = compute_parallel(spark, key, 4)
        print(f"Groups: {len(rows)}")
        print(f"Elapsed: {elapsed:.6f} seconds")
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
