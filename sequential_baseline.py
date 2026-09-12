import time
import pandas as pd
import config as cfg
from load_and_join import build_working_dataset

def get_partition_key():
    import json
    path = cfg.RESULTS_DIR / "partition_strategy.json"
    if not path.exists():
        from partition_strategy import main
        main()
    return json.loads(path.read_text(encoding="utf-8"))["selected_partition_key"]

def run_baseline(df=None, partition_key=None, verbose=True):
    if df is None:
        df = build_working_dataset(verbose=False)
    if partition_key is None:
        partition_key = get_partition_key()

    start = time.perf_counter()
    result = (
        df.assign(**{partition_key: df[partition_key].fillna("MISSING")})
          .groupby(partition_key, dropna=False)
          .agg(
              transaction_count=("total_value", "size"),
              total_quantity=("quantity", "sum"),
              revenue_total=("total_value", "sum"),
              revenue_mean=("total_value", "mean"),
          )
          .reset_index()
          .sort_values(partition_key, kind="stable")
          .reset_index(drop=True)
    )
    elapsed = time.perf_counter() - start
    if verbose:
        print(f"Sequential groups: {len(result)}")
        print(f"Sequential aggregation time: {elapsed:.6f} seconds")
    return result, elapsed

def main():
    cfg.ensure_directories()
    result, elapsed = run_baseline()
    out = cfg.RESULTS_DIR / "sequential_results.csv"
    result.to_csv(out, index=False)
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
