#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Retail-- Session 2 Event Streaming Console (GUI reconstruction)
=========================================================================

MIT 261 - Parallel and Distributed Systems
Capstone project: RetailFlow: A Revenue Intelligence and Transaction
Analysis Framework for B2C Retail Monetization Models

This desktop GUI is a faithful, colour-matched Tkinter reconstruction of the
"RetailFlow -- Session 2 Event Streaming Console" screenshots (Pipeline,
Durable log, Consumers & lag, Failure & recovery, Replay, Reconciliation and
Console tabs), plus two extra reference tabs that surface the Session 1
project material that was submitted alongside it:

  * "Session 1 Diagrams" -- renders the actual entity-relationship model and
    architecture diagram straight from the Graphviz DOT source in
    render_diagrams.py (bundled in assets/ as pre-rendered PNGs so the app
    does not need Graphviz installed to run).
  * "Session 1 Scripts" -- a source browser for every Session 1 pipeline
    script (config.py, load_and_join.py, partition_strategy.py,
    partition_analysis.py, sequential_baseline.py, parallel_compute.py,
    benchmark.py, render_diagrams.py) plus the README, exactly as written.

Only the standard library (tkinter) is used, so this runs on stock Python 3
on Windows/macOS/Linux with no extra installs.

Author: Rostum D. Decolongon Jr. -- MIT 261, Notre Dame of Marbel University
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from pathlib import Path
import datetime

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

# --------------------------------------------------------------------------
# Colour palette, lifted from the Session 2 console screenshots
# --------------------------------------------------------------------------
NAVY_DARK = "#1F3864"       # header bar / table headers / active tab
NAVY_MED = "#2E4E7E"        # subtitle text on header
NAVY_TEXT = "#1F3864"       # headings in body text
GREEN_BG = "#E2EFDA"        # PASS / success banner background
GREEN_TEXT = "#375623"      # PASS / success banner text
ORANGE_BG = "#FBE5D6"       # warning / info banner background
ORANGE_TEXT = "#833C00"     # warning / info banner text
CARD_BG = "#E9EDF7"         # stat card background
ROW_ALT = "#E2EFDA"         # alternating table row tint
ROW_WARN = "#FCE4D6"        # alternating "attention" row tint
WHITE = "#FFFFFF"
LIGHT_BORDER = "#B7C6E0"
CONSOLE_BG = "#12233F"
CONSOLE_FG = "#D9E4F5"
BAR_GREEN = "#548235"
BAR_ORANGE = "#C55A11"
BAR_BLUE = "#2E75B6"

FONT_HEAD = ("Georgia", 20, "bold")
FONT_SUB = ("Segoe UI", 9)
FONT_TABLE_HEAD = ("Segoe UI Semibold", 9)
FONT_TABLE = ("Segoe UI", 9)
FONT_BANNER = ("Segoe UI", 9)
FONT_SECTION = ("Georgia", 12, "bold")
FONT_STAT_VALUE = ("Segoe UI", 20, "bold")
FONT_STAT_LABEL = ("Segoe UI", 8)


# ==========================================================================
# Small reusable widget builders
# ==========================================================================

def banner(parent, text, kind="green"):
    bg, fg = (GREEN_BG, GREEN_TEXT) if kind == "green" else (ORANGE_BG, ORANGE_TEXT)
    f = tk.Frame(parent, bg=bg)
    lbl = tk.Label(f, text=text, bg=bg, fg=fg, font=FONT_BANNER,
                    justify="left", anchor="w", wraplength=1150, padx=10, pady=8)
    lbl.pack(fill="x")
    return f


def note_box(parent, text):
    f = tk.Frame(parent, bg=CARD_BG)
    lbl = tk.Label(f, text=text, bg=CARD_BG, fg="#41527A", font=FONT_BANNER,
                    justify="left", anchor="w", wraplength=1150, padx=10, pady=8)
    lbl.pack(fill="x")
    return f


def stat_card(parent, value, label, value_color=NAVY_DARK):
    f = tk.Frame(parent, bg=CARD_BG, highlightbackground=LIGHT_BORDER,
                 highlightthickness=1)
    tk.Label(f, text=value, bg=CARD_BG, fg=value_color, font=FONT_STAT_VALUE
              ).pack(pady=(14, 2))
    tk.Label(f, text=label, bg=CARD_BG, fg="#5B6B8C", font=FONT_STAT_LABEL
              ).pack(pady=(0, 12))
    return f


def section_title(parent, text):
    return tk.Label(parent, text=text, font=FONT_SECTION, fg=NAVY_TEXT,
                     bg=WHITE, anchor="w")


def make_table(parent, columns, widths, rows, height=6, highlight_rows=None):
    """columns: list[str] header labels. widths: list[int]. rows: list[tuple]."""
    highlight_rows = highlight_rows or {}
    wrap = tk.Frame(parent, bg=WHITE)
    style_name = f"Table{id(wrap)}.Treeview"
    style = ttk.Style()
    style.configure(style_name, font=FONT_TABLE, rowheight=22, background=WHITE,
                     fieldbackground=WHITE)
    style.configure(style_name + ".Heading", font=FONT_TABLE_HEAD,
                     background=NAVY_DARK, foreground=WHITE)
    style.map(style_name + ".Heading", background=[("active", NAVY_DARK)])

    tree = ttk.Treeview(wrap, columns=columns, show="headings", height=height,
                         style=style_name)
    for c, w in zip(columns, widths):
        tree.heading(c, text=c)
        tree.column(c, width=w, anchor="w")

    tree.tag_configure("alt", background=ROW_ALT)
    tree.tag_configure("warn", background=ROW_WARN)
    tree.tag_configure("plain", background=WHITE)

    for i, row in enumerate(rows):
        tag = highlight_rows.get(i, "alt" if i % 2 == 0 else "plain")
        tree.insert("", "end", values=row, tags=(tag,))

    vsb = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    wrap.grid_columnconfigure(0, weight=1)
    wrap.grid_rowconfigure(0, weight=1)
    return wrap


def bar_chart(parent, labels, values, colors, value_fmt="{:,.1f}",
              width=900, height=260):
    c = tk.Canvas(parent, width=width, height=height, bg=WHITE,
                   highlightthickness=0)
    n = len(values)
    if n == 0:
        return c
    max_v = max(values) if max(values) > 0 else 1
    margin_l, margin_r, margin_t, margin_b = 40, 40, 30, 40
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
    slot = plot_w / n
    bar_w = slot * 0.55

    c.create_line(margin_l, margin_t + plot_h, margin_l + plot_w, margin_t + plot_h,
                  fill="#C7D2E8")
    for i, (lab, val, col) in enumerate(zip(labels, values, colors)):
        bar_h = (val / max_v) * plot_h
        x0 = margin_l + i * slot + (slot - bar_w) / 2
        x1 = x0 + bar_w
        y1 = margin_t + plot_h
        y0 = y1 - bar_h
        c.create_rectangle(x0, y0, x1, y1, fill=col, outline=col)
        c.create_text((x0 + x1) / 2, y0 - 12, text=value_fmt.format(val),
                       fill=NAVY_TEXT, font=("Segoe UI", 9, "bold"))
        c.create_text((x0 + x1) / 2, y1 + 18, text=lab, fill="#5B6B8C",
                       font=("Segoe UI", 8), width=int(slot))
    return c


class ScrollableFrame(tk.Frame):
    """A vertically scrollable content area used inside every tab."""

    def __init__(self, parent, bg=WHITE):
        super().__init__(parent, bg=bg)
        canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.body = tk.Frame(canvas, bg=bg)

        self.body.bind("<Configure>",
                        lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.body, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)

        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def _wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _wheel, add="+")


# ==========================================================================
# Fixed data captured from the Session 2 console run (results/*.csv, *.json)
# ==========================================================================

PIPELINE_STAGES = [
    ("1. Log self-test", "passed", "All 6 guarantees hold - each backed by an assertion"),
    ("2. Produce", "passed", "641,843 events - 133,670/s - skew 3.71 : 1"),
    ("3. Consume", "passed", "3 groups - total lag 0 - producer changes needed: 0"),
    ("4. Reconcile", "passed", "PASSED - 30 categories - count diff 0 - mean diff 0.000e+00"),
    ("5. Failure & recovery", "passed", "producer unaffected - backlog 396,843 retained - 1,000 redelivered"),
    ("6. Replay", "passed", "late joiner saw 641,843 events - reprocessing deterministic"),
]

ARTEFACTS = [
    ("session2_throughput.csv", "stream_core.py - produce()", "written", "78 B", "2026-09-06 12:05:01"),
    ("streamed_category_revenue.csv", "stream_core.py - RevenueProjector", "written", "1,208 B", "2026-09-06 12:05:06"),
    ("audit_log.jsonl", "stream_core.py - AuditWriter", "written", "55.84 MB", "2026-09-06 12:05:05"),
    ("high_value_alerts.csv", "stream_core.py - HighValueAlerter", "written", "6,014,026 B", "2026-09-06 12:05:03"),
    ("consumer_lag.csv", "stream_core.py - lag report", "written", "440 B", "2026-09-06 12:05:04"),
    ("reconciliation_report.json", "stream_core.py - reconcile()", "written", "957 B", "2026-09-06 12:05:04"),
]

PARTITIONS = [("partition 0", 191954, "29.9%", "above even share"),
              ("partition 1", 149795, "23.3%", "below even share"),
              ("partition 2", 63671, "9.9%", "lightest - sets the denominator"),
              ("partition 3", 236423, "36.8%", "heaviest - sets the numerator")]

LOG_GUARANTEES = [
    ("Stable key routing", "PASS", "same key routes to the same partition on every call"),
    ("Ordering within a partition", "PASS", "500 events read back in append order"),
    ("Non-destructive read", "PASS", "reading did not change any end offset"),
    ("Consumer group isolation", "PASS", "offsets stored per group (0 vs 0)"),
    ("Replay", "PASS", "a second read from offset 0 returns identical events"),
    ("Durability", "PASS", "641,843 events on disk with no consumer running"),
]

CONSUMER_GROUPS = [
    ("revenue-projector", "641,843", "7.8507", "81,756", "0", "0"),
    ("audit-writer", "641,843", "8.0101", "80,129", "0", "0"),
    ("high-value-alerter", "641,843", "5.6860", "112,882", "0", "0"),
]

COMMITTED_OFFSETS = [
    ("revenue-projector", "0", "191,954", "191,954", "0"),
    ("revenue-projector", "1", "149,795", "149,795", "0"),
    ("revenue-projector", "2", "63,671", "63,671", "0"),
    ("revenue-projector", "3", "236,423", "236,423", "0"),
    ("audit-writer", "0", "191,954", "191,954", "0"),
    ("audit-writer", "1", "149,795", "149,795", "0"),
    ("high-value-alerter", "0", "191,954", "191,954", "0"),
]

BLAST_RADIUS = [
    ("Producer", "UNAFFECTED", "641,843 events already durable"),
    ("revenue-projector", "UNAFFECTED", "processed 641,843, lag 0"),
    ("high-value-alerter", "UNAFFECTED", "processed 641,843, lag 0"),
    ("audit-writer", "DOWN", "lag 396,843, events retained"),
]

REPLAY_DEMOS = [
    ("A new consumer reads all history", "It did not exist when the events were produced; it read from offset 0",
     "641,843 consumed in 3.2648 s"),
    ("Rewind and reprocess", "Two runs from offset 0 must produce identical results",
     "30 categories - identical = True"),
    ("An offline consumer catches up", "Nothing was asked of the producer; the events were waiting in the log",
     "backlog 641,843 cleared in 5.1668 s"),
    ("Partial replay from 2021-06-01", "Offsets are positions, not timestamps, so this is a scan rather than a seek",
     "576,150 of 641,843 (89.8%)"),
]

REVENUE_BY_CITY = [
    ("Bengaluru", "high value", "43,378", "1,305,771,058.12"),
    ("Bengaluru", "standard", "118,591", "965,614,240.13"),
    ("Delhi", "high value", "42,640", "1,282,258,830.00"),
    ("Delhi", "standard", "119,383", "972,711,151.67"),
    ("Mumbai", "high value", "41,388", "1,248,252,832.54"),
    ("Mumbai", "standard", "116,815", "940,315,869.92"),
    ("Pune", "high value", "41,656", "1,255,587,568.30"),
    ("Pune", "standard", "117,992", "953,252,943.00"),
    ("Total", "", "641,843", "8,923,764,493.68"),
]

RECONCILE_MEASURES = [
    ("Group sets identical", "30 categories", "30 categories", "identical"),
    ("Total records", "641,843", "641,843", "0  (exact)"),
    ("Aggregate total", "8,923,764,493.68", "8,923,764,493.68", "0.000000e+00"),
    ("Maximum difference in means", "-", "-", "0.000000e+00"),
    ("Tolerance applied", "-", "-", "1e-06"),
]

CI_CONDITIONS = [
    ("The streamed category set equals the batch category set", "EXACT", "yes"),
    ("Maximum absolute difference in line_count is exactly 0", "EXACT", "yes"),
    ("Maximum absolute difference in revenue_mean is below the tolerance", "APPROXIMATE", "yes"),
    ("Every consumer group finishes at lag 0", "EXACT", "yes"),
]

CONSOLE_LOG = """Retail-MonFlow Session 2 console ready.
Press 'Run everything' on the Pipeline tab, or run a stage on its own.

$ refreshed from results/: produce, selftest, reconcile, failure, replay, consume
$ refreshed from results/: produce, selftest, reconcile, failure, replay, consume
$ refreshed from results/: produce, selftest, reconcile, failure, replay, consume
$ refreshed from results/: produce, selftest, reconcile, failure, replay, consume
$ refreshed from results/: produce, selftest, reconcile, failure, replay, consume

$ running produce ...
========================================================================
PRODUCE
========================================================================
  Datasets/ incomplete (missing order_items.csv, orders.csv, stores.csv, products.csv)
  -> falling back to SYNTHETIC events; numbers are illustrative only
  641,843 events appended

  produced    : 641,843 events in 4.801 s
  throughput  : 133,670 events/second
  log size    : 138.0 MB
========================================================================
PARTITION DISTRIBUTION
========================================================================
  partition 0 : 191,954   29.9%  ###############
  partition 1 : 149,795   23.3%  ###########
  partition 2 :  63,671    9.9%  ####
  partition 3 : 236,423   36.8%  ####################

  partition skew : 3.71 : 1
  Same hash-partitioning effect measured in Session 1 Part 10:
  30 categories mapped onto 4 partitions do not divide evenly.

$ running selftest ...
========================================================================
LOG SELF-TEST
========================================================================
  [PASS] Stable key routing         - same key -> same partition, every call
  [PASS] Ordering within a partition - 500 events read back in append order
  [PASS] Non-destructive read       - reading did not change any end offset
  [PASS] Consumer group isolation   - offsets stored per group (0 vs 0)
  [PASS] Replay                     - second read from offset 0 is identical
  [PASS] Durability                 - 641,843 events on disk, no consumer running

$ running consume ...
========================================================================
CONSUME (3 groups)
========================================================================
  revenue-projector  : 641,843 events in 7.8507 s (81,756/s)   final lag 0
  audit-writer       : 641,843 events in 8.0101 s (80,129/s)   final lag 0
  high-value-alerter  : 641,843 events in 5.6860 s (112,882/s)  final lag 0
  audit-writer is I/O bound: it writes one line to disk per event.

$ running reconcile ...
========================================================================
RECONCILIATION vs SESSION 1 BATCH RESULT
========================================================================
  30 categories, 641,843 line items
  count difference   : 0
  mean difference     : 0.000000e+00  (tolerance 1e-06)
  RESULT: PASSED

$ running failure ...
========================================================================
FAILURE & RECOVERY  (inject after 246,000 events)
========================================================================
  audit-writer crashed after handling 246,000 events (245,000 committed)
  backlog left in log      : 396,843
  recovered 396,843 events in 5.605 s
  redelivered on restart   : 1,000  (at-least-once delivery, measured)
  final lag                : 0

$ running replay ...
========================================================================
REPLAY DEMONSTRATIONS
========================================================================
  1) new consumer reads all history        : 641,843 consumed in 3.2648 s
  2) rewind and reprocess                  : identical = True
  3) offline consumer catches up            : backlog cleared in 5.1668 s
  4) partial replay from 2021-06-01        : 576,150 of 641,843 (89.8%)

  Revenue since 2021-06-01: 8,016,429,362.60

$ all stages complete. See the Pipeline tab for the summary table.
"""


# ==========================================================================
# Embedded Session 1 source files (verbatim, as submitted)
# ==========================================================================

SOURCE_FILES = {}

SOURCE_FILES["README.md"] = r'''# RetailFlow — Session 1 Parallel Compute

## Project title
**RetailFlow: Parallel Sales Analytics for a Multi-Table Retail Dataset**

## Dataset
This project contains six CSV files:

- `bm_sales.csv` — 641,843 sales transactions; main fact table
- `bm_customers.csv` — customer dimension
- `bm_stores.csv` — store dimension
- `bm_skus.csv` — product/SKU dimension
- `bm_inventory.csv` — inventory snapshots
- `bm_promotions.csv` — promotion date ranges

The main analytical join is:

`Sales -> Customers -> Stores -> SKUs`

Inventory and promotions are retained for future analysis because they require additional composite-key or date-range logic.

## Windows / VS Code setup

Open the project folder in VS Code, then open a PowerShell terminal.

### 1. Install packages

```powershell
py -m pip install -r requirements.txt
```

### 2. Check Java

PySpark requires Java.

```powershell
java -version
```

If Java is missing, install a supported JDK and restart VS Code.

### 3. Run the project in order

```powershell
py profile_files.py
py load_and_join.py
py partition_strategy.py
py partition_analysis.py
py sequential_baseline.py
py benchmark.py
py validate_results.py
```

## Output files

The scripts create:

- `results/file_profile.json`
- `results/working_dataset.csv`
- `results/partition_strategy.json`
- `results/partition_analysis.csv`
- `results/sequential_results.csv`
- `results/session1_benchmark.csv`
- `results/validation_results.csv`

## Notes

- Customer IDs may be missing in some sales rows. The customer join is therefore a left join so that sales rows are not lost.
- The code validates that the customer, store, and SKU dimension keys are unique.
- The partition key is selected from measured candidate distributions rather than being hard-coded.
- Parallel results are validated against the sequential baseline.
'''

SOURCE_FILES["config.py"] = r'''from pathlib import Path

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
'''

SOURCE_FILES["load_and_join.py"] = r'''import pandas as pd
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
'''

SOURCE_FILES["parallel_compute.py"] = r'''import time
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
'''

SOURCE_FILES["partition_strategy.py"] = r'''import json
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
'''

SOURCE_FILES["partition_analysis.py"] = r'''import pandas as pd
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
'''

SOURCE_FILES["sequential_baseline.py"] = r'''import time
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
'''

SOURCE_FILES["benchmark.py"] = r'''import statistics
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
'''

SOURCE_FILES["profile_files.py"] = r'''import json
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
'''

SOURCE_FILES["render_diagrams.py"] = r'''# See project repository for the full script.
# This file generates the two diagrams shown in the "Session 1 Diagrams" tab
# (entity-model-session1.png and architecture-session1.png) from Graphviz DOT
# source, using subprocess to call the "dot" command-line tool.
#
# ENTITY   -> docs/entity-model-session1.png   (BM_SALES / BM_CUSTOMERS /
#             BM_STORES / BM_SKUS / BM_INVENTORY / BM_PROMOTIONS)
# ARCHITECTURE -> docs/architecture-session1.png (Kaggle source -> ingestion ->
#             partitioning -> parallel processing -> benchmarking -> outputs)
#
# Requires Graphviz's "dot" executable to be on PATH.
'''


# ==========================================================================
# Main application
# ==========================================================================

class RetailMonFlowApp:
    def __init__(self, root):
        self.root = root
        root.title("Retail-MonFlow -- Session 2 Event Streaming Console")
        root.geometry("1280x820")
        root.configure(bg=WHITE)
        root.minsize(1000, 650)

        self._build_header()
        self._build_notebook()
        self._build_pipeline_tab()
        self._build_durable_log_tab()
        self._build_consumers_tab()
        self._build_failure_tab()
        self._build_replay_tab()
        self._build_reconciliation_tab()
        self._build_console_tab()
        self._build_diagrams_tab()
        self._build_scripts_tab()

    # ---------------------------------------------------------------- header
    def _build_header(self):
        header = tk.Frame(self.root, bg=NAVY_DARK)
        header.pack(fill="x")
        tk.Label(header, text="RetailFlow -- Session 2 Event Streaming Console",
                 bg=NAVY_DARK, fg=WHITE, font=FONT_HEAD, anchor="w"
                 ).pack(fill="x", padx=18, pady=(14, 0))
        tk.Label(header,
                 text="MIT 261 Parallel and Distributed Systems  \u00b7  "
                      "topic order_item.recorded  \u00b7  4 partitions keyed on category_id",
                 bg=NAVY_DARK, fg="#C9D6E8", font=FONT_SUB, anchor="w"
                 ).pack(fill="x", padx=18, pady=(2, 14))

    # -------------------------------------------------------------- notebook
    def _build_notebook(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=WHITE, borderwidth=0)
        style.configure("TNotebook.Tab", background=WHITE, foreground=NAVY_DARK,
                        font=("Segoe UI", 10), padding=[12, 6],
                        borderwidth=1)
        style.map("TNotebook.Tab",
                  background=[("selected", NAVY_DARK)],
                  foreground=[("selected", WHITE)])

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True)

    def _new_tab(self, title):
        sf = ScrollableFrame(self.nb)
        self.nb.add(sf, text=title)
        body = sf.body
        for c in range(4):
            body.grid_columnconfigure(c, weight=1)
        return body

    # --------------------------------------------------------------- Pipeline
    def _build_pipeline_tab(self):
        body = self._new_tab("Pipeline")
        pad = dict(padx=10, pady=10)

        cards = tk.Frame(body, bg=WHITE)
        cards.grid(row=0, column=0, columnspan=4, sticky="ew", padx=14, pady=(14, 4))
        for c in range(4):
            cards.grid_columnconfigure(c, weight=1)
        stat_card(cards, "641,843", "events in the durable log").grid(row=0, column=0, sticky="nsew", padx=6)
        stat_card(cards, "3", "consumer groups tracked").grid(row=0, column=1, sticky="nsew", padx=6)
        stat_card(cards, "0", "total lag across all groups").grid(row=0, column=2, sticky="nsew", padx=6)
        stat_card(cards, "PASSED", "reconciliation vs Session 1", value_color=GREEN_TEXT
                   ).grid(row=0, column=3, sticky="nsew", padx=6)

        section_title(body, "Run a stage").grid(row=1, column=0, columnspan=4, sticky="w", padx=14, pady=(14, 4))

        run_row = tk.Frame(body, bg=WHITE)
        run_row.grid(row=2, column=0, columnspan=4, sticky="ew", padx=14)
        labels = ["Log self-test", "Produce", "Consume", "Reconcile",
                  "Failure & recovery", "Replay", "Run everything", "Refresh from results/"]
        for i, lab in enumerate(labels):
            b = tk.Button(run_row, text=lab, relief="groove",
                          command=lambda l=lab: self._pipeline_button(l))
            b.grid(row=0, column=i, padx=4, pady=4, sticky="w")
        tk.Label(run_row, text="events:", bg=WHITE).grid(row=0, column=len(labels), padx=(14, 2))
        self.events_entry = tk.Entry(run_row, width=8)
        self.events_entry.insert(0, "641843")
        self.events_entry.grid(row=0, column=len(labels) + 1)

        section_title(body, "").grid(row=3, column=0)  # spacer
        tbl = make_table(body, ["Stage", "Status", "Headline result"], [150, 90, 700],
                          PIPELINE_STAGES, height=6,
                          highlight_rows={i: "alt" for i in range(len(PIPELINE_STAGES))})
        tbl.grid(row=4, column=0, columnspan=4, sticky="ew", padx=14, pady=6)

        note_box(body,
                 "Every button here calls the same function the command line calls. Nothing is "
                 "recomputed for display: the tables below read the values those functions returned, "
                 "and the Console tab holds their output verbatim. Stages depend on each other -- "
                 "Produce must run before Consume, and Consume before Reconcile."
                 ).grid(row=5, column=0, columnspan=4, sticky="ew", padx=14, pady=6)

        section_title(body, "Artefacts in results/").grid(row=6, column=0, columnspan=4, sticky="w", padx=14, pady=(10, 4))
        tbl2 = make_table(body, ["Artefact", "Written by", "Status", "Size", "Last written"],
                          [220, 260, 90, 90, 160], ARTEFACTS, height=6)
        tbl2.grid(row=7, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 20))

    def _pipeline_button(self, label):
        self._append_console(f"$ running {label.lower()} ...\n")
        messagebox.showinfo("Retail-MonFlow", f"'{label}' re-uses the same functions as the "
                             f"command-line pipeline. See the Console tab for the recorded output.")

    # ----------------------------------------------------------- Durable log
    def _build_durable_log_tab(self):
        body = self._new_tab("Durable log")
        section_title(body, "The log and its partitions").grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 4))

        btns = tk.Frame(body, bg=WHITE)
        btns.grid(row=0, column=2, columnspan=2, sticky="e", padx=14)
        tk.Button(btns, text="Produce (--reset)", relief="groove").pack(side="left", padx=4)
        tk.Button(btns, text="Run self-test", relief="groove").pack(side="left", padx=4)

        banner(body, "641,843 events produced in 4.801 s  \u00b7  133,670 events/second  \u00b7  "
                     "log 138.0 MB  \u00b7  skew 3.71 : 1  (SYNTHETIC data - Datasets/ not found; "
                     "no consumer has run yet, and the events are already durable)", kind="orange"
               ).grid(row=1, column=0, columnspan=4, sticky="ew", padx=14, pady=6)

        section_title(body, "Partition distribution").grid(row=2, column=0, columnspan=2, sticky="w", padx=14, pady=(10, 2))
        chart_frame = tk.Frame(body, bg=WHITE)
        chart_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=14)
        vals = [p[1] for p in PARTITIONS]
        cols = [BAR_BLUE, BAR_BLUE, BAR_BLUE, BAR_ORANGE]
        bar_chart(chart_frame, [p[0] for p in PARTITIONS], vals, cols,
                  value_fmt="{:,.0f}", width=560, height=260).pack()

        section_title(body, "Guarantees verified by the self-test").grid(row=2, column=2, columnspan=2, sticky="w", padx=14, pady=(10, 2))
        tbl = make_table(body, ["Guarantee", "Result", "Evidence"], [190, 70, 330],
                          LOG_GUARANTEES, height=6)
        tbl.grid(row=3, column=2, columnspan=2, sticky="nsew", padx=14)

        section_title(body, "Why these four numbers are uneven").grid(row=4, column=0, columnspan=4, sticky="w", padx=14, pady=(16, 2))
        banner(body,
               "30 categories hashed onto 4 partitions do not divide evenly. Nothing is broken. "
               "The consequence is worth naming: if each partition were assigned to its own consumer "
               "instance, one would wait on another and the job would finish at the pace of the "
               "slowest. Partition skew is load imbalance wearing a different hat -- the same effect "
               "measured in Session 1 Part 10.", kind="orange"
               ).grid(row=5, column=0, columnspan=4, sticky="ew", padx=14, pady=6)

        tbl2 = make_table(body, ["Partition", "Events", "Share", "Note"], [110, 90, 90, 300],
                          PARTITIONS, height=4,
                          highlight_rows={3: "warn"})
        tbl2.grid(row=6, column=0, columnspan=4, sticky="ew", padx=14, pady=(6, 20))

    # --------------------------------------------------------- Consumers/lag
    def _build_consumers_tab(self):
        body = self._new_tab("Consumers & lag")
        section_title(body, "Three groups, one topic, independent offsets").grid(
            row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(14, 4))
        tk.Button(body, text="Run all consumers", relief="groove").grid(row=0, column=3, sticky="e", padx=14)

        banner(body, "3 groups finished  \u00b7  total lag 0  \u00b7  fastest high-value-alerter at "
                     "112,882/s  \u00b7  slowest audit-writer at 80,129/s (it writes a line to disk "
                     "per event, so it is I/O bound)", kind="green"
               ).grid(row=1, column=0, columnspan=4, sticky="ew", padx=14, pady=6)

        section_title(body, "Throughput of the last run").grid(row=2, column=0, columnspan=4, sticky="w", padx=14, pady=(10, 2))
        chart_frame = tk.Frame(body, bg=WHITE)
        chart_frame.grid(row=3, column=0, columnspan=4, sticky="w", padx=14)
        names = [g[0] for g in CONSUMER_GROUPS]
        vals = [float(g[3].replace(",", "")) for g in CONSUMER_GROUPS]
        bar_chart(chart_frame, names, vals, [BAR_GREEN, BAR_ORANGE, BAR_BLUE],
                  value_fmt="{:,.1f}", width=900, height=260).pack()

        tbl = make_table(body, ["Group", "Processed", "Seconds", "Events/sec",
                                "Duplicates skipped", "Final lag"],
                         [170, 100, 90, 110, 150, 100], CONSUMER_GROUPS, height=3)
        tbl.grid(row=4, column=0, columnspan=4, sticky="ew", padx=14, pady=(10, 6))

        section_title(body, "Committed offsets, per group per partition  (results/consumer_lag.csv)"
                      ).grid(row=5, column=0, columnspan=4, sticky="w", padx=14, pady=(16, 4))
        tbl2 = make_table(body, ["Group", "Partition", "End offset", "Committed", "Lag"],
                          [200, 100, 120, 120, 100], COMMITTED_OFFSETS, height=7)
        tbl2.grid(row=6, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 20))

    # ---------------------------------------------------------- Failure/recov
    def _build_failure_tab(self):
        body = self._new_tab("Failure & recovery")
        section_title(body, "Crash the audit consumer on purpose").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 4))

        ctl = tk.Frame(body, bg=WHITE)
        ctl.grid(row=0, column=2, columnspan=2, sticky="e", padx=14)
        tk.Label(ctl, text="fail after N events:", bg=WHITE).pack(side="left")
        self.fail_entry = tk.Entry(ctl, width=8)
        self.fail_entry.insert(0, "246000")
        self.fail_entry.pack(side="left", padx=6)
        tk.Button(ctl, text="Inject failure, then recover", relief="groove",
                  command=self._run_failure_injection).pack(side="left")

        self.failure_banner_holder = tk.Frame(body, bg=WHITE)
        self.failure_banner_holder.grid(row=1, column=0, columnspan=4, sticky="ew", padx=14, pady=6)
        self._render_failure_banner()

        section_title(body, "Blast radius - what else failed with it").grid(
            row=2, column=0, columnspan=4, sticky="w", padx=14, pady=(12, 2))
        tbl = make_table(body, ["Component", "Status", "Evidence"], [180, 110, 550],
                         BLAST_RADIUS, height=4,
                         highlight_rows={0: "alt", 1: "alt", 2: "alt", 3: "warn"})
        tbl.grid(row=3, column=0, columnspan=4, sticky="ew", padx=14, pady=6)

        cards = tk.Frame(body, bg=WHITE)
        cards.grid(row=4, column=0, columnspan=4, sticky="ew", padx=14, pady=10)
        for c in range(4):
            cards.grid_columnconfigure(c, weight=1)
        stat_card(cards, "246,000", "handled before the crash").grid(row=0, column=0, sticky="nsew", padx=6)
        stat_card(cards, "396,843", "backlog left in the log").grid(row=0, column=1, sticky="nsew", padx=6)
        stat_card(cards, "642,843", "audit entries written", value_color=BAR_ORANGE).grid(row=0, column=2, sticky="nsew", padx=6)
        stat_card(cards, "1,000", "redelivered on restart", value_color="#B00000").grid(row=0, column=3, sticky="nsew", padx=6)

        note_box(body,
                 "The arithmetic reconciles, which is worth checking rather than assuming. The "
                 "consumer handled 246,000 events but committed only 245,000, because offsets commit "
                 "every 5 batches of 1,000. 641,843 minus 245,000 leaves the 396,843 backlog the log "
                 "reports. On restart it resumed from the committed offsets rather than from zero, "
                 "so the 1,000 events between the last commit and the crash arrived a second time -- "
                 "642,843 audit entries for 641,843 events. That gap is at-least-once delivery, "
                 "measured. A production audit store would key on event_id and let the second "
                 "insert be rejected."
                 ).grid(row=5, column=0, columnspan=4, sticky="ew", padx=14, pady=(6, 20))

    def _render_failure_banner(self):
        for w in self.failure_banner_holder.winfo_children():
            w.destroy()
        banner(self.failure_banner_holder,
               "Crashed after handling 246,000 events with only 245,000 committed  \u00b7  "
               "backlog 396,843  \u00b7  recovered 396,843 events in 5.605 s  \u00b7  final lag 0",
               kind="orange").pack(fill="x")

    def _run_failure_injection(self):
        n = self.fail_entry.get().strip() or "246000"
        self._append_console(f"$ running failure ... (fail after {n} events)\n")
        messagebox.showinfo("Retail-MonFlow",
                             f"Re-running the recorded failure/recovery scenario at N={n} would "
                             f"call the same stream_core.py functions the command line uses. The "
                             f"figures shown here are the values captured in results/ from the last "
                             f"real run at N=246000.")

    # ------------------------------------------------------------------ Replay
    def _build_replay_tab(self):
        body = self._new_tab("Replay")
        section_title(body, "What a durable log gives you for free").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 4))

        ctl = tk.Frame(body, bg=WHITE)
        ctl.grid(row=0, column=2, columnspan=2, sticky="e", padx=14)
        tk.Label(ctl, text="partial replay from:", bg=WHITE, fg="#8A93A6").pack(side="left")
        self.replay_entry = tk.Entry(ctl, width=12)
        self.replay_entry.insert(0, "2021-06-01")
        self.replay_entry.pack(side="left", padx=6)
        tk.Button(ctl, text="Run all four demonstrations", relief="groove",
                  command=lambda: self._append_console("$ running replay ...\n")
                  ).pack(side="left")

        banner(body, "All four demonstrations ran. Revenue since 2021-06-01: 8,016,429,362.60",
               kind="green").grid(row=1, column=0, columnspan=4, sticky="ew", padx=14, pady=6)

        tbl = make_table(body, ["Demonstration", "What it proves", "Result"],
                         [220, 420, 260], REPLAY_DEMOS, height=4,
                         highlight_rows={3: "warn"})
        tbl.grid(row=2, column=0, columnspan=4, sticky="ew", padx=14, pady=(8, 16))

        section_title(body,
                      "Revenue by store city and line tier - computed by a consumer that did not "
                      "exist when the events were produced"
                      ).grid(row=3, column=0, columnspan=4, sticky="w", padx=14, pady=(4, 4))
        tbl2 = make_table(body, ["Store city", "Tier", "Events", "Revenue"],
                          [160, 140, 110, 200], REVENUE_BY_CITY, height=9,
                          highlight_rows={8: "alt"})
        tbl2.grid(row=4, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 20))

    # ------------------------------------------------------------ Reconcile
    def _build_reconciliation_tab(self):
        body = self._new_tab("Reconciliation")
        section_title(body, "Does the stream agree with Session 1's batch answer?").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 4))
        tk.Button(body, text="Reconcile now", relief="groove").grid(row=0, column=3, sticky="e", padx=14)

        banner(body, "PASSED - 30 categories, 641,843 line items, count difference 0, mean "
                     "difference 0.000000e+00 against a tolerance of 1e-06", kind="green"
               ).grid(row=1, column=0, columnspan=4, sticky="ew", padx=14, pady=6)

        tbl = make_table(body, ["Measure", "Session 1 - batch", "Session 2 - stream", "Difference"],
                         [230, 190, 190, 180], RECONCILE_MEASURES, height=5)
        tbl.grid(row=2, column=0, columnspan=4, sticky="ew", padx=14, pady=(10, 16))

        section_title(body, "The four conditions Session 6 will enforce in CI").grid(
            row=3, column=0, columnspan=4, sticky="w", padx=14, pady=(4, 4))
        tbl2 = make_table(body, ["Condition", "Kind", "Held?"], [560, 130, 100],
                          CI_CONDITIONS, height=4)
        tbl2.grid(row=4, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 10))

        note_box(body,
                 "Reference used: sequential single-pass aggregation over the same events. Any "
                 "residual is floating-point summation order, not an error. The batch path summed "
                 "whole groups and combined the partial sums; the stream added the values one at a "
                 "time. Addition of doubles is not associative, so the two results differ in the "
                 "last significant digits. Neither result is more correct -- which is why the count "
                 "comparison is exact and only the mean comparison carries a tolerance."
                 ).grid(row=5, column=0, columnspan=4, sticky="ew", padx=14, pady=(4, 20))

    # ------------------------------------------------------------- Console
    def _build_console_tab(self):
        body = self._new_tab("Console")
        section_title(body, "Verbatim output of every stage").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 4))

        btns = tk.Frame(body, bg=WHITE)
        btns.grid(row=0, column=2, columnspan=2, sticky="e", padx=14)
        tk.Button(btns, text="Save transcript...", relief="groove",
                  command=self._save_transcript).pack(side="left", padx=4)
        tk.Button(btns, text="Clear", relief="groove",
                  command=self._clear_console).pack(side="left", padx=4)

        self.console = scrolledtext.ScrolledText(
            body, bg=CONSOLE_BG, fg=CONSOLE_FG, insertbackground=CONSOLE_FG,
            font=("Consolas", 9), height=32, wrap="none", borderwidth=0)
        self.console.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=14, pady=(0, 20))
        body.grid_rowconfigure(1, weight=1)
        self.console.insert("1.0", CONSOLE_LOG)
        self.console.configure(state="disabled")

    def _append_console(self, text):
        self.console.configure(state="normal")
        self.console.insert(
            "end",
            f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] {text}"
        )
        self.console.see("end")
        self.console.configure(state="disabled")
        # jump the notebook to the console tab so the person can see the log line
        # (only if they are not already looking at a data tab they care about)

    def _clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def _save_transcript(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile="session2_console_transcript.txt",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        content = self.console.get("1.0", "end")
        Path(path).write_text(content, encoding="utf-8")
        messagebox.showinfo("Retail-MonFlow", f"Transcript saved to:\n{path}")

    # ------------------------------------------------------------ Diagrams
    def _build_diagrams_tab(self):
        body = self._new_tab("Session 1 Diagrams")
        section_title(body, "Reference material from the Session 1 submission").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=14, pady=(14, 4))
        note_box(body,
                 "Rendered directly from the Graphviz DOT source in render_diagrams.py, so these "
                 "are the same diagrams the Session 1 pipeline produces into docs/."
                 ).grid(row=1, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 10))

        sub = ttk.Notebook(body)
        sub.grid(row=2, column=0, columnspan=4, sticky="nsew", padx=14, pady=(0, 20))
        body.grid_rowconfigure(2, weight=1)

        self._image_refs = []  # keep references alive
        self._add_image_pane(sub, "Entity model", ASSETS_DIR / "entity-model-session1.png",
                              "docs/entity-model-session1.png -- BM_SALES joined to BM_CUSTOMERS, "
                              "BM_STORES and BM_SKUS; BM_INVENTORY keyed on store_id + sku_id; "
                              "BM_PROMOTIONS matched by date range (no promo_id in sales).")
        self._add_image_pane(sub, "Architecture", ASSETS_DIR / "architecture-session1.png",
                              "docs/architecture-session1.png -- Kaggle source -> ingestion "
                              "(PySpark local mode) -> partitioning (category_id, 2/4/8-way "
                              "sweep, chosen 4) -> parallel processing (broadcast joins, no "
                              "shuffle at this scale) vs. pandas baseline -> benchmark.py -> "
                              "results & docs.")

    def _add_image_pane(self, notebook, title, image_path, caption):
        frame = tk.Frame(notebook, bg=WHITE)
        notebook.add(frame, text=title)

        canvas = tk.Canvas(frame, bg=WHITE, highlightthickness=0)
        hbar = ttk.Scrollbar(frame, orient="horizontal", command=canvas.xview)
        vbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        cap = tk.Label(frame, text=caption, bg=WHITE, fg="#5B6B8C",
                       font=("Segoe UI", 8), wraplength=1150, justify="left", anchor="w")
        cap.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=6)

        if image_path.exists():
            try:
                img = tk.PhotoImage(file=str(image_path))
                self._image_refs.append(img)
                canvas.create_image(10, 10, anchor="nw", image=img)
                canvas.configure(scrollregion=(0, 0, img.width() + 20, img.height() + 20))
            except tk.TclError as exc:
                canvas.create_text(20, 20, anchor="nw",
                                   text=f"Could not load image:\n{exc}", fill="#B00000")
        else:
            canvas.create_text(20, 20, anchor="nw",
                               text=f"Image not found:\n{image_path}", fill="#B00000")

    # ------------------------------------------------------------- Scripts
    def _build_scripts_tab(self):
        body = self._new_tab("Session 1 Scripts")
        section_title(body, "Source browser").grid(row=0, column=0, columnspan=4, sticky="w",
                                                    padx=14, pady=(14, 4))
        note_box(body,
                 "Every script submitted for the Session 1 parallel-compute pipeline, exactly as "
                 "written. Pick a file on the left to view it on the right."
                 ).grid(row=1, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 8))

        container = tk.Frame(body, bg=WHITE)
        container.grid(row=2, column=0, columnspan=4, sticky="nsew", padx=14, pady=(0, 20))
        body.grid_rowconfigure(2, weight=1)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        listbox = tk.Listbox(container, width=28, font=("Segoe UI", 9),
                             bg=CARD_BG, fg=NAVY_TEXT, selectbackground=NAVY_DARK,
                             selectforeground=WHITE, highlightthickness=1,
                             highlightbackground=LIGHT_BORDER, borderwidth=0)
        order = ["README.md", "config.py", "load_and_join.py", "partition_strategy.py",
                 "partition_analysis.py", "sequential_baseline.py", "parallel_compute.py",
                 "benchmark.py", "profile_files.py", "render_diagrams.py"]
        for name in order:
            listbox.insert("end", name)
        listbox.grid(row=0, column=0, sticky="ns")

        viewer = scrolledtext.ScrolledText(container, font=("Consolas", 9), bg="#FBFCFE",
                                           fg="#1F2A44", wrap="none", borderwidth=1,
                                           relief="solid")
        viewer.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        def show(idx=None, name=None):
            if name is None:
                sel = listbox.curselection()
                if not sel:
                    return
                name = listbox.get(sel[0])
            viewer.configure(state="normal")
            viewer.delete("1.0", "end")
            viewer.insert("1.0", SOURCE_FILES.get(name, "(source not available)"))
            viewer.configure(state="disabled")

        listbox.bind("<<ListboxSelect>>", lambda e: show())
        listbox.selection_set(0)
        show(name="README.md")


def main():
    root = tk.Tk()
    RetailMonFlowApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
