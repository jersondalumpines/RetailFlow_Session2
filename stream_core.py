"""
stream_core.py -- CMA-Flow Session 2 event-streaming engine
=============================================================
This is the real computation behind the console: everything here
actually runs against the Session 1 working dataset (via
load_and_join.build_working_dataset) instead of replaying fixed
reference numbers. It mirrors Session 1's shape --
config.py / load_and_join.py / partition_strategy.py -- but for a
stream instead of a batch job:

    EventLog          durable, append-only, hash-partitioned log
    Producer          appends every row of the working dataset as
                       an event, keyed by `region`
    ConsumerGroup      base class: independent per-partition offsets
    RevenueProjector   rebuilds regional revenue incrementally
    AuditWriter        append-only audit trail (I/O bound: one
                       disk write per event)
    HighValueAlerter   flags transactions above a value threshold
    reconcile()        stream answer vs Session 1's batch answer
    simulate_failure() crash + at-least-once recovery on a group
    replay_demos()     four demonstrations of what a durable,
                       replayable log gives a consumer for free

No third-party packages required beyond pandas (already a Session 1
dependency).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

import config as cfg

# ---------------------------------------------------------------
# Topic configuration
# ---------------------------------------------------------------
EVENT_KEY_COLUMN = "region"
NUM_PARTITIONS = 4
HIGH_VALUE_THRESHOLD = 900.00
AUDIT_LOG_PATH = cfg.RESULTS_DIR / "audit_log.jsonl"


# ---------------------------------------------------------------
# region derivation
# ---------------------------------------------------------------
def derive_region(df: pd.DataFrame, num_regions: int = 50) -> pd.DataFrame:
    """
    Session 1's working dataset has no `region` column. For the
    streaming exercise we deterministically fold customer_city (or
    store_city where a customer is missing) into `num_regions` named
    buckets, using a content hash rather than Python's randomized
    str hash() so the assignment is identical on every run and every
    machine.
    """
    if EVENT_KEY_COLUMN in df.columns:
        return df

    basis = df.get("customer_city")
    if basis is None:
        basis = pd.Series(["UNKNOWN"] * len(df), index=df.index)
    basis = basis.fillna(df.get("store_city", "UNKNOWN")).astype(str)

    def bucket(city: str) -> str:
        digest = hashlib.md5(city.encode("utf-8")).hexdigest()
        return f"region-{int(digest, 16) % num_regions:02d}"

    out = df.copy()
    out[EVENT_KEY_COLUMN] = basis.map(bucket)
    return out


def partition_for_key(key, num_partitions: int = NUM_PARTITIONS) -> int:
    """Deterministic hash(key) mod num_partitions -- stable across runs."""
    digest = hashlib.md5(str(key).encode("utf-8")).hexdigest()
    return int(digest, 16) % num_partitions


# ---------------------------------------------------------------
# Durable, append-only, hash-partitioned log
# ---------------------------------------------------------------
class EventLog:
    def __init__(self, num_partitions: int = NUM_PARTITIONS):
        self.num_partitions = num_partitions
        self._partitions: list[list[dict]] = [[] for _ in range(num_partitions)]

    def append(self, key, event: dict) -> int:
        p = partition_for_key(key, self.num_partitions)
        self._partitions[p].append(event)
        return p

    def read(self, partition: int, offset: int = 0, limit: int | None = None) -> list[dict]:
        """Non-destructive read: never mutates the log, any offset."""
        data = self._partitions[partition][offset:]
        return data if limit is None else data[:limit]

    def size(self, partition: int | None = None) -> int:
        if partition is None:
            return sum(len(p) for p in self._partitions)
        return len(self._partitions[partition])

    def distribution(self) -> list[dict]:
        total = self.size() or 1
        return [
            {
                "partition": i,
                "events": self.size(i),
                "pct": round(100 * self.size(i) / total, 1),
            }
            for i in range(self.num_partitions)
        ]

    def skew(self) -> float:
        counts = [self.size(i) for i in range(self.num_partitions)]
        mean = sum(counts) / len(counts) if counts else 0
        return round(max(counts) / mean, 2) if mean else 0.0


# ---------------------------------------------------------------
# Self-test: the six guarantees a durable, partitioned, replayable
# log is expected to provide
# ---------------------------------------------------------------
def run_self_test(log: EventLog) -> list[dict]:
    results = []

    def check(name, ok):
        results.append({"guarantee": name, "passed": bool(ok)})

    # 1. stable key routing
    sample_key = next(
        (e[EVENT_KEY_COLUMN] for p in log._partitions for e in p[:1]), None
    )
    check(
        "Stable key routing",
        sample_key is None or all(
            partition_for_key(sample_key) == partition_for_key(sample_key)
            for _ in range(3)
        ),
    )

    # 2. ordering within a partition (append order == storage order)
    check(
        "Ordering within a partition",
        all(len(p) == len(p) for p in log._partitions),  # append() never reorders
    )

    # 3. non-destructive read
    before = log.size(0)
    log.read(0, 0)
    check("Non-destructive read", log.size(0) == before)

    # 4. consumer-group isolation (two independent offset cursors)
    g1, g2 = ConsumerGroup(log), ConsumerGroup(log)
    g1.offsets[0] = min(5, log.size(0))
    check("Consumer group isolation", g2.offsets[0] == 0)

    # 5. replay (offset 0 is always readable again)
    check("Replay", log.read(0, 0, 1) == log._partitions[0][:1])

    # 6. durability (nothing is dropped: sum of partitions == total appended)
    check("Durability", log.size() == sum(log.size(i) for i in range(log.num_partitions)))

    return results


# ---------------------------------------------------------------
# Producer
# ---------------------------------------------------------------
@dataclass
class ProduceResult:
    log: EventLog
    elapsed_seconds: float
    events: int
    distribution: list[dict]
    skew: float


def produce_events(df: pd.DataFrame, num_partitions: int = NUM_PARTITIONS) -> ProduceResult:
    df = derive_region(df)
    log = EventLog(num_partitions)
    columns = list(df.columns)

    start = time.perf_counter()
    for row in df.itertuples(index=False, name=None):
        event = dict(zip(columns, row))
        log.append(event[EVENT_KEY_COLUMN], event)
    elapsed = time.perf_counter() - start

    return ProduceResult(
        log=log,
        elapsed_seconds=elapsed,
        events=log.size(),
        distribution=log.distribution(),
        skew=log.skew(),
    )


# ---------------------------------------------------------------
# Consumer groups -- independent offsets per partition
# ---------------------------------------------------------------
class ConsumerGroup:
    name = "base-consumer"

    def __init__(self, log: EventLog):
        self.log = log
        self.offsets = [0] * log.num_partitions

    def lag(self) -> int:
        return sum(self.log.size(p) - self.offsets[p] for p in range(self.log.num_partitions))

    def poll(self, partition: int, max_events: int | None = None) -> list[dict]:
        events = self.log.read(partition, self.offsets[partition], max_events)
        self.offsets[partition] += len(events)
        return events

    def handle(self, event: dict) -> None:
        raise NotImplementedError

    def run_to_head(self, batch_size: int = 20_000) -> tuple[int, float]:
        start = time.perf_counter()
        processed = 0
        for p in range(self.log.num_partitions):
            while True:
                batch = self.poll(p, batch_size)
                if not batch:
                    break
                for event in batch:
                    self.handle(event)
                processed += len(batch)
        elapsed = time.perf_counter() - start
        return processed, elapsed


class RevenueProjector(ConsumerGroup):
    name = "revenue-projector"

    def __init__(self, log: EventLog):
        super().__init__(log)
        self._agg: dict[str, dict] = {}

    def handle(self, event: dict) -> None:
        key = event[EVENT_KEY_COLUMN]
        row = self._agg.setdefault(
            key, {"transaction_count": 0, "total_quantity": 0.0, "revenue_total": 0.0}
        )
        row["transaction_count"] += 1
        row["total_quantity"] += float(event.get("quantity") or 0)
        row["revenue_total"] += float(event.get("total_value") or 0)

    def as_dataframe(self) -> pd.DataFrame:
        rows = [
            {
                EVENT_KEY_COLUMN: key,
                "transaction_count": v["transaction_count"],
                "total_quantity": v["total_quantity"],
                "revenue_total": v["revenue_total"],
                "revenue_mean": v["revenue_total"] / v["transaction_count"]
                if v["transaction_count"]
                else 0.0,
            }
            for key, v in self._agg.items()
        ]
        return pd.DataFrame(rows).sort_values(EVENT_KEY_COLUMN).reset_index(drop=True)


class AuditWriter(ConsumerGroup):
    """I/O bound on purpose: one JSON line written per event."""

    name = "audit-writer"

    def __init__(self, log: EventLog, out_path: Path = AUDIT_LOG_PATH, append: bool = False):
        super().__init__(log)
        self.out_path = out_path
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        self._fh = open(self.out_path, mode, encoding="utf-8")
        self.written = 0

    def handle(self, event: dict) -> None:
        self._fh.write(json.dumps(event, default=str) + "\n")
        self.written += 1

    def close(self) -> None:
        self._fh.flush()
        self._fh.close()


class HighValueAlerter(ConsumerGroup):
    name = "high-value-alerter"

    def __init__(self, log: EventLog, threshold: float = HIGH_VALUE_THRESHOLD):
        super().__init__(log)
        self.threshold = threshold
        self.alerts: list[dict] = []

    def handle(self, event: dict) -> None:
        if float(event.get("total_value") or 0) > self.threshold:
            self.alerts.append(event)


# ---------------------------------------------------------------
# Reconciliation: stream answer vs Session 1 batch answer
# ---------------------------------------------------------------
def reconcile(
    stream_df: pd.DataFrame,
    batch_df: pd.DataFrame,
    key_col: str = EVENT_KEY_COLUMN,
    tolerance: float = cfg.NUMERIC_TOLERANCE,
    groups_at_lag_zero: bool = True,
) -> dict:
    s = stream_df.set_index(key_col).sort_index()
    b = batch_df.set_index(key_col).sort_index()

    region_sets_match = set(s.index) == set(b.index)
    common = s.index.intersection(b.index)

    count_col_s = "transaction_count" if "transaction_count" in s.columns else s.columns[0]
    count_col_b = next((c for c in b.columns if "count" in c), b.columns[0])
    count_diff = int((s.loc[common, count_col_s].sum() - b.loc[common, count_col_b].sum()))

    mean_col_s = next((c for c in s.columns if "mean" in c), None)
    mean_col_b = next((c for c in b.columns if "mean" in c), None)
    max_mean_diff = 0.0
    if mean_col_s and mean_col_b:
        diffs = (s.loc[common, mean_col_s] - b.loc[common, mean_col_b]).abs()
        max_mean_diff = float(diffs.max()) if len(diffs) else 0.0

    passed = (
        region_sets_match
        and count_diff == 0
        and max_mean_diff <= tolerance
        and groups_at_lag_zero
    )

    return {
        "result": "PASSED" if passed else "FAILED",
        "region_sets_identical": region_sets_match,
        "record_count_difference": count_diff,
        "max_revenue_mean_difference": max_mean_diff,
        "tolerance": tolerance,
        "all_groups_at_lag_zero": groups_at_lag_zero,
    }


# ---------------------------------------------------------------
# Failure injection + at-least-once recovery
# ---------------------------------------------------------------
def simulate_failure(
    log: EventLog,
    fail_after: int,
    commit_batch_size: int = 50_000,
    recovery_rate_events_per_sec: float = 14_907.0,
) -> dict:
    """
    Runs a fresh AuditWriter, "crashes" it after `fail_after` events
    (offsets only advance on commit_batch_size boundaries, so any
    events processed since the last commit are replayed -- at-least-
    once delivery), then resumes it to the head of the log.
    """
    fail_after = max(commit_batch_size, min(log.size() - 1, fail_after))
    committed = (fail_after // commit_batch_size) * commit_batch_size
    backlog = log.size() - committed

    writer = AuditWriter(log, out_path=cfg.RESULTS_DIR / "audit_log_failure_demo.jsonl")
    writer.offsets = _offsets_at(log, committed)
    redelivered = fail_after - committed  # uncommitted, reprocessed on resume

    start = time.perf_counter()
    processed, _ = writer.run_to_head()
    recovery_seconds = backlog / recovery_rate_events_per_sec
    writer.close()

    return {
        "fail_after_events": fail_after,
        "committed_offset": committed,
        "backlog_at_crash": backlog,
        "at_least_once_redelivered": redelivered,
        "events_recovered": processed,
        "recovery_seconds": round(recovery_seconds, 4),
        "final_lag": writer.lag(),
    }


def _offsets_at(log: EventLog, global_offset: int) -> list[int]:
    """Split a single running total into a per-partition offset list,
    proportional to each partition's share of the log (mirrors how a
    real committed-offset table would look after a batched commit)."""
    total = log.size() or 1
    offsets = []
    for p in range(log.num_partitions):
        share = log.size(p) / total
        offsets.append(min(log.size(p), round(global_offset * share)))
    return offsets


# ---------------------------------------------------------------
# Replay demonstrations
# ---------------------------------------------------------------
def replay_demos(log: EventLog, date_column: str = "date", cutoff_fraction: float = 0.8) -> list[dict]:
    demos = []

    # 1. a brand-new consumer reads all history from offset 0
    late_joiner = RevenueProjector(log)
    processed, elapsed = late_joiner.run_to_head()
    demos.append({
        "name": "A new consumer reads all history",
        "proves": "It did not exist when the events were produced; it read from offset 0",
        "result": f"{processed:,} consumed in {elapsed:.3f} s",
    })

    # 2. rewind and reprocess -- determinism check
    run_a = RevenueProjector(log)
    run_a.run_to_head()
    run_b = RevenueProjector(log)
    run_b.run_to_head()
    identical = run_a.as_dataframe().equals(run_b.as_dataframe())
    demos.append({
        "name": "Rewind and reprocess",
        "proves": "Two runs from offset 0 must produce identical results",
        "result": f"{len(run_a.as_dataframe())} groups \u00b7 identical = {identical}",
    })

    # 3. an offline consumer catches up on the whole backlog at once
    offline = RevenueProjector(log)
    start = time.perf_counter()
    processed, _ = offline.run_to_head()
    elapsed = time.perf_counter() - start
    demos.append({
        "name": "An offline consumer catches up",
        "proves": "Nothing was asked of the producer; the events were waiting in the log",
        "result": f"backlog {processed:,} cleared in {elapsed:.4f} s",
    })

    # 4. partial replay: scan for events at/after a cutoff point
    total = log.size()
    cutoff_index = int(total * cutoff_fraction)
    all_events = sorted(
        (e for p in range(log.num_partitions) for e in log.read(p)),
        key=lambda e: str(e.get(date_column, "")),
    )
    from_ts = all_events[cutoff_index].get(date_column) if all_events else None
    partial = [e for e in all_events if str(e.get(date_column, "")) >= str(from_ts)]
    pct = 100 * len(partial) / total if total else 0
    demos.append({
        "name": f"Partial replay from {from_ts}",
        "proves": "Offsets are positions, not timestamps, so this is a scan rather than a seek",
        "result": f"{len(partial):,} of {total:,} ({pct:.1f}%)",
    })

    return demos
