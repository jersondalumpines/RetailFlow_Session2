from pathlib import Path
import os
import shutil
import subprocess
import sys

# ============================================================
# RetailFlow - Session 2 Diagram Renderer
# Generates:
#   1. Entity Relationship Diagram (ERD)
#   2. Session 2 System / Data Architecture Diagram
#
# Requirements:
#   - Python 3.x
#   - Graphviz installed
#
# The diagrams are based on the BM_* tables represented in the
# previous diagram script:
#   BM_SALES, BM_CUSTOMERS, BM_STORES, BM_SKUS,
#   BM_INVENTORY, BM_PROMOTIONS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DOCS_OUT = BASE_DIR / "docs"
DOCS_OUT.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# SESSION 2 ENTITY / ER DIAGRAM
# ------------------------------------------------------------
ENTITY = r"""
digraph RetailFlowSession2ERD {
    graph [
        rankdir=LR,
        bgcolor="white",
        pad="0.35",
        nodesep="0.65",
        ranksep="1.0",
        fontname="Arial",
        labelloc="t",
        label="RetailFlow - Session 2 Entity Relationship Diagram",
        fontsize=18
    ];

    node [
        shape=plain,
        fontname="Arial"
    ];

    edge [
        fontname="Arial",
        fontsize=10,
        color="#555555"
    ];

    SALES [
        label=<
        <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="7">
            <TR>
                <TD BGCOLOR="lightblue">
                    <B>BM_SALES</B><BR/>
                    <FONT POINT-SIZE="10">Transaction / Fact Table</FONT>
                </TD>
            </TR>
            <TR>
                <TD ALIGN="LEFT">
                    <B>sale_id (PK)</B><BR/>
                    date<BR/>
                    <B>store_id (FK)</B><BR/>
                    <B>sku_id (FK)</B><BR/>
                    <B>customer_id (FK)</B><BR/>
                    quantity<BR/>
                    unit_price<BR/>
                    total_value<BR/>
                    channel<BR/>
                    discount_pct
                </TD>
            </TR>
        </TABLE>
        >
    ];

    CUSTOMERS [
        label=<
        <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="7">
            <TR>
                <TD BGCOLOR="palegreen">
                    <B>BM_CUSTOMERS</B><BR/>
                    <FONT POINT-SIZE="10">Customer Dimension</FONT>
                </TD>
            </TR>
            <TR>
                <TD ALIGN="LEFT">
                    <B>cust_id (PK)</B><BR/>
                    age<BR/>
                    gender<BR/>
                    city<BR/>
                    loyalty_segment<BR/>
                    preferred_channel<BR/>
                    registration_date
                </TD>
            </TR>
        </TABLE>
        >
    ];

    STORES [
        label=<
        <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="7">
            <TR>
                <TD BGCOLOR="palegreen">
                    <B>BM_STORES</B><BR/>
                    <FONT POINT-SIZE="10">Store Dimension</FONT>
                </TD>
            </TR>
            <TR>
                <TD ALIGN="LEFT">
                    <B>store_id (PK)</B><BR/>
                    store_name<BR/>
                    city<BR/>
                    store_type<BR/>
                    opening_date
                </TD>
            </TR>
        </TABLE>
        >
    ];

    SKUS [
        label=<
        <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="7">
            <TR>
                <TD BGCOLOR="palegreen">
                    <B>BM_SKUS</B><BR/>
                    <FONT POINT-SIZE="10">Product Dimension</FONT>
                </TD>
            </TR>
            <TR>
                <TD ALIGN="LEFT">
                    <B>sku_id (PK)</B><BR/>
                    sku_name<BR/>
                    category<BR/>
                    subcategory<BR/>
                    unit_price<BR/>
                    cost_price<BR/>
                    brand
                </TD>
            </TR>
        </TABLE>
        >
    ];

    INVENTORY [
        label=<
        <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="7">
            <TR>
                <TD BGCOLOR="khaki">
                    <B>BM_INVENTORY</B><BR/>
                    <FONT POINT-SIZE="10">Inventory Snapshot</FONT>
                </TD>
            </TR>
            <TR>
                <TD ALIGN="LEFT">
                    <B>inventory_id (PK)</B><BR/>
                    <B>store_id (FK)</B><BR/>
                    <B>sku_id (FK)</B><BR/>
                    stock_on_hand<BR/>
                    reorder_point<BR/>
                    safety_stock<BR/>
                    last_restock_date<BR/>
                    snapshot_date
                </TD>
            </TR>
        </TABLE>
        >
    ];

    PROMOTIONS [
        label=<
        <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="7">
            <TR>
                <TD BGCOLOR="mistyrose">
                    <B>BM_PROMOTIONS</B><BR/>
                    <FONT POINT-SIZE="10">Promotion Dimension</FONT>
                </TD>
            </TR>
            <TR>
                <TD ALIGN="LEFT">
                    <B>promo_id (PK)</B><BR/>
                    promo_name<BR/>
                    start_date<BR/>
                    end_date<BR/>
                    discount_pct<BR/>
                    promo_type
                </TD>
            </TR>
        </TABLE>
        >
    ];

    CUSTOMERS -> SALES [
        dir=both,
        arrowtail=tee,
        arrowhead=crow,
        label=" cust_id = customer_id\n1 : many"
    ];

    STORES -> SALES [
        dir=both,
        arrowtail=tee,
        arrowhead=crow,
        label=" store_id\n1 : many"
    ];

    SKUS -> SALES [
        dir=both,
        arrowtail=tee,
        arrowhead=crow,
        label=" sku_id\n1 : many"
    ];

    STORES -> INVENTORY [
        dir=both,
        arrowtail=tee,
        arrowhead=crow,
        label=" store_id\n1 : many"
    ];

    SKUS -> INVENTORY [
        dir=both,
        arrowtail=tee,
        arrowhead=crow,
        label=" sku_id\n1 : many"
    ];

    PROMOTIONS -> SALES [
        style=dashed,
        color="#888888",
        label=" date range / discount matching\n(no promo_id FK shown)"
    ];
}
"""


# ------------------------------------------------------------
# SESSION 2 ARCHITECTURE DIAGRAM
# ------------------------------------------------------------
ARCHITECTURE = r"""
digraph RetailFlowSession2Architecture {
    graph [
        rankdir=TB,
        bgcolor="white",
        pad="0.35",
        nodesep="0.55",
        ranksep="0.75",
        fontname="Arial",
        fontsize=16,
        label="RetailFlow - Session 2 Data Warehouse Architecture",
        labelloc="t"
    ];

    node [
        shape=box,
        style="rounded,filled",
        fontname="Arial",
        fontsize=11,
        margin="0.22,0.14"
    ];

    edge [
        fontname="Arial",
        fontsize=9,
        color="#555555"
    ];

    subgraph cluster_source {
        label="Source Data";
        style="rounded";
        color="gray60";

        CSV [
            label="CSV / Retail Dataset\nSales • Customers • Stores\nSKUs • Inventory • Promotions",
            fillcolor="lightblue"
        ];
    }

    subgraph cluster_database {
        label="Session 2 PostgreSQL Database";
        style="rounded";
        color="gray60";

        DB [
            label="RetailFlow PostgreSQL\nRelational Data Warehouse",
            fillcolor="palegreen"
        ];

        TABLES [
            label="BM_* Tables\nBM_SALES\nBM_CUSTOMERS • BM_STORES • BM_SKUS\nBM_INVENTORY • BM_PROMOTIONS",
            fillcolor="palegreen"
        ];
    }

    subgraph cluster_model {
        label="Data Model / Relationships";
        style="rounded";
        color="gray60";

        STAR [
            label="Star-style Analytical Model\nBM_SALES as central fact table\nDimensions: Customer • Store • SKU • Promotion",
            fillcolor="khaki"
        ];

        INV [
            label="Inventory Analysis\nStore × SKU × Snapshot Date",
            fillcolor="khaki"
        ];
    }

    subgraph cluster_sql {
        label="SQL Analytics Layer";
        style="rounded";
        color="gray60";

        QUERIES [
            label="PostgreSQL Queries\nJOIN • GROUP BY • Aggregation\nFiltering • KPI calculation",
            fillcolor="mistyrose"
        ];
    }

    subgraph cluster_output {
        label="Output / Presentation";
        style="rounded";
        color="gray60";

        KPI [
            label="Retail KPIs\nRevenue • Quantity Sold\nAverage Value • Discounts\nInventory Levels",
            fillcolor="wheat"
        ];

        GUI [
            label="RetailFlow GUI / Dashboard\nTables • Charts • Analysis",
            fillcolor="wheat"
        ];
    }

    CSV -> DB [
        label=" load / import"
    ];

    DB -> TABLES [
        label=" stores data"
    ];

    TABLES -> STAR [
        label=" PK / FK relationships"
    ];

    TABLES -> INV [
        label=" inventory relationships"
    ];

    STAR -> QUERIES [
        label=" analytical SQL"
    ];

    INV -> QUERIES [
        label=" inventory SQL"
    ];

    QUERIES -> KPI [
        label=" calculated results"
    ];

    KPI -> GUI [
        label=" visualization"
    ];
}
"""


# ------------------------------------------------------------
# GRAPHVIZ DISCOVERY
# ------------------------------------------------------------
def find_graphviz():
    """Find Graphviz dot.exe on Windows or Unix-like systems."""

    dot = shutil.which("dot")
    if dot:
        return dot

    if os.name == "nt":
        possible_paths = [
            r"C:\Program Files\Graphviz\bin\dot.exe",
            r"C:\Program Files (x86)\Graphviz\bin\dot.exe",
        ]

        # Also check common installed Graphviz directories.
        for root in (
            Path(r"C:\Program Files\Graphviz"),
            Path(r"C:\Program Files (x86)\Graphviz"),
        ):
            if root.exists():
                matches = list(root.glob("*/bin/dot.exe"))
                if matches:
                    return str(matches[0])

        for path in possible_paths:
            if Path(path).exists():
                return path

    return None


# ------------------------------------------------------------
# RENDER FUNCTION
# ------------------------------------------------------------
def render(dot_source, output_png, dot_command):
    """Write DOT source and render it to PNG."""

    dot_file = output_png.with_suffix(".dot")

    dot_file.write_text(dot_source, encoding="utf-8")

    try:
        result = subprocess.run(
            [
                dot_command,
                "-Tpng",
                "-Gdpi=150",
                str(dot_file),
                "-o",
                str(output_png),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        print(f"Diagram successfully created:")
        print(f"  PNG : {output_png}")
        print(f"  DOT : {dot_file}")

        if result.stderr.strip():
            print("\nGraphviz message:")
            print(result.stderr.strip())

        return True

    except subprocess.CalledProcessError as error:
        print("\nERROR: Graphviz failed to render the diagram.")
        if error.stderr:
            print(error.stderr)
        return False

    except OSError as error:
        print("\nERROR: Could not execute Graphviz.")
        print(error)
        return False


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    print("=" * 70)
    print("RetailFlow - Session 2 Diagram Renderer")
    print("=" * 70)

    dot_command = find_graphviz()

    if not dot_command:
        print("\nERROR: Graphviz 'dot' executable was not found.")
        print("\nInstall Graphviz, then restart VS Code.")
        print("Official installer: https://graphviz.org/download/")
        print("\nIf Graphviz is already installed, add this folder to PATH:")
        print(r"C:\Program Files\Graphviz\bin")
        return 1

    print(f"\nGraphviz found: {dot_command}")

    entity_output = DOCS_OUT / "entity-model-session2.png"
    architecture_output = DOCS_OUT / "architecture-session2.png"

    entity_success = render(
        ENTITY,
        entity_output,
        dot_command
    )

    architecture_success = render(
        ARCHITECTURE,
        architecture_output,
        dot_command
    )

    if entity_success and architecture_success:
        print("\n" + "=" * 70)
        print("SESSION 2 RENDERING COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"\nOutput folder: {DOCS_OUT}")
        print(f"1. {entity_output.name}")
        print(f"2. {architecture_output.name}")
        print("\nThe corresponding .dot files were also saved.")
        return 0

    print("\nSESSION 2 RENDERING FAILED.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
