#!/usr/bin/env python3
"""
console.py -- CMA-Flow Session 2, command-line console
=========================================================
The real, computed counterpart to cma_flow_session2.py's Tkinter GUI:
same six stages (self-test, produce, consume, reconcile, failure &
recovery, replay), same artefacts in results/, but every number here
comes from actually running stream_core against Session 1's working
dataset instead of a fixed reference run.

Usage
-----
    python console.py                  # run every stage, print a
                                        # transcript, save artefacts
    python console.py --stage produce  # run one stage only
    python console.py --fail-after 267435
    python console.py --list-stages
"""

from __future__ import annotations

import argparse
import json
import time

import pandas as pd

import config as cfg
import stream_core as sc
from load_and_join import build_working_dataset
from sequential_baseline import run_baseline

STAGES = ["selftest", "produce", "consume", "reconcile", "failure", "replay"]


def banner(title: str) -> None:
    print()
    print("=" * 64)
    print(title)
    print("=" * 64)


def fmt(n) -> str:
    return f"{n:,}" if isinstance(n, (int,)) else f"{n:,.2f}"


class Session:
    """Holds state between stages, same dependency order as the GUI:
    produce -> consume -> reconcile, produce -> consume -> failure,
    produce -> consume -> replay."""

    def __init__(self):
        self.df: pd.DataFrame | None = None
        self.log: sc.EventLog | None = None
        self.produce_result: sc.ProduceResult | None = None
        self.projector: sc.RevenueProjector | None = None
        self.auditor: sc.AuditWriter | None = None
        self.alerter: sc.HighValueAlerter | None = None

    # ---- stage 0: load ------------------------------------------------
    def ensure_data(self):
        if self.df is None:
            cfg.ensure_directories()
            self.df = sc.derive_region(build_working_dataset(verbose=False))

    # ---- stage 1: self-test -------------------------------------------
    def stage_selftest(self):
        self.ensure_produced()
        banner("SELF-TEST")
        results = sc.run_self_test(self.log)
        for r in results:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"  {r['guarantee']:.<40} {status}")
        return results

    # ---- stage 2: produce ----------------------------------------------
    def ensure_produced(self):
        if self.produce_result is None:
            self.ensure_data()
            self.produce_result = sc.produce_events(self.df)
            self.log = self.produce_result.log

    def stage_produce(self):
        self.ensure_produced()
        r = self.produce_result
        banner("PRODUCE")
        print(f"  events produced : {fmt(r.events)}")
        print(f"  elapsed         : {r.elapsed_seconds:.3f} s")
        throughput = r.events / r.elapsed_seconds if r.elapsed_seconds else 0
        print(f"  throughput      : {fmt(int(throughput))} events/second")
        print()
        print("  PARTITION DISTRIBUTION  (hash(region) mod 4)")
        for p in r.distribution:
            bar = "#" * round(p["pct"] / 2)
            print(f"    partition {p['partition']} : {p['events']:>7,}  {p['pct']:>5}%  {bar}")
        print(f"  partition skew    : {r.skew} : 1")

        out = cfg.RESULTS_DIR / "session2_throughput.csv"
        pd.DataFrame([{
            "events": r.events,
            "elapsed_seconds": r.elapsed_seconds,
            "throughput_events_per_sec": throughput,
            "partition_skew": r.skew,
        }]).to_csv(out, index=False)
        print(f"  saved: {out}")
        return r

    # ---- stage 3: consume ----------------------------------------------
    def stage_consume(self):
        self.ensure_produced()
        banner("CONSUME")

        self.projector = sc.RevenueProjector(self.log)
        n, t = self.projector.run_to_head()
        print(f"  revenue-projector   : {fmt(n)} events in {t:.3f} s "
              f"({fmt(int(n / t)) if t else 0} events/sec), lag {self.projector.lag()}")

        self.auditor = sc.AuditWriter(self.log)
        n, t = self.auditor.run_to_head()
        self.auditor.close()
        print(f"  audit-writer        : {fmt(n)} events in {t:.3f} s "
              f"({fmt(int(n / t)) if t else 0} events/sec), lag {self.auditor.lag()}")

        self.alerter = sc.HighValueAlerter(self.log)
        n, t = self.alerter.run_to_head()
        print(f"  high-value-alerter  : {fmt(n)} events in {t:.3f} s "
              f"({fmt(int(n / t)) if t else 0} events/sec), lag {self.alerter.lag()}, "
              f"{len(self.alerter.alerts)} alerts")

        rev_df = self.projector.as_dataframe()
        rev_out = cfg.RESULTS_DIR / "streamed_regional_revenue.csv"
        rev_df.to_csv(rev_out, index=False)

        alerts_out = cfg.RESULTS_DIR / "high_value_alerts.csv"
        pd.DataFrame(self.alerter.alerts).to_csv(alerts_out, index=False)

        lag_out = cfg.RESULTS_DIR / "consumer_lag.csv"
        pd.DataFrame([
            {"group": g.name, "lag": g.lag()}
            for g in (self.projector, self.auditor, self.alerter)
        ]).to_csv(lag_out, index=False)

        print(f"  saved: {rev_out}")
        print(f"  saved: {alerts_out}")
        print(f"  saved: {lag_out}")
        print(f"  saved: {self.auditor.out_path}")
        return rev_df

    # ---- stage 4: reconcile ---------------------------------------------
    def stage_reconcile(self):
        if self.projector is None:
            self.stage_consume()
        banner("RECONCILIATION vs Session 1 batch")

        batch_df, _ = run_baseline(self.df, sc.EVENT_KEY_COLUMN, verbose=False)
        stream_df = self.projector.as_dataframe()
        report = sc.reconcile(stream_df, batch_df, sc.EVENT_KEY_COLUMN)

        print(f"  region sets identical        : {report['region_sets_identical']}")
        print(f"  record count difference      : {report['record_count_difference']}")
        print(f"  max revenue-mean difference  : {report['max_revenue_mean_difference']:.3e}")
        print(f"  tolerance applied            : {report['tolerance']:.0e}")
        print(f"  all groups at lag 0          : {report['all_groups_at_lag_zero']}")
        print(f"  RESULT                       : {report['result']}")

        out = cfg.RESULTS_DIR / "reconciliation_report.json"
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"  saved: {out}")
        return report

    # ---- stage 5: failure & recovery -------------------------------------
    def stage_failure(self, fail_after: int | None = None):
        self.ensure_produced()
        banner("FAILURE & RECOVERY  (audit-writer)")
        if fail_after is None:
            fail_after = self.log.size() * 2 // 5  # ~40% through, matches GUI default feel
        report = sc.simulate_failure(self.log, fail_after)
        print(f"  fail after       : {fmt(report['fail_after_events'])} events")
        print(f"  committed offset : {fmt(report['committed_offset'])} events")
        print(f"  backlog at crash : {fmt(report['backlog_at_crash'])} events")
        print(f"  at-least-once redelivered : {fmt(report['at_least_once_redelivered'])} events")
        print(f"  recovered        : {fmt(report['events_recovered'])} events "
              f"in {report['recovery_seconds']:.4f} s")
        print(f"  final lag        : {report['final_lag']}")
        return report

    # ---- stage 6: replay --------------------------------------------------
    def stage_replay(self):
        if self.projector is None:
            self.stage_consume()
        banner("REPLAY DEMONSTRATIONS")
        demos = sc.replay_demos(self.log)
        for i, d in enumerate(demos, 1):
            print(f"  {i}. {d['name']}")
            print(f"     proves : {d['proves']}")
            print(f"     result : {d['result']}")
        return demos


def run_all(session: Session, fail_after: int | None):
    start = time.perf_counter()
    session.stage_selftest()
    session.stage_produce()
    session.stage_consume()
    session.stage_reconcile()
    session.stage_failure(fail_after)
    session.stage_replay()
    banner("DONE")
    print(f"  total wall time: {time.perf_counter() - start:.2f} s")
    print(f"  artefacts written to: {cfg.RESULTS_DIR}")


def main():
    parser = argparse.ArgumentParser(description="CMA-Flow Session 2 console")
    parser.add_argument("--stage", choices=STAGES, help="run a single stage instead of all")
    parser.add_argument("--fail-after", type=int, default=None,
                         help="event count to fail audit-writer after (failure stage)")
    parser.add_argument("--list-stages", action="store_true")
    args = parser.parse_args()

    if args.list_stages:
        print("\n".join(STAGES))
        return

    session = Session()
    if args.stage:
        getattr(session, f"stage_{args.stage}")(
            *([args.fail_after] if args.stage == "failure" else [])
        )
    else:
        run_all(session, args.fail_after)


if __name__ == "__main__":
    main()
