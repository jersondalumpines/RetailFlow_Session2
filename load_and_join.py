import pandas as pd
import config as cfg

DATE_COLUMNS = {
    "sales": ["date"],
    "customers": ["registration_date"],
    "stores": ["opening_date"],
    "inventory": ["last_restock_date", "snapshot_date"],
    "promotions": ["start_date", "end_date"],
}

def load_frames():
    frames = {}
    for name, path in cfg.FILES.items():
        df = pd.read_csv(path)
        for col in DATE_COLUMNS.get(name, []):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        frames[name] = df
    return frames

def validate_dimensions(frames):
    assert frames["customers"]["cust_id"].is_unique, "customers.cust_id must be unique"
    assert frames["stores"]["store_id"].is_unique, "stores.store_id must be unique"
    assert frames["skus"]["sku_id"].is_unique, "skus.sku_id must be unique"

def build_working_dataset(frames=None, verbose=True):
    if frames is None:
        frames = load_frames()
    validate_dimensions(frames)

    sales = frames["sales"].copy()
    customers = frames["customers"].rename(columns={
        "cust_id": "customer_id",
        "city": "customer_city"
    }).copy()
    stores = frames["stores"].rename(columns={
        "city": "store_city",
        "store_name": "store_name"
    }).copy()

    # customer_id has missing values in the source, so preserve all sales with a left join.
    before = len(sales)
    w = sales.merge(
        customers,
        on="customer_id",
        how="left",
        validate="many_to_one",
        indicator="_customer_merge"
    )
    assert len(w) == before, "Customer join changed sales row count unexpectedly"

    w = w.merge(
        stores,
        on="store_id",
        how="left",
        validate="many_to_one",
        indicator="_store_merge"
    )
    assert len(w) == before, "Store join changed sales row count unexpectedly"

    w = w.merge(
        frames["skus"],
        on="sku_id",
        how="left",
        validate="many_to_one",
        suffixes=("_sale", "_sku"),
        indicator="_sku_merge"
    )
    assert len(w) == before, "SKU join changed sales row count unexpectedly"

    if verbose:
        print(f"Sales rows before joins: {before:,}")
        print(f"Working dataset rows:   {len(w):,}")
        for c in ["_customer_merge", "_store_merge", "_sku_merge"]:
            print(f"{c}: {w[c].value_counts(dropna=False).to_dict()}")

    return w

def main():
    cfg.ensure_directories()
    w = build_working_dataset(verbose=True)
    out = cfg.RESULTS_DIR / "working_dataset.csv"
    w.to_csv(out, index=False)
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
