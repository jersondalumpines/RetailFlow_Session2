import json
import pandas as pd
import config as cfg
from load_and_join import build_working_dataset

def evaluate_candidate(df, key):
    s = df[key].fillna("MISSING")
    counts = s.value_counts(dropna=False)
    mean = float(counts.mean())
    return {
        "key": key,
        "distinct_groups": int(len(counts)),
        "min_group_rows": int(counts.min()),
        "max_group_rows": int(counts.max()),
        "mean_group_rows": mean,
        "median_group_rows": float(counts.median()),
        "max_to_mean_skew": float(counts.max() / mean) if mean else None,
    }

def choose_partition_key(results):
    # Prefer a moderate number of groups with lower skew.
    candidates = [
        r for r in results
        if 2 <= r["distinct_groups"] <= 500 and r["mean_group_rows"] > 0
    ]
    if not candidates:
        return results[0]["key"]
    candidates.sort(key=lambda r: (r["max_to_mean_skew"], -r["distinct_groups"]))
    return candidates[0]["key"]

def main():
    cfg.ensure_directories()
    w = build_working_dataset(verbose=False)
    results = [evaluate_candidate(w, key) for key in cfg.PARTITION_CANDIDATES if key in w.columns]
    selected = choose_partition_key(results)
    payload = {"selected_partition_key": selected, "candidates": results}
    out = cfg.RESULTS_DIR / "partition_strategy.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return selected

if __name__ == "__main__":
    main()
