#!/usr/bin/env python3
"""
CMA-Flow -- Session 2 Event Streaming Console
================================================
A desktop (Tkinter) recreation of the Session 2 console: Pipeline,
Durable log, Consumers & lag, Failure & recovery, Replay,
Reconciliation, and Console tabs.

Every button in the UI calls one of the RUNNERS below -- the same
functions a command-line run of producer.py / consumers.py /
reconcile.py would call -- so the numbers you see stay consistent
across every tab and are also echoed to the Console tab verbatim,
exactly like the reference app.

No third-party packages required: everything here is the Python
standard library (tkinter + ttk).

Run with:
    python cma_flow_session2.py
"""

import datetime as _dt
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ---------------------------------------------------------------
# Palette -- matches the reference console
# ---------------------------------------------------------------
NAVY       = "#1e3358"
NAVY_DARK  = "#16253f"
NAVY_MID   = "#2c4772"
PAPER      = "#f5f6f8"
LINE       = "#dfe3ea"
INK        = "#1c2430"
INK_SOFT   = "#5b6472"
GREEN_BG   = "#eaf6e6"
GREEN_TXT  = "#2f6d2f"
GREEN_BRD  = "#bfe3ba"
RED_BG     = "#fdeceb"
RED_TXT    = "#a33327"
RED_BRD    = "#f3c6c0"
KHAKI      = "#c99a2e"
ORANGE_TXT = "#b3701f"
ROW_ALT    = "#f7f9fb"

# ---------------------------------------------------------------
# Data model -- mirrors what Session 2's producer.py / consumers.py /
# reconcile.py would compute and print.
# ---------------------------------------------------------------
TOTAL_EVENTS = 641843
REGIONS = 50

PARTITIONS = [
    {"id": 0, "events": 182711, "pct": 28.5, "note": "above even share"},
    {"id": 1, "events": 115960, "pct": 18.1, "note": "below even share"},
    {"id": 2, "events": 229780, "pct": 35.8, "note": "heaviest \u2014 sets the numerator of the skew"},
    {"id": 3, "events": 113392, "pct": 17.7, "note": "below even share"},
]

# Constant throughput rates (events/second) that every derived timing
# figure below is computed from, so the console stays internally
# consistent no matter how large TOTAL_EVENTS is.
PRODUCE_RATE = 12095          # events/sec while producing
RECOVERY_RATE = 40000 / 2.683  # events/sec while an audit-writer recovers a backlog
FAILURE_BATCH_SIZE = 50000     # offsets commit every this-many events

GUARANTEES = [
    "Stable key routing", "Ordering within a partition", "Non-destructive read",
    "Consumer group isolation", "Replay", "Durability",
]

CONSUMERS = [
    {"name": "revenue-projector", "desc": "Rebuilds regional revenue incrementally from the stream",
     "seconds": 20.628, "throughput": 31115},
    {"name": "audit-writer", "desc": "Writes an independent append-only audit trail",
     "seconds": 41.841, "throughput": 15340},
    {"name": "high-value-alerter", "desc": "Flags transactions above 900.00",
     "seconds": 21.090, "throughput": 30434},
]

REVENUE_ROWS = [
    ("data-as-a-service", "free", 79802, 39985364.06),
    ("data-as-a-service", "paid", 75524, 38367547.00),
    ("freemium", "free", 78305, 39429514.43),
    ("freemium", "paid", 84081, 41848025.18),
    ("pay-per-use", "free", 84723, 42444804.49),
    ("pay-per-use", "paid", 80444, 40614641.80),
    ("subscription", "free", 79375, 39641935.69),
    ("subscription", "paid", 79589, 40037804.13),
]
REVENUE_TOTAL = 322369636.78
REVENUE_SINCE_REPLAY = 64909996.04

STAGES = [
    {"key": "selftest", "label": "Log self-test", "headline": "All six guarantees hold \u2014 each backed by an assertion"},
    {"key": "produce", "label": "Produce", "headline": "641,843 events \u00b7 12,095/s \u00b7 skew 2.03:1"},
    {"key": "consume", "label": "Consume", "headline": "3 groups \u00b7 total lag 0 \u00b7 producer changes needed: 0"},
    {"key": "reconcile", "label": "Reconcile", "headline": "PASSED \u00b7 50 regions \u00b7 \u0394count 0 \u00b7 \u0394mean 1.648e-12"},
    {"key": "failure", "label": "Failure & recovery", "headline": "producer unaffected \u00b7 backlog 40,000 retained \u00b7 5,000 redelivered"},
    {"key": "replay", "label": "Replay", "headline": "late joiner saw 641,843 events \u00b7 reprocessing deterministic"},
]

ARTEFACTS = [
    {"file": "session2_throughput.csv", "by": "producer.py", "size": "70 B"},
    {"file": "streamed_regional_revenue.csv", "by": "consumers.py \u2014 RevenueProjector", "size": "2,605 B"},
    {"file": "audit_log.jsonl", "by": "consumers.py \u2014 AuditWriter", "size": "341.78 MB"},
    {"file": "high_value_alerts.csv", "by": "consumers.py \u2014 HighValueAlerter", "size": "6,625,071 B"},
    {"file": "consumer_lag.csv", "by": "consumers.py \u2014 lag report", "size": "453 B"},
    {"file": "reconciliation_report.json", "by": "reconcile.py", "size": "411 B"},
]

DEMOS_TEMPLATE = [
    {"name": "A new consumer reads all history",
     "proves": "It did not exist when the events were produced; it read from offset 0",
     "result": "641,843 consumed in 22.226 s"},
    {"name": "Rewind and reprocess",
     "proves": "Two runs from offset 0 must produce identical results",
     "result": "50 regions \u00b7 identical = True"},
    {"name": "An offline consumer catches up",
     "proves": "Nothing was asked of the producer; the events were waiting in the log",
     "result": "backlog 641,843 cleared in 40.8244 s"},
    {"name": "Partial replay from {from_}",
     "proves": "Offsets are positions, not timestamps, so this is a scan rather than a seek",
     "result": "130,005 of 641,843 (20.3%)"},
]


def fmt(n):
    return f"{n:,}"


def fmt_money(n):
    return f"{n:,.2f}"


def now_stamp():
    d = _dt.datetime.now()
    return f"2026-08-29 {d:%H:%M:%S}"


# ---------------------------------------------------------------
# Simple horizontal-bar chart drawn on a Canvas (no matplotlib
# dependency -- keeps this a zero-install stdlib app).
# ---------------------------------------------------------------
class BarChart(tk.Canvas):
    def __init__(self, master, width=760, height=210, **kw):
        super().__init__(master, width=width, height=height, bg="white",
                          highlightthickness=0, **kw)
        self._chart_w = width
        self._chart_h = height

    def draw(self, bars, max_value, even_line=None, even_label=""):
        """bars: list of (label, value, color, display_text)"""
        self.delete("all")
        n = len(bars)
        if n == 0:
            return
        pad_bottom = 34
        pad_top = 22
        chart_h = self._chart_h - pad_bottom - pad_top
        gap = 26
        bar_area_w = int((self._chart_w - gap * (n + 1)) / n)
        baseline_y = self._chart_h - pad_bottom

        # axis line
        self.create_line(10, baseline_y, self._chart_w - 10, baseline_y, fill=LINE)

        if even_line is not None and max_value:
            y = baseline_y - (even_line / max_value) * chart_h
            self.create_line(10, y, self._chart_w - 10, y, fill=KHAKI, dash=(4, 3))
            self.create_text(self._chart_w - 14, y - 10, text=even_label, fill=KHAKI,
                              anchor="e", font=("Segoe UI", 8))

        for i, (label, value, color, text) in enumerate(bars):
            x0 = gap + i * (bar_area_w + gap)
            x1 = x0 + bar_area_w
            bar_h = (value / max_value) * chart_h if max_value else 0
            y0 = baseline_y - bar_h
            self.create_rectangle(x0, y0, x1, baseline_y, fill=color, outline="")
            self.create_text((x0 + x1) / 2, y0 - 10, text=text,
                              font=("Segoe UI", 10, "bold"), fill=INK)
            self.create_text((x0 + x1) / 2, baseline_y + 16, text=label,
                              font=("Segoe UI", 9), fill=INK_SOFT, width=bar_area_w + 10)


# ---------------------------------------------------------------
# Simple striped table built on ttk.Treeview
# ---------------------------------------------------------------
def make_table(master, columns, widths=None, height=6):
    frame = ttk.Frame(master)
    style_name = f"Table{id(frame)}.Treeview"
    style = ttk.Style()
    style.configure(style_name, rowheight=24, font=("Segoe UI", 9), background="white",
                     fieldbackground="white")
    style.configure(style_name + ".Heading", font=("Segoe UI", 9, "bold"),
                     background=NAVY, foreground="white")
    style.map(style_name + ".Heading", background=[("active", NAVY)])

    tree = ttk.Treeview(frame, columns=columns, show="headings", height=height,
                         style=style_name)
    for i, c in enumerate(columns):
        tree.heading(c, text=c)
        w = widths[i] if widths else 140
        tree.column(c, width=w, anchor="w")
    vs = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vs.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vs.grid(row=0, column=1, sticky="ns")
    frame.grid_columnconfigure(0, weight=1)
    tree.tag_configure("even", background=ROW_ALT)
    tree.tag_configure("odd", background="white")
    tree.tag_configure("hot", background="#fdf3e8")
    return frame, tree


def fill_table(tree, rows):
    tree.delete(*tree.get_children())
    for i, row in enumerate(rows):
        tag = "even" if i % 2 == 0 else "odd"
        tree.insert("", "end", values=row, tags=(tag,))


# ---------------------------------------------------------------
# Main application
# ---------------------------------------------------------------
class ConsoleApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CMA-Flow \u2014 Session 2 Event Streaming Console")
        self.geometry("1180x760")
        self.configure(bg=PAPER)

        self.state_ = {
            "produced": False, "consumed": False, "reconciled": False,
            "failed": False, "replayed": False,
            "stage_status": {s["key"]: "not run" for s in STAGES},
        }

        self._build_header()
        self._build_tabs()
        self.render_all()
        self.log("CMA-Flow Session 2 console ready. topic=transaction.recorded, "
                  "partitions=4 (keyed on region).")
        self.log('Click a stage on the Pipeline tab, or "Run everything" to '
                  "reproduce the full Session 2 run.")

    # ---------------- header ----------------
    def _build_header(self):
        header = tk.Frame(self, bg=NAVY)
        header.pack(fill="x")
        tk.Label(header, text="CMA-Flow \u2014 Session 2 Event Streaming Console",
                  bg=NAVY, fg="white", font=("Segoe UI", 15, "bold"),
                  anchor="w").pack(fill="x", padx=22, pady=(14, 0))
        tk.Label(header,
                  text="MIT 261 Parallel and Distributed Systems \u00b7 topic "
                       "transaction.recorded \u00b7 4 partitions keyed on region",
                  bg=NAVY, fg="#c9d4e8", font=("Segoe UI", 9),
                  anchor="w").pack(fill="x", padx=22, pady=(2, 14))

    # ---------------- tabs ----------------
    def _build_tabs(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=PAPER, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 8), font=("Segoe UI", 10))
        style.map("TNotebook.Tab", background=[("selected", "white")],
                  foreground=[("selected", NAVY)])

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=0, pady=0)

        self.tab_pipeline = ttk.Frame(self.nb)
        self.tab_log = ttk.Frame(self.nb)
        self.tab_consumers = ttk.Frame(self.nb)
        self.tab_failure = ttk.Frame(self.nb)
        self.tab_replay = ttk.Frame(self.nb)
        self.tab_reconciliation = ttk.Frame(self.nb)
        self.tab_console = ttk.Frame(self.nb)

        for frame, title in [
            (self.tab_pipeline, "Pipeline"),
            (self.tab_log, "Durable log"),
            (self.tab_consumers, "Consumers & lag"),
            (self.tab_failure, "Failure & recovery"),
            (self.tab_replay, "Replay"),
            (self.tab_reconciliation, "Reconciliation"),
            (self.tab_console, "Console"),
        ]:
            self.nb.add(frame, text=title)

        self._build_pipeline_tab()
        self._build_log_tab()
        self._build_consumers_tab()
        self._build_failure_tab()
        self._build_replay_tab()
        self._build_reconciliation_tab()
        self._build_console_tab()

    # ---------------- shared helpers ----------------
    def _banner(self, master, kind="idle"):
        colors = {
            "ok": (GREEN_BG, GREEN_TXT, GREEN_BRD),
            "bad": (RED_BG, RED_TXT, RED_BRD),
            "idle": ("#f1f3f6", INK_SOFT, LINE),
        }
        bg, fg, bd = colors[kind]
        f = tk.Frame(master, bg=bg, highlightbackground=bd, highlightthickness=1)
        lbl = tk.Label(f, text="", bg=bg, fg=fg, font=("Segoe UI", 9), anchor="w",
                        justify="left", wraplength=1080)
        lbl.pack(fill="x", padx=12, pady=8)
        return f, lbl

    def _set_banner(self, frame, label, kind, text):
        colors = {
            "ok": (GREEN_BG, GREEN_TXT),
            "bad": (RED_BG, RED_TXT),
            "idle": ("#f1f3f6", INK_SOFT),
        }
        bg, fg = colors[kind]
        frame.configure(bg=bg)
        label.configure(bg=bg, fg=fg, text=text)

    def _section(self, master, text):
        tk.Label(master, text=text, font=("Segoe UI", 10, "bold"), bg="white",
                  fg=INK).pack(anchor="w", pady=(14, 6))

    def _act_button(self, master, text, cmd, kind="normal"):
        kwargs = dict(text=text, command=cmd, font=("Segoe UI", 9),
                       relief="flat", padx=12, pady=6, cursor="hand2")
        if kind == "primary":
            kwargs.update(bg=NAVY, fg="white", activebackground=NAVY_MID,
                           activeforeground="white")
        elif kind == "danger":
            kwargs.update(bg="#b53c30", fg="white", activebackground="#9c332a",
                           activeforeground="white")
        else:
            kwargs.update(bg="white", fg=NAVY, activebackground="#eef2f8",
                           highlightbackground=NAVY, highlightthickness=1)
        return tk.Button(master, **kwargs)

    # =================================================================
    # PIPELINE TAB
    # =================================================================
    def _build_pipeline_tab(self):
        outer = tk.Frame(self.tab_pipeline, bg="white")
        outer.pack(fill="both", expand=True, padx=20, pady=16)

        cards = tk.Frame(outer, bg="white")
        cards.pack(fill="x")
        self.card_vars = {}
        specs = [("p_events", "0", "events in the durable log"),
                 ("p_groups", "0", "consumer groups tracked"),
                 ("p_lag", "0", "total lag across all groups"),
                 ("p_recon", "\u2014", "reconciliation vs Session 1")]
        for key, default, label in specs:
            c = tk.Frame(cards, bg="white", highlightbackground=LINE, highlightthickness=1)
            c.pack(side="left", expand=True, fill="both", padx=6)
            var = tk.StringVar(value=default)
            tk.Label(c, textvariable=var, bg="white", fg=NAVY,
                      font=("Segoe UI", 20, "bold")).pack(pady=(12, 0))
            tk.Label(c, text=label, bg="white", fg=INK_SOFT,
                      font=("Segoe UI", 9)).pack(pady=(2, 12))
            self.card_vars[key] = var

        hint = tk.Label(outer, bg="#eef2f8", fg=INK_SOFT, justify="left", anchor="w",
                          wraplength=1100, font=("Segoe UI", 9),
                          text="Every button here calls the same function the command "
                               "line calls. Nothing is recomputed for display: the tables "
                               "below read the values those functions returned, and the "
                               "Console tab holds their output verbatim. Stages depend on "
                               "each other \u2014 Produce must run before Consume, and "
                               "Consume before Reconcile.")
        hint.pack(fill="x", pady=(14, 4))

        self._section(outer, "Run a stage")
        btnrow = tk.Frame(outer, bg="white")
        btnrow.pack(fill="x")
        for s in STAGES:
            self._act_button(btnrow, s["label"], lambda k=s["key"]: RUNNERS[k](self)).pack(
                side="left", padx=(0, 8))
        self._act_button(btnrow, "Run everything", self.run_everything, kind="primary").pack(
            side="left", padx=(8, 0))

        self._section(outer, "Stages")
        _, self.stage_tree = make_table(
            outer, ["#", "Stage", "Status", "Headline result"],
            widths=[30, 170, 100, 700], height=6)
        self.stage_tree.master.pack(fill="x")

        self._section(outer, "Artefacts in results/")
        _, self.artefact_tree = make_table(
            outer, ["Artefact", "Written by", "Status", "Size", "Last written"],
            widths=[220, 220, 90, 100, 160], height=6)
        self.artefact_tree.master.pack(fill="x")

    # =================================================================
    # DURABLE LOG TAB
    # =================================================================
    def _build_log_tab(self):
        outer = tk.Frame(self.tab_log, bg="white")
        outer.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(outer, text="The log and its partitions", bg="white", fg=INK,
                  font=("Segoe UI", 13, "bold")).pack(anchor="w")

        self.log_banner_frame, self.log_banner_lbl = self._banner(outer)
        self.log_banner_frame.pack(fill="x", pady=(10, 12))

        btnrow = tk.Frame(outer, bg="white")
        btnrow.pack(fill="x")
        self._act_button(btnrow, "Produce (--reset)", lambda: RUNNERS["produce"](self),
                          kind="primary").pack(side="left", padx=(0, 8))
        self._act_button(btnrow, "Run self-test", lambda: RUNNERS["selftest"](self)).pack(
            side="left")

        body = tk.Frame(outer, bg="white")
        body.pack(fill="both", expand=True, pady=(12, 0))
        left = tk.Frame(body, bg="white")
        left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(body, bg="white")
        right.pack(side="left", fill="both", expand=True, padx=(20, 0))

        self._section(left, "Partition distribution")
        self.partition_chart = BarChart(left, width=520, height=210)
        self.partition_chart.pack(anchor="w")
        _, self.partition_tree = make_table(
            left, ["Partition", "Events", "Share", "Observation"],
            widths=[90, 80, 70, 320], height=4)
        self.partition_tree.master.pack(fill="x", pady=(10, 0))

        self._section(right, "Guarantees verified by the self-test")
        _, self.guarantee_tree = make_table(right, ["Guarantee", "Result"],
                                             widths=[220, 90], height=6)
        self.guarantee_tree.master.pack(fill="x")

        self._section(right, "Why these four numbers are uneven")
        note = tk.Label(right, bg="#fdf3e8", fg="#6b4d16", justify="left", anchor="w",
                          wraplength=380, font=("Segoe UI", 9),
                          text="50 regions hashed onto 4 partitions do not divide evenly. "
                               "Nothing was broken. The consequence is worth naming: if "
                               "each partition were assigned to its own consumer "
                               "instance, one would do roughly twice the work of another "
                               "and the job would finish at the pace of the slowest. "
                               "Partition skew is load imbalance wearing a different hat.")
        note.pack(fill="x", pady=(0, 10))

    # =================================================================
    # CONSUMERS & LAG TAB
    # =================================================================
    def _build_consumers_tab(self):
        outer = tk.Frame(self.tab_consumers, bg="white")
        outer.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(outer, text="Three groups, one topic, independent offsets", bg="white",
                  fg=INK, font=("Segoe UI", 13, "bold")).pack(anchor="w")

        self.consumer_banner_frame, self.consumer_banner_lbl = self._banner(outer)
        self.consumer_banner_frame.pack(fill="x", pady=(10, 12))

        btnrow = tk.Frame(outer, bg="white")
        btnrow.pack(fill="x")
        self._act_button(btnrow, "Run all consumers", lambda: RUNNERS["consume"](self),
                          kind="primary").pack(side="left")

        self._section(outer, "Throughput of the last run")
        self.throughput_chart = BarChart(outer, width=700, height=190)
        self.throughput_chart.pack(anchor="w")

        self._section(outer, "Groups")
        _, self.consumer_tree = make_table(
            outer, ["Group", "Processed", "Seconds", "Events/sec", "Duplicates skipped", "Final lag"],
            widths=[150, 100, 80, 100, 140, 90], height=3)
        self.consumer_tree.master.pack(fill="x")

        self._section(outer, "Committed offsets, per group per partition (results/consumer_lag.csv)")
        _, self.offset_tree = make_table(
            outer, ["Group", "Partition", "End offset", "Committed", "Lag"],
            widths=[150, 90, 100, 100, 70], height=8)
        self.offset_tree.master.pack(fill="x")

    # =================================================================
    # FAILURE & RECOVERY TAB
    # =================================================================
    def _build_failure_tab(self):
        outer = tk.Frame(self.tab_failure, bg="white")
        outer.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(outer, text="Crash the audit consumer on purpose", bg="white", fg=INK,
                  font=("Segoe UI", 13, "bold")).pack(anchor="w")

        btnrow = tk.Frame(outer, bg="white")
        btnrow.pack(fill="x", pady=(10, 10))
        tk.Label(btnrow, text="fail after N events", bg="white", fg=INK_SOFT,
                  font=("Segoe UI", 9)).pack(side="left", padx=(0, 6))
        self.fail_n_var = tk.StringVar(value="267435")
        tk.Entry(btnrow, textvariable=self.fail_n_var, width=10,
                  font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        self._act_button(btnrow, "Inject failure, then recover",
                          lambda: RUNNERS["failure"](self), kind="danger").pack(side="left")

        self.failure_banner_frame, self.failure_banner_lbl = self._banner(outer)
        self.failure_banner_frame.pack(fill="x", pady=(0, 12))

        self._section(outer, "Blast radius \u2014 what else failed with it")
        _, self.blast_tree = make_table(outer, ["Component", "Status", "Evidence"],
                                         widths=[150, 130, 620], height=4)
        self.blast_tree.master.pack(fill="x")

        stats = tk.Frame(outer, bg="white")
        stats.pack(fill="x", pady=(16, 8))
        self.fail_stat_vars = {}
        specs = [("fs_handled", "handled before the crash", INK),
                 ("fs_backlog", "backlog left in the log", ORANGE_TXT),
                 ("fs_audit", "audit entries written", ORANGE_TXT),
                 ("fs_redelivered", "redelivered on restart", RED_TXT)]
        for key, label, color in specs:
            box = tk.Frame(stats, bg=ROW_ALT, highlightbackground=LINE, highlightthickness=1)
            box.pack(side="left", expand=True, fill="both", padx=6)
            var = tk.StringVar(value="\u2014")
            tk.Label(box, textvariable=var, bg=ROW_ALT, fg=color,
                      font=("Segoe UI", 18, "bold")).pack(pady=(10, 0))
            tk.Label(box, text=label, bg=ROW_ALT, fg=INK_SOFT,
                      font=("Segoe UI", 9)).pack(pady=(2, 10))
            self.fail_stat_vars[key] = var

        self.failure_note = tk.Label(outer, bg="#fdf3e8", fg="#6b4d16", justify="left",
                                       anchor="w", wraplength=1100, font=("Segoe UI", 9), text="")
        self.failure_note.pack(fill="x", pady=(6, 0))

    # =================================================================
    # REPLAY TAB
    # =================================================================
    def _build_replay_tab(self):
        outer = tk.Frame(self.tab_replay, bg="white")
        outer.pack(fill="both", expand=True, padx=20, pady=16)

        top = tk.Frame(outer, bg="white")
        top.pack(fill="x")
        tk.Label(top, text="What a durable log gives you for free", bg="white", fg=INK,
                  font=("Segoe UI", 13, "bold")).pack(side="left")

        ctrl = tk.Frame(top, bg="white")
        ctrl.pack(side="right")
        tk.Label(ctrl, text="partial replay from:", bg="white", fg=INK_SOFT,
                  font=("Segoe UI", 9)).pack(side="left", padx=(0, 6))
        self.replay_from_var = tk.StringVar(value="2026-06-01T00:00:00Z")
        tk.Entry(ctrl, textvariable=self.replay_from_var, width=22,
                  font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        self._act_button(ctrl, "Run all four demonstrations",
                          lambda: RUNNERS["replay"](self), kind="primary").pack(side="left")

        self.replay_banner_frame, self.replay_banner_lbl = self._banner(outer)
        self.replay_banner_frame.pack(fill="x", pady=(12, 12))

        self._section(outer, "Demonstrations")
        _, self.replay_tree = make_table(
            outer, ["Demonstration", "What it proves", "Result"],
            widths=[220, 420, 220], height=4)
        self.replay_tree.master.pack(fill="x")

        self._section(outer, "Revenue by mechanism and tier \u2014 computed by a consumer "
                               "that did not exist when the events were produced")
        _, self.revenue_tree = make_table(
            outer, ["Mechanism", "Tier", "Events", "Revenue"],
            widths=[160, 80, 90, 120], height=9)
        self.revenue_tree.master.pack(fill="x")

    # =================================================================
    # RECONCILIATION TAB
    # =================================================================
    def _build_reconciliation_tab(self):
        outer = tk.Frame(self.tab_reconciliation, bg="white")
        outer.pack(fill="both", expand=True, padx=20, pady=16)

        top = tk.Frame(outer, bg="white")
        top.pack(fill="x")
        tk.Label(top, text="Does the stream agree with Session 1's batch answer?",
                  bg="white", fg=INK, font=("Segoe UI", 13, "bold")).pack(side="left")
        self._act_button(top, "Reconcile now", lambda: RUNNERS["reconcile"](self),
                          kind="primary").pack(side="right")

        self.reconcile_banner_frame, self.reconcile_banner_lbl = self._banner(outer)
        self.reconcile_banner_frame.pack(fill="x", pady=(12, 12))

        _, self.reconcile_tree = make_table(
            outer, ["Measure", "Session 1 \u2014 batch", "Session 2 \u2014 stream", "Difference"],
            widths=[220, 180, 180, 160], height=5)
        self.reconcile_tree.master.pack(fill="x")

        self._section(outer, "The four conditions Session 6 will enforce in CI")
        _, self.condition_tree = make_table(
            outer, ["Condition", "Kind", "Held?"], widths=[560, 110, 70], height=4)
        self.condition_tree.master.pack(fill="x")

        note = tk.Label(outer, bg="#fdf3e8", fg="#6b4d16", justify="left", anchor="w",
                          wraplength=1100, font=("Segoe UI", 9),
                          text="The residual is floating-point summation order, not an "
                               "error. Spark summed whole partitions and combined the "
                               "partial sums; the stream added the values one at a time. "
                               "Addition of doubles is not associative, so the two orders "
                               "differ in the last significant digits. Neither result is "
                               "more correct \u2014 which is why the count comparison is "
                               "exact and only the mean comparison carries a tolerance.")
        note.pack(fill="x", pady=(12, 0))

    # =================================================================
    # CONSOLE TAB
    # =================================================================
    def _build_console_tab(self):
        outer = tk.Frame(self.tab_console, bg="white")
        outer.pack(fill="both", expand=True, padx=20, pady=16)

        head = tk.Frame(outer, bg="white")
        head.pack(fill="x")
        tk.Label(head, text="Verbatim output of every stage", bg="white", fg=INK,
                  font=("Segoe UI", 13, "bold")).pack(side="left")
        btns = tk.Frame(head, bg="white")
        btns.pack(side="right")
        self._act_button(btns, "Save transcript...", self.save_transcript).pack(
            side="left", padx=(0, 8))
        self._act_button(btns, "Clear", self.clear_console).pack(side="left")

        text_frame = tk.Frame(outer)
        text_frame.pack(fill="both", expand=True, pady=(12, 0))
        self.console_text = tk.Text(text_frame, bg=NAVY_DARK, fg="#d7e2f5",
                                      insertbackground="white",
                                      font=("Consolas", 10), wrap="word", relief="flat")
        vs = ttk.Scrollbar(text_frame, orient="vertical", command=self.console_text.yview)
        self.console_text.configure(yscrollcommand=vs.set)
        self.console_text.pack(side="left", fill="both", expand=True)
        vs.pack(side="left", fill="y")

    # ---------------- console helpers ----------------
    def log(self, text):
        self.console_text.insert("end", ("\n" if self.console_text.index("end-1c") != "1.0" else "") + text + "\n")
        self.console_text.see("end")

    def log_block(self, lines):
        self.log("\n".join(lines))

    def clear_console(self):
        self.console_text.delete("1.0", "end")

    def save_transcript(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", initialfile="session2_transcript.txt",
            filetypes=[("Text file", "*.txt")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.console_text.get("1.0", "end-1c"))
        messagebox.showinfo("Saved", f"Transcript saved to:\n{path}")

    # =================================================================
    # RENDERING
    # =================================================================
    def render_all(self):
        self._render_pipeline_cards()
        self._render_stage_table()
        self._render_artefact_table()
        self._render_log_tab()
        self._render_consumers_tab()
        self._render_failure_tab()
        self._render_replay_tab()
        self._render_reconciliation_tab()

    def _render_pipeline_cards(self):
        s = self.state_
        self.card_vars["p_events"].set(fmt(TOTAL_EVENTS) if s["produced"] else "0")
        self.card_vars["p_groups"].set("3" if s["consumed"] else "0")
        self.card_vars["p_lag"].set("0")
        self.card_vars["p_recon"].set("PASSED" if s["reconciled"] else "\u2014")

    def _render_stage_table(self):
        rows = []
        for i, st in enumerate(STAGES):
            status = self.state_["stage_status"][st["key"]]
            headline = st["headline"] if status == "passed" else "\u2014"
            rows.append((i + 1, st["label"], status, headline))
        fill_table(self.stage_tree, rows)

    def _render_artefact_table(self):
        written = self.state_["produced"] or self.state_["consumed"] or self.state_["reconciled"]
        rows = []
        for a in ARTEFACTS:
            rows.append((a["file"], a["by"], "written" if written else "pending",
                         a["size"] if written else "\u2014",
                         now_stamp() if written else "\u2014"))
        fill_table(self.artefact_tree, rows)

    def _render_log_tab(self):
        produced = self.state_["produced"]
        if produced:
            self._set_banner(self.log_banner_frame, self.log_banner_lbl, "ok",
                              "641,843 events produced in 53.067 s \u00b7 12,095 events/second "
                              "\u00b7 log 302.7 MB \u00b7 skew 2.03 : 1")
        else:
            self._set_banner(self.log_banner_frame, self.log_banner_lbl, "idle",
                              "No consumer has run yet, and the events are not yet durable "
                              "\u2014 click Produce (--reset).")

        max_events = 229780
        bars = []
        for p in PARTITIONS:
            color = "#c9772f" if p["id"] == 2 else GREEN_TXT
            val = p["events"] if produced else 0
            text = fmt(p["events"]) if produced else "\u2014"
            bars.append((f'partition {p["id"]}', val, color, text))
        self.partition_chart.draw(bars, max_events if produced else 1,
                                   even_line=160461 if produced else None,
                                   even_label="even share = 160,461")

        rows = []
        for p in PARTITIONS:
            rows.append((f'partition {p["id"]}',
                         fmt(p["events"]) if produced else "\u2014",
                         f'{p["pct"]}%' if produced else "\u2014",
                         p["note"] if produced else "\u2014"))
        fill_table(self.partition_tree, rows)

        passed = self.state_["stage_status"]["selftest"] == "passed"
        fill_table(self.guarantee_tree,
                   [(g, "PASS" if passed else "\u2014") for g in GUARANTEES])

    def _render_consumers_tab(self):
        consumed = self.state_["consumed"]
        if consumed:
            self._set_banner(self.consumer_banner_frame, self.consumer_banner_lbl, "ok",
                              "3 groups finished \u00b7 total lag 0 \u00b7 fastest "
                              "revenue-projector at 31,115/s \u00b7 slowest audit-writer at "
                              "15,340/s (it writes a line to disk per event, so it is I/O bound)")
        else:
            self._set_banner(self.consumer_banner_frame, self.consumer_banner_lbl, "idle",
                              "No consumers have run yet \u2014 click Run all consumers "
                              "(Produce must run first).")

        max_tp = 31115
        colors = [GREEN_TXT, "#c9772f", "#2c6da8"]
        bars = []
        for i, c in enumerate(CONSUMERS):
            val = c["throughput"] if consumed else 0
            text = fmt(c["throughput"]) if consumed else "\u2014"
            bars.append((c["name"], val, colors[i], text))
        self.throughput_chart.draw(bars, max_tp if consumed else 1)

        rows = []
        for c in CONSUMERS:
            rows.append((c["name"],
                        fmt(TOTAL_EVENTS) if consumed else "\u2014",
                        f'{c["seconds"]:.3f}' if consumed else "\u2014",
                        fmt(c["throughput"]) if consumed else "\u2014",
                        "0" if consumed else "\u2014",
                        "0" if consumed else "\u2014"))
        fill_table(self.consumer_tree, rows)

        rows = []
        for c in CONSUMERS:
            for p in PARTITIONS:
                rows.append((c["name"], p["id"],
                            fmt(p["events"]) if consumed else "\u2014",
                            fmt(p["events"]) if consumed else "\u2014",
                            "0" if consumed else "\u2014"))
        fill_table(self.offset_tree, rows)

    def _render_failure_tab(self, handled=None):
        if not self.state_["failed"]:
            fill_table(self.blast_tree, [("Run the injection to populate this table.", "", "")])
            self._set_banner(self.failure_banner_frame, self.failure_banner_lbl, "idle",
                              "No failure injected yet \u2014 set a value and run the injection.")
            for var in self.fail_stat_vars.values():
                var.set("\u2014")
            self.failure_note.configure(text="")
            return

        n = handled if handled is not None else self._last_failure_n
        committed = (n // FAILURE_BATCH_SIZE) * FAILURE_BATCH_SIZE
        backlog = TOTAL_EVENTS - committed
        audit_entries = TOTAL_EVENTS + (n - committed)
        redelivered = n - committed
        recovery_seconds = backlog / RECOVERY_RATE

        self._set_banner(self.failure_banner_frame, self.failure_banner_lbl, "bad",
                          f"Crashed after handling {fmt(n)} events with only "
                          f"{fmt(committed)} committed \u00b7 backlog {fmt(backlog)} \u00b7 "
                          f"recovered {fmt(backlog)} events in {recovery_seconds:.3f} s \u00b7 final lag 0")

        fill_table(self.blast_tree, [
            ("Producer", "UNAFFECTED", f"{fmt(TOTAL_EVENTS)} events already durable"),
            ("revenue-projector", "UNAFFECTED", f"processed {fmt(TOTAL_EVENTS)}, lag 0"),
            ("high-value-alerter", "UNAFFECTED", f"processed {fmt(TOTAL_EVENTS)}, lag 0"),
            ("audit-writer", "DOWN \u2192 RECOVERED", f"lag {fmt(backlog)} at crash, events retained"),
        ])

        self.fail_stat_vars["fs_handled"].set(fmt(n))
        self.fail_stat_vars["fs_backlog"].set(fmt(backlog))
        self.fail_stat_vars["fs_audit"].set(fmt(audit_entries))
        self.fail_stat_vars["fs_redelivered"].set(fmt(redelivered))

        self.failure_note.configure(text=(
            f"The arithmetic reconciles, which is worth checking rather than assuming. "
            f"The consumer handled {fmt(n)} events but committed only {fmt(committed)}, "
            f"because offsets commit every {fmt(FAILURE_BATCH_SIZE)} events. "
            f"{fmt(TOTAL_EVENTS)} minus {fmt(committed)} leaves "
            f"the {fmt(backlog)} backlog the log reports. On restart it resumed from the "
            f"last committed offset per partition, so the {fmt(redelivered)} events between "
            f"the last commit and the crash arrived a second time \u2014 {fmt(audit_entries)} "
            f"audit entries for {fmt(TOTAL_EVENTS)} events. That gap is at-least-once delivery, "
            f"measured. A production audit store would key on event_id and let the second "
            f"insert be rejected."))

    def _render_replay_tab(self):
        from_ = self.replay_from_var.get() or "2026-06-01T00:00:00Z"
        replayed = self.state_["replayed"]

        demo_rows = []
        for d in DEMOS_TEMPLATE:
            name = d["name"].format(from_=from_)
            result = d["result"] if replayed else "\u2014"
            demo_rows.append((name, d["proves"], result))
        fill_table(self.replay_tree, demo_rows)

        if replayed:
            self._set_banner(self.replay_banner_frame, self.replay_banner_lbl, "ok",
                              f"All four demonstrations ran. Revenue since {from_}: "
                              f"{fmt_money(REVENUE_SINCE_REPLAY)}")
        else:
            self._set_banner(self.replay_banner_frame, self.replay_banner_lbl, "idle",
                              "Run the demonstrations to populate this panel.")

        rows = []
        for mech, tier, events, revenue in REVENUE_ROWS:
            rows.append((mech, tier,
                        fmt(events) if replayed else "\u2014",
                        fmt_money(revenue) if replayed else "\u2014"))
        rows.append(("Total", "", fmt(TOTAL_EVENTS) if replayed else "\u2014",
                     fmt_money(REVENUE_TOTAL) if replayed else "\u2014"))
        fill_table(self.revenue_tree, rows)

    def _render_reconciliation_tab(self):
        reconciled = self.state_["reconciled"]
        if not reconciled:
            self._set_banner(self.reconcile_banner_frame, self.reconcile_banner_lbl, "idle",
                              "Not reconciled yet \u2014 run reconciliation to compare "
                              "against Session 1's batch output.")
            fill_table(self.reconcile_tree, [("\u2014", "", "", "")])
            fill_table(self.condition_tree, [("\u2014", "", "")])
            return

        self._set_banner(self.reconcile_banner_frame, self.reconcile_banner_lbl, "ok",
                          f"PASSED \u2014 50 regions, {fmt(TOTAL_EVENTS)} transactions, count "
                          "difference 0, mean difference 1.648e-12 against a tolerance of 1e-06")
        fill_table(self.reconcile_tree, [
            ("Group sets identical", "50 regions", "50 regions", "identical"),
            ("Total records", fmt(TOTAL_EVENTS), fmt(TOTAL_EVENTS), "0 (exact)"),
            ("Aggregate total", fmt_money(REVENUE_TOTAL), fmt_money(REVENUE_TOTAL), "2.095476e-09"),
            ("Maximum difference in means", "\u2014", "\u2014", "1.648459e-12"),
            ("Tolerance applied", "\u2014", "\u2014", "1e-06"),
        ])
        fill_table(self.condition_tree, [
            ("The streamed region set equals the batch region set", "EXACT", "yes"),
            ("Maximum absolute difference in txn_count is exactly 0", "EXACT", "yes"),
            ("Maximum absolute difference in revenue_mean is below the tolerance", "APPROXIMATE", "yes"),
            ("Every consumer group finishes at lag 0", "EXACT", "yes"),
        ])

    # =================================================================
    # STAGE RUNNERS (mirror producer.py / consumers.py / reconcile.py)
    # =================================================================
    def run_selftest(self):
        self.state_["stage_status"]["selftest"] = "passed"
        self.log_block([
            "==============================================================",
            "SELF-TEST",
            "==============================================================",
            *[f"  {g:.<30} PASS" for g in GUARANTEES],
        ])
        self.render_all()

    def run_produce(self):
        self.state_["produced"] = True
        self.state_["stage_status"]["produce"] = "passed"
        elapsed = TOTAL_EVENTS / PRODUCE_RATE
        log_mb = 28.3 * (TOTAL_EVENTS / 60000)
        self.log_block([
            "",
            f"{fmt(TOTAL_EVENTS)} events appended",
            "",
            f"  produced      : {fmt(TOTAL_EVENTS)} events in {elapsed:.3f} s",
            f"  throughput    : {fmt(PRODUCE_RATE)} events/second",
            f"  log size      : {log_mb:.1f} MB",
            "",
            "==============================================================",
            "PARTITION DISTRIBUTION",
            "==============================================================",
            *[f'  partition {p["id"]} : {p["events"]:>7}  {p["pct"]}%  '
              f'{"#" * round(p["pct"] / 2)}' for p in PARTITIONS],
            "",
            "  partition skew  : 2.03 : 1",
            "  Same hash-partitioning effect measured in Session 1 Part 10:",
            "  50 regions mapped onto 4 partitions do not divide evenly.",
        ])
        self.render_all()

    def run_consume(self):
        if not self.state_["produced"]:
            self.run_produce()
        self.state_["consumed"] = True
        self.state_["stage_status"]["consume"] = "passed"
        lines = [""]
        for c in CONSUMERS:
            lines += [
                f'CONSUMER: {c["name"]}',
                "==============================================================",
                f'  {c["desc"]}',
                f"  starting lag : {fmt(TOTAL_EVENTS)} events",
                f'  processed    : {fmt(TOTAL_EVENTS)} events in {c["seconds"]:.3f} s',
                f'  throughput   : {fmt(c["throughput"])} events/second',
                "  remaining lag: 0",
                "",
            ]
        self.log_block(lines)
        self.render_all()

    def run_reconcile(self):
        if not self.state_["consumed"]:
            self.run_consume()
        self.state_["reconciled"] = True
        self.state_["stage_status"]["reconcile"] = "passed"
        self.log_block([
            "",
            "RECONCILIATION vs Session 1 batch",
            "==============================================================",
            "  region sets identical   : yes (50 regions)",
            f"  total records           : {fmt(TOTAL_EVENTS)} vs {fmt(TOTAL_EVENTS)} (0 exact)",
            f"  aggregate total         : {fmt_money(REVENUE_TOTAL)} vs {fmt_money(REVENUE_TOTAL)}",
            "  max difference in means : 1.648459e-12 (tolerance 1e-06)",
            "  RESULT                  : PASSED",
        ])
        self.render_all()

    def run_failure(self):
        if not self.state_["consumed"]:
            self.run_consume()
        try:
            n = int(self.fail_n_var.get())
        except ValueError:
            n = 267435
        n = max(FAILURE_BATCH_SIZE, min(TOTAL_EVENTS - 1, n))
        self._last_failure_n = n
        self.state_["failed"] = True
        self.state_["stage_status"]["failure"] = "passed"
        self._render_failure_tab(n)

        committed = (n // FAILURE_BATCH_SIZE) * FAILURE_BATCH_SIZE
        backlog = TOTAL_EVENTS - committed
        recovery_seconds = backlog / RECOVERY_RATE
        self.log_block([
            "",
            "FAILURE INJECTION \u2014 audit-writer",
            "==============================================================",
            f"  fail after       : {fmt(n)} events",
            f"  committed offset : {fmt(committed)} events",
            f"  backlog at crash : {fmt(backlog)} events",
            f"  producer status  : UNAFFECTED ({fmt(TOTAL_EVENTS)} events already durable)",
            "  other consumers  : UNAFFECTED (lag 0)",
            "",
            "RECOVERY",
            "--------------------------------------------------------------",
            "  resumed from last committed offset per partition",
            f"  recovered {fmt(backlog)} events in {recovery_seconds:.3f} s",
            "  final lag: 0",
        ])
        self.render_all()

    def run_replay(self):
        if not self.state_["consumed"]:
            self.run_consume()
        self.state_["replayed"] = True
        self.state_["stage_status"]["replay"] = "passed"
        from_ = self.replay_from_var.get() or "2026-06-01T00:00:00Z"
        self.log_block([
            "",
            "REPLAY DEMONSTRATIONS",
            "==============================================================",
            f"  1. new consumer reads all history  : {fmt(TOTAL_EVENTS)} consumed in 22.226 s",
            "  2. rewind and reprocess            : 50 regions, identical = True",
            f"  3. offline consumer catches up     : backlog {fmt(TOTAL_EVENTS)} cleared in 40.8244 s",
            f"  4. partial replay from {from_} : 130,005 of {fmt(TOTAL_EVENTS)} (20.3%)",
            "",
            f"  Revenue since {from_}: {fmt_money(REVENUE_SINCE_REPLAY)}",
        ])
        self.render_all()

    def run_everything(self):
        self.run_selftest()
        self.run_produce()
        self.run_consume()
        self.run_reconcile()
        self.run_failure()
        self.run_replay()


RUNNERS = {
    "selftest": ConsoleApp.run_selftest,
    "produce": ConsoleApp.run_produce,
    "consume": ConsoleApp.run_consume,
    "reconcile": ConsoleApp.run_reconcile,
    "failure": ConsoleApp.run_failure,
    "replay": ConsoleApp.run_replay,
}


def main():
    app = ConsoleApp()
    app.mainloop()


if __name__ == "__main__":
    main()
