# CMA-Flow — Session 2 Event Streaming

## Project title
**CMA-Flow: Event Streaming Console for the RetailFlow Retail Dataset**

## What this session is

Session 1 answered a batch question with pandas/PySpark:
"if we group RetailFlow's sales by region, what does the data say?"

Session 2 asks the same question a different way — as an event stream.
The same 641,843 joined sales transactions from Session 1 are replayed
as events onto a topic, `transaction.recorded`, keyed on `region` and
split across 4 partitions. Three independent consumer groups read that
stream, a reconciliation step checks the stream's answer against
Session 1's batch answer, and two more demonstrations show what a
durable, replayable log gives you for free: crash-and-recover, and
replay from any offset.

Everything in the console is a simulation/demo layer — the numbers are
fixed, illustrative figures (matching a reference run) rather than a
live Kafka cluster — but the structure, terminology, and arithmetic
are all real: hash partitioning and skew, consumer-group offsets and
lag, at-least-once delivery on recovery, and floating-point
non-associativity in the reconciliation tolerance.

## Files

| File | What it is |
|---|---|
| `cma_flow_session2.py` | The console app — a Tkinter desktop GUI with 7 tabs (Pipeline, Durable log, Consumers & lag, Failure & recovery, Replay, Reconciliation, Console). No third-party packages required. |
| `cma-flow-session2.html` | The same console as a single-file HTML/JS app — open it directly in a browser, no install needed. |
| `render_diagrams_session2.py` | Renders `docs/entity-model-session2.png` and `docs/architecture-session2.png` with Graphviz. |
| `docs/` | Output folder for the rendered diagrams. |

## Topic model

- **Topic**: `transaction.recorded`
- **Key**: `region` (50 distinct values)
- **Partitions**: 4, assigned by `hash(region) mod 4`
- **Total events**: 641,843
- **Partition distribution**: 182,711 / 115,960 / 229,780 / 113,392 (skew 2.03 : 1 — 50 regions don't divide evenly onto 4 partitions, so one partition does roughly twice the work of the lightest one)

## Consumer groups

| Group | Job | Throughput |
|---|---|---|
| `revenue-projector` | Rebuilds regional revenue incrementally from the stream | 31,115 events/sec |
| `audit-writer` | Writes an independent append-only audit trail (I/O bound — a disk write per event) | 15,340 events/sec |
| `high-value-alerter` | Flags transactions above 900.00 | 30,434 events/sec |

Each group reads all 4 partitions and tracks its own offsets, so one
group's speed or a crash never affects the others' lag.

## Windows / VS Code setup

Open the project folder in VS Code, then open a PowerShell terminal.

### Option A — desktop app (Tkinter)

No packages to install; Tkinter ships with most standard Python
installs on Windows.

```powershell
py cma_flow_session2.py
```

If you get `ModuleNotFoundError: No module named 'tkinter'`, reinstall
Python from python.org with the "tcl/tk and IDLE" option checked.

### Option B — browser app

No install at all — just open the file:

```powershell
start cma-flow-session2.html
```

### Diagrams

Diagram rendering needs Graphviz's `dot` on PATH.

```powershell
py render_diagrams_session2.py
```

If `dot` isn't found, install Graphviz and add its `bin` folder to
PATH, e.g.:

```
C:\Program Files\Graphviz\bin
```

## Running the console

Every button calls one of the same six stage functions the console
uses internally (self-test, produce, consume, reconcile, inject
failure, replay), so the numbers you see stay identical across every
tab and are also echoed verbatim to the **Console** tab. Stages depend
on each other — Produce runs before Consume, Consume before Reconcile
— and clicking a later stage will silently run its prerequisites
first if you haven't run them yet. **Run everything** on the Pipeline
tab reproduces the full session end to end.

- **Pipeline** — overall status cards, a button per stage, the stage
  table, and the `results/` artefact list.
- **Durable log** — partition distribution chart, the six guarantees
  the self-test checks (stable key routing, ordering within a
  partition, non-destructive read, consumer-group isolation, replay,
  durability), and why the four partitions come out uneven.
- **Consumers & lag** — throughput per group and the full
  per-partition committed-offset table.
- **Failure & recovery** — pick an event count, inject a crash on
  `audit-writer`, and see the blast radius (what's unaffected vs.
  down), the backlog, and the at-least-once redelivery count on
  recovery. The recovery time is computed from the backlog size, not
  hard-coded.
- **Replay** — four demonstrations of what a durable log gives a
  consumer that didn't exist when the events were produced, plus a
  revenue breakdown by mechanism and tier.
- **Reconciliation** — the stream's answer vs. Session 1's batch
  answer, and the four conditions a later CI session enforces (exact
  region-set match, exact count match, revenue-mean match within
  tolerance, every group at lag 0).
- **Console** — a verbatim, appendable transcript of every action;
  save it to a text file with **Save transcript...**.

## Output files

`render_diagrams_session2.py` creates:

- `docs/entity-model-session2.png` — topic → partitions → consumer
  groups → Session 1 batch answer, as an entity-relationship diagram.
- `docs/architecture-session2.png` — the full pipeline: source →
  producer → durable log → parallel consumers → reconciliation →
  outputs, with the failure/recovery and replay paths shown as
  side branches.

## Notes

- All Session 2 figures were derived from Session 1's 641,843-row
  joined dataset, scaled consistently from an original 60,000-event
  reference run — partition counts, consumer timings, revenue
  figures, and failure/recovery math all agree with each other and
  sum back to 641,843 exactly.
- The reconciliation step's tiny residual (on the order of `1e-12`)
  isn't an error: Spark sums whole partitions and combines the partial
  sums, while the stream adds values one at a time. Floating-point
  addition isn't associative, so the two summation orders differ in
  the last significant digits — which is why the record count is
  compared exactly and only the revenue mean carries a tolerance.
- The failure-injection recovery time is computed live from the
  backlog size (`backlog / recovery rate`), so it stays correct for
  any "fail after N events" value you enter, not just the default.
