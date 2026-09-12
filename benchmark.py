import statistics
import json
import pandas as pd
import config as cfg
from load_and_join import build_working_dataset
from sequential_baseline import run_baseline
from parallel_compute import compute_parallel

def median_time(fn, repeats):
    values = []
    for _ in range(repeats):
        _, elapsed = fn()
        values.append(elapsed)
    return statistics.median(values), values

def main():
    cfg.ensure_directories()
    if not (cfg.RESULTS_DIR / "partition_strategy.json").exists():
        from partition_strategy import main as select
        select()

    key = json.loads((cfg.RESULTS_DIR / "partition_strategy.json").read_text())["selected_partition_key"]
    working = build_working_dataset(verbose=False)

    seq_median, seq_runs = median_time(
        lambda: run_baseline(working, key, verbose=False),
        cfg.BENCHMARK_REPEATS
    )

    rows = [{
        "configuration": "Sequential baseline",
        "partitions": 1,
        "median_seconds": seq_median,
        "all_runs_seconds": "|".join(f"{x:.6f}" for x in seq_runs),
        "speedup_vs_baseline": 1.0,
    }]

    spark = cfg.build_spark("RetailFlow Benchmark")
    try:
        for n in cfg.PARTITION_SETTINGS:
            values = []
            for _ in range(cfg.BENCHMARK_REPEATS):
                _, elapsed = compute_parallel(spark, key, n)
                values.append(elapsed)
            med = statistics.median(values)
            rows.append({
                "configuration": f"Parallel ({n})",
                "partitions": n,
                "median_seconds": med,
                "all_runs_seconds": "|".join(f"{x:.6f}" for x in values),
                "speedup_vs_baseline": seq_median / med if med else None,
            })
    finally:
        spark.stop()

    out_df = pd.DataFrame(rows)
    out = cfg.RESULTS_DIR / "session1_benchmark.csv"
    out_df.to_csv(out, index=False)
    print(out_df.to_string(index=False))
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
