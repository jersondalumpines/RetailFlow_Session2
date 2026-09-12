from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "Datasets"
RESULTS_DIR = BASE_DIR / "results"
DOCS_DIR = BASE_DIR / "docs"

FILES = {
    "sales": DATA_DIR / "bm_sales.csv",
    "customers": DATA_DIR / "bm_customers.csv",
    "stores": DATA_DIR / "bm_stores.csv",
    "skus": DATA_DIR / "bm_skus.csv",
    "inventory": DATA_DIR / "bm_inventory.csv",
    "promotions": DATA_DIR / "bm_promotions.csv",
}

PARTITION_CANDIDATES = [
    "channel",
    "store_id",
    "category",
    "customer_city",
    "store_city",
    "loyalty_segment",
]

PARTITION_SETTINGS = [2, 4, 8]
BENCHMARK_REPEATS = 3
NUMERIC_TOLERANCE = 1e-6

def ensure_directories():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

def build_spark(app_name="RetailFlow Session 1"):
    from pyspark.sql import SparkSession
    return (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
