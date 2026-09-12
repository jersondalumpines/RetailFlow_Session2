import pandas as pd
import config as cfg
from load_and_join import build_working_dataset
from partition_strategy import main as select_partition_key

def main():
    cfg.ensure_directories()
    key = select_partition_key()
    w = build_working_dataset(verbose=False)
    analysis = (
        w.assign(_partition=w[key].fillna("MISSING"))
         .groupby("_partition", dropna=False)
         .agg(
             row_count=("total_value", "size"),
             total_revenue=("total_value", "sum"),
             total_quantity=("quantity", "sum"),
             average_transaction_value=("total_value", "mean"),
         )
         .sort_values("row_count", ascending=False)
         .reset_index()
         .rename(columns={"_partition": key})
    )
    out = cfg.RESULTS_DIR / "partition_analysis.csv"
    analysis.to_csv(out, index=False)
    print(f"Selected partition key: {key}")
    print(analysis.head(20).to_string(index=False))
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
