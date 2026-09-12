import json
import pandas as pd
import config as cfg

KEY_CANDIDATES = {
    "sales": ["date", "store_id", "sku_id", "customer_id"],
    "customers": ["cust_id"],
    "stores": ["store_id"],
    "skus": ["sku_id"],
    "inventory": ["store_id", "sku_id", "snapshot_date"],
    "promotions": ["promo_id"],
}

def profile_file(name, path):
    df = pd.read_csv(path)
    return {
        "file": path.name,
        "table": name,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": df.columns.tolist(),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "null_counts": {c: int(v) for c, v in df.isna().sum().items()},
        "distinct_counts": {c: int(df[c].nunique(dropna=True)) for c in df.columns},
        "candidate_key_unique": {
            c: bool(df[c].is_unique) for c in KEY_CANDIDATES.get(name, []) if c in df.columns
        },
    }

def main():
    cfg.ensure_directories()
    report = {name: profile_file(name, path) for name, path in cfg.FILES.items()}
    out = cfg.RESULTS_DIR / "file_profile.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved: {out}")
    for name, info in report.items():
        print(f"{name:12} rows={info['rows']:,} columns={info['columns']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
