#!/usr/bin/env python3
"""
render_diagrams.py -- Session 2 (CMA-Flow Event Streaming)
============================================================
Renders two Graphviz diagrams that document the Session 2 event
streaming pipeline, in the same style/tooling as Session 1's
render_diagrams.py:

  1. entity-model-session2.png
     The topic / partition / consumer-group entity relationships:
     one topic hash-partitioned into 4 partitions, read independently
     by 3 consumer groups, each tracking its own offsets.

  2. architecture-session2.png
     The end-to-end pipeline: producer -> durable log -> parallel
     consumers -> reconciliation against Session 1's batch answer,
     plus the failure/recovery and replay demonstrations the console
     app (cma_flow_session2.py) exercises.

Requires Graphviz's `dot` command to be on PATH. No other
third-party packages are needed.

Run with:
    python render_diagrams.py
"""

from pathlib import Path
import subprocess
import sys
import shutil

BASE_DIR = Path(__file__).resolve().parent
DOCS_OUT = BASE_DIR / "docs"
DOCS_OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------
# Figures pulled from cma_flow_session2.py, duplicated here as
# plain constants so this script has no import-time dependency on
# Tkinter (the console app imports tkinter at module scope).
# Keep these in sync if the console's numbers ever change.
# ---------------------------------------------------------------
TOTAL_EVENTS = 641_843
REGIONS = 50
PARTITIONS = [
    {"id": 0, "events": 182_711, "pct": 28.5},
    {"id": 1, "events": 115_960, "pct": 18.1},
    {"id": 2, "events": 229_780, "pct": 35.8},
    {"id": 3, "events": 113_392, "pct": 17.7},
]
CONSUMERS = [
    {"name": "revenue-projector", "seconds": 20.628, "throughput": 31_115},
    {"name": "audit-writer", "seconds": 41.841, "throughput": 15_340},
    {"name": "high-value-alerter", "seconds": 21.090, "throughput": 30_434},
]
PARTITION_SKEW = "2.03 : 1"
PRODUCE_ELAPSED = "53.067 s"
LOG_SIZE = "302.7 MB"


# =================================================================
# 1. ENTITY MODEL -- topic / partitions / consumer groups
# =================================================================
def build_entity_dot():
    partition_rows = "".join(
        f'<TR><TD ALIGN="LEFT">partition {p["id"]}</TD>'
        f'<TD ALIGN="RIGHT">{p["events"]:,}</TD>'
        f'<TD ALIGN="RIGHT">{p["pct"]}%</TD></TR>'
        for p in PARTITIONS
    )

    consumer_rows = "".join(
        f'<TR><TD ALIGN="LEFT">{c["name"]}</TD>'
        f'<TD ALIGN="RIGHT">{c["throughput"]:,}/s</TD>'
        f'<TD ALIGN="RIGHT">{c["seconds"]:.3f} s</TD></TR>'
        for c in CONSUMERS
    )

    return f"""
digraph CMAFlowEntities {{
    graph [
        rankdir=LR,
        bgcolor="white",
        pad="0.35",
        nodesep="0.7",
        ranksep="1.1",
        fontname="Arial"
    ];

    node [shape=plain, fontname="Arial"];
    edge [fontname="Arial", fontsize=10];

    TOPIC [
        label=<
        <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="7">
            <TR>
                <TD BGCOLOR="lightblue">
                    <B>TOPIC: transaction.recorded</B><BR/>
                    <FONT POINT-SIZE="10">Durable, append-only event log</FONT>
                </TD>
            </TR>
            <TR>
                <TD ALIGN="LEFT">
                    <B>key</B>: region ({REGIONS} distinct values)<BR/>
                    <B>partitions</B>: {len(PARTITIONS)}<BR/>
                    <B>total events</B>: {TOTAL_EVENTS:,}<BR/>
                    <B>log size</B>: {LOG_SIZE}<BR/>
                    <B>partition skew</B>: {PARTITION_SKEW}
                </TD>
            </TR>
        </TABLE>
        >
    ];

    PARTITIONS [
        label=<
        <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6">
            <TR>
                <TD BGCOLOR="khaki" COLSPAN="3"><B>PARTITIONS</B><BR/>
                    <FONT POINT-SIZE="10">hash(region) mod 4</FONT>
                </TD>
            </TR>
            <TR>
                <TD ALIGN="LEFT"><B>Partition</B></TD>
                <TD ALIGN="RIGHT"><B>Events</B></TD>
                <TD ALIGN="RIGHT"><B>Share</B></TD>
            </TR>
            {partition_rows}
        </TABLE>
        >
    ];

    CONSUMER_GROUPS [
        label=<
        <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6">
            <TR>
                <TD BGCOLOR="palegreen" COLSPAN="3"><B>CONSUMER GROUPS</B><BR/>
                    <FONT POINT-SIZE="10">each reads all 4 partitions, own offsets</FONT>
                </TD>
            </TR>
            <TR>
                <TD ALIGN="LEFT"><B>Group</B></TD>
                <TD ALIGN="RIGHT"><B>Throughput</B></TD>
                <TD ALIGN="RIGHT"><B>Elapsed</B></TD>
            </TR>
            {consumer_rows}
        </TABLE>
        >
    ];

    RECONCILIATION [
        label=<
        <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="7">
            <TR>
                <TD BGCOLOR="mistyrose">
                    <B>SESSION 1 BATCH ANSWER</B><BR/>
                    <FONT POINT-SIZE="10">results/session1_benchmark.csv</FONT>
                </TD>
            </TR>
            <TR>
                <TD ALIGN="LEFT">
                    {REGIONS} regions &middot; {TOTAL_EVENTS:,} rows<BR/>
                    compared against the stream on:<BR/>
                    region set, record count, revenue mean
                </TD>
            </TR>
        </TABLE>
        >
    ];

    TOPIC -> PARTITIONS [
        dir=both, arrowtail=tee, arrowhead=crow,
        label=" hash-partitioned\\n1 : {len(PARTITIONS)}"
    ];

    PARTITIONS -> CONSUMER_GROUPS [
        dir=both, arrowtail=crow, arrowhead=crow,
        label=" independent offsets\\n{len(PARTITIONS)} : {len(CONSUMERS)}"
    ];

    CONSUMER_GROUPS -> RECONCILIATION [
        style=dashed, color=gray,
        label=" revenue-projector output\\nvs Session 1 batch"
    ];
}}
"""


# =================================================================
# 2. ARCHITECTURE -- end-to-end pipeline
# =================================================================
def build_architecture_dot():
    return f"""
digraph CMAFlowArchitecture {{
    graph [
        rankdir=TB,
        bgcolor="white",
        pad="0.35",
        nodesep="0.55",
        ranksep="0.75",
        fontname="Arial",
        fontsize=16,
        label="CMA-Flow: Session 2 Event Streaming Architecture",
        labelloc="t"
    ];

    node [
        shape=box,
        style="rounded,filled",
        fontname="Arial",
        fontsize=11,
        margin="0.22,0.14"
    ];

    edge [fontname="Arial", fontsize=9];

    subgraph cluster_source {{
        label="Source";
        style="rounded";
        color="gray60";

        SOURCE [
            label="Session 1 working dataset\\n{TOTAL_EVENTS:,} sales transactions\\n(bm_sales.csv, joined)"
            fillcolor="lightblue"
        ];
    }}

    subgraph cluster_produce {{
        label="Producer";
        style="rounded";
        color="gray60";

        PRODUCE [
            label="producer.py\\nappend to topic.transaction.recorded\\nkey = region"
            fillcolor="palegreen"
        ];
        PARTITION [
            label="Hash-partition into 4\\nskew {PARTITION_SKEW} (50 regions -> 4 partitions)\\n{PRODUCE_ELAPSED} &middot; {LOG_SIZE}"
            fillcolor="palegreen"
        ];
    }}

    subgraph cluster_log {{
        label="Durable Log";
        style="rounded";
        color="gray60";

        LOG [
            label="Append-only, replayable log\\n{TOTAL_EVENTS:,} events durable\\noffsets are positions, not timestamps"
            fillcolor="khaki"
        ];
    }}

    subgraph cluster_consume {{
        label="Consumers (parallel, independent offsets)";
        style="rounded";
        color="gray60";

        REV [label="revenue-projector\\nregional revenue rebuild" fillcolor="mistyrose"];
        AUD [label="audit-writer\\nappend-only audit trail (I/O bound)" fillcolor="mistyrose"];
        ALERT [label="high-value-alerter\\nflags transactions > 900.00" fillcolor="mistyrose"];
    }}

    subgraph cluster_failure {{
        label="Failure & Recovery";
        style="rounded";
        color="gray60";

        CRASH [label="Inject crash on audit-writer\\nbacklog left in log" fillcolor="lightgrey"];
        RECOVER [label="Resume from last committed offset\\nat-least-once redelivery" fillcolor="lightgrey"];
    }}

    subgraph cluster_replay {{
        label="Replay";
        style="rounded";
        color="gray60";

        REPLAY [
            label="New / offline / rewound consumers\\nread history from offset 0\\nor a partial timestamp scan"
            fillcolor="lightcyan"
        ];
    }}

    subgraph cluster_reconcile {{
        label="Reconciliation";
        style="rounded";
        color="gray60";

        RECONCILE [
            label="reconcile.py\\nstream vs Session 1 batch\\nregion set, count, revenue mean"
            fillcolor="wheat"
        ];
    }}

    subgraph cluster_output {{
        label="Outputs";
        style="rounded";
        color="gray60";

        RESULTS [
            label="results/\\nthroughput, lag, reconciliation report"
            fillcolor="lightyellow"
        ];
        DOCS [
            label="docs/\\nentity model + architecture diagrams"
            fillcolor="lightyellow"
        ];
    }}

    SOURCE -> PRODUCE;
    PRODUCE -> PARTITION;
    PARTITION -> LOG;

    LOG -> REV;
    LOG -> AUD;
    LOG -> ALERT;

    AUD -> CRASH [style=dashed, color=gray, label=" fail after N events"];
    CRASH -> RECOVER;
    RECOVER -> AUD [style=dashed, color=gray, label=" lag returns to 0"];

    LOG -> REPLAY [style=dashed, color=gray, label=" offset 0 / partial scan"];

    REV -> RECONCILE;
    RECONCILE -> RESULTS;
    REPLAY -> RESULTS [style=dashed, color=gray];
    CRASH -> RESULTS [style=dashed, color=gray, label=" blast-radius evidence"];
    RESULTS -> DOCS [style=dashed, color=gray];
}}
"""


# =================================================================
# Rendering helper (same approach as Session 1's render_diagrams.py)
# =================================================================
def render(dot_source, output_png):
    if shutil.which("dot") is None:
        print("\nERROR: Graphviz 'dot' command was not found.")
        print("Install Graphviz and add its bin folder to your PATH.")
        print("Windows example PATH entry:")
        print(r"C:\Program Files\Graphviz\bin")
        return False

    dot_file = output_png.with_suffix(".dot")
    dot_file.write_text(dot_source, encoding="utf-8")

    try:
        subprocess.run(
            ["dot", "-Tpng", "-Gdpi=150", str(dot_file), "-o", str(output_png)],
            check=True,
        )
        print(f"\nDiagram successfully created:")
        print(output_png)
        return True
    except FileNotFoundError:
        print("\nERROR: Graphviz was not found.")
        print("Make sure Graphviz is installed and 'dot' is in PATH.")
        return False
    except subprocess.CalledProcessError as error:
        print("\nERROR: Graphviz failed to render the diagram.")
        print(error)
        return False


def main():
    print("=" * 60)
    print("CMA-Flow Session 2 Diagram Renderer")
    print("=" * 60)

    entity_output = DOCS_OUT / "entity-model-session2.png"
    architecture_output = DOCS_OUT / "architecture-session2.png"

    entity_success = render(build_entity_dot(), entity_output)
    architecture_success = render(build_architecture_dot(), architecture_output)

    if entity_success and architecture_success:
        print("\nRendering completed successfully.")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
