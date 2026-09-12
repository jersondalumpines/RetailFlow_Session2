# RetailFlow — Session 2 Event Streaming

## Project Title

**RetailFlow: Real-Time Retail Analytics Using PostgreSQL and Event Streaming**

---

## Overview

Session 2 extends the RetailFlow project from parallel sales analytics into a **database and event-streaming architecture**.

The objective is to organize the retail data into a PostgreSQL database, define the relationships between business entities, and prepare an architecture that can support near-real-time sales, inventory, customer, store, SKU, and promotion analysis.

The project uses the RetailFlow `BM_*` datasets and focuses on:

- PostgreSQL database design
- Entity Relationship Diagram (ERD)
- System and data architecture
- Sales event processing
- Inventory event processing
- SQL-based analytics
- Retail KPI generation
- GUI/dashboard integration

---

## Dataset

The project uses six main retail tables:

- `bm_sales.csv` — sales transactions and the main fact table
- `bm_customers.csv` — customer information
- `bm_stores.csv` — store information
- `bm_skus.csv` — product/SKU information
- `bm_inventory.csv` — inventory snapshots
- `bm_promotions.csv` — promotion information and date ranges

The primary analytical relationship is:

```text
Customers
     |
     v
   Sales <---- Stores
     |
     v
    SKUs
```

Inventory provides additional Store × SKU information, while Promotions can be matched using promotion dates and discount information.

---

## Session 2 Objectives

The main objectives are to:

1. Create a PostgreSQL database for the RetailFlow project.
2. Create normalized relational tables using the `BM_*` structure.
3. Define primary keys and foreign keys.
4. Establish relationships between sales, customers, stores, and SKUs.
5. Create an Entity Relationship Diagram (ERD).
6. Create a Session 2 system/data architecture diagram.
7. Prepare the database for event-streaming workflows.
8. Process sales and inventory events.
9. Generate analytical SQL queries and retail KPIs.
10. Provide data outputs that can be used by the RetailFlow GUI/dashboard.

---

## Database Architecture

The Session 2 architecture follows this flow:

```text
CSV Retail Data
       |
       v
Data Import / Ingestion
       |
       v
PostgreSQL Database
       |
       +----------------------+
       |                      |
       v                      v
   BM_* Tables          Event Processing
       |                      |
       +----------+-----------+
                  |
                  v
             SQL Analytics
                  |
                  v
             Retail KPIs
                  |
                  v
          GUI / Dashboard
```

---

## Database Tables

### 1. BM_SALES

The main transaction/fact table.

Important fields include:

```text
sale_id
date
store_id
sku_id
customer_id
quantity
unit_price
total_value
channel
discount_pct
```

Relationships:

```text
BM_CUSTOMERS 1 ---- * BM_SALES
BM_STORES    1 ---- * BM_SALES
BM_SKUS      1 ---- * BM_SALES
```

### 2. BM_CUSTOMERS

Stores customer information.

```text
cust_id (PK)
age
gender
city
loyalty_segment
preferred_channel
registration_date
```

### 3. BM_STORES

Stores information about retail stores.

```text
store_id (PK)
store_name
city
store_type
opening_date
```

### 4. BM_SKUS

Stores product/SKU information.

```text
sku_id (PK)
sku_name
category
subcategory
unit_price
cost_price
brand
```

### 5. BM_INVENTORY

Stores inventory snapshots for a store and SKU.

```text
inventory_id (PK)
store_id (FK)
sku_id (FK)
stock_on_hand
reorder_point
safety_stock
last_restock_date
snapshot_date
```

The inventory relationship is:

```text
BM_STORES 1 ---- * BM_INVENTORY
BM_SKUS   1 ---- * BM_INVENTORY
```

### 6. BM_PROMOTIONS

Stores promotional campaigns.

```text
promo_id (PK)
promo_name
start_date
end_date
discount_pct
promo_type
```

Promotions can be associated with sales using date-range and discount matching when a direct `promo_id` foreign key is not available.

---

## Entity Relationship Diagram

The main entity relationships are:

```text
                 +----------------+
                 | BM_CUSTOMERS   |
                 | cust_id (PK)   |
                 +-------+--------+
                         |
                         | 1:M
                         |
+----------------+       v
| BM_STORES      |     +----------------+
| store_id (PK)  |---->| BM_SALES       |
+-------+--------+ 1:M | sale_id (PK)   |
        |               | store_id (FK) |
        |               | sku_id (FK)   |
        |               | customer_id   |
        |               +-------+--------+
        |                       |
        |                       | M:1
        |                       v
        |               +----------------+
        |               | BM_SKUS        |
        |               | sku_id (PK)    |
        |               +----------------+
        |
        | 1:M
        v
+----------------+
| BM_INVENTORY   |
| inventory_id   |
| store_id (FK)  |
| sku_id (FK)    |
+----------------+

+----------------+
| BM_PROMOTIONS  |
| promo_id (PK)  |
+----------------+
        |
        | date-range /
        | discount matching
        v
    BM_SALES
```

---

## Event Streaming Concept

Session 2 introduces an event-oriented view of the retail system.

A sale can be treated as a business event:

```text
Sales Event
    |
    +-- sale_id
    +-- date
    +-- store_id
    +-- sku_id
    +-- customer_id
    +-- quantity
    +-- unit_price
    +-- total_value
    +-- channel
    +-- discount_pct
```

An inventory event can contain:

```text
Inventory Event
    |
    +-- inventory_id
    +-- store_id
    +-- sku_id
    +-- stock_on_hand
    +-- reorder_point
    +-- safety_stock
    +-- snapshot_date
```

These events can be ingested into the PostgreSQL analytical environment for processing and reporting.

---

## Event Processing Flow

```text
Retail Transaction
       |
       v
   Sales Event
       |
       v
Event Ingestion
       |
       v
PostgreSQL
       |
       v
SQL Processing
       |
       +----------------+
       |                |
       v                v
Sales KPIs        Inventory KPIs
       |                |
       +-------+--------+
               |
               v
        RetailFlow GUI
```

---

## Retail KPIs

### Total Revenue

```sql
SELECT SUM(total_value) AS total_revenue
FROM bm_sales;
```

### Total Quantity Sold

```sql
SELECT SUM(quantity) AS total_quantity
FROM bm_sales;
```

### Revenue by Store

```sql
SELECT
    store_id,
    SUM(total_value) AS revenue
FROM bm_sales
GROUP BY store_id
ORDER BY revenue DESC;
```

### Revenue by SKU

```sql
SELECT
    sku_id,
    SUM(total_value) AS revenue
FROM bm_sales
GROUP BY sku_id
ORDER BY revenue DESC;
```

### Revenue by Channel

```sql
SELECT
    channel,
    SUM(total_value) AS revenue
FROM bm_sales
GROUP BY channel
ORDER BY revenue DESC;
```

### Inventory Monitoring

```sql
SELECT
    store_id,
    sku_id,
    stock_on_hand,
    reorder_point,
    safety_stock
FROM bm_inventory
WHERE stock_on_hand <= reorder_point;
```

---

## Suggested Project Structure

```text
session2_event_streaming/
│
├── README.md
│
├── data/
│   ├── bm_sales.csv
│   ├── bm_customers.csv
│   ├── bm_stores.csv
│   ├── bm_skus.csv
│   ├── bm_inventory.csv
│   └── bm_promotions.csv
│
├── sql/
│   ├── create_tables.sql
│   ├── load_data.sql
│   ├── relationships.sql
│   └── analytics.sql
│
├── diagrams/
│   ├── entity-model-session2.dot
│   ├── entity-model-session2.png
│   ├── architecture-session2.dot
│   └── architecture-session2.png
│
├── src/
│   ├── event_producer.py
│   ├── event_consumer.py
│   └── database.py
│
├── results/
│   ├── sales_kpis.csv
│   └── inventory_kpis.csv
│
└── requirements.txt
```

---

## Windows / VS Code Setup

Open the `session2_event_streaming` folder in VS Code.

Open a PowerShell terminal.

### 1. Check Python

```powershell
py --version
```

### 2. Install Python packages

```powershell
py -m pip install -r requirements.txt
```

### 3. Check PostgreSQL

```powershell
psql --version
```

Make sure the PostgreSQL server is running before executing the SQL scripts.

### 4. Create the Database

Example:

```sql
CREATE DATABASE "RetailFlow";
```

Connect to the database and execute:

```powershell
psql -U postgres -d RetailFlow -f sql/create_tables.sql
```

### 5. Load the Data

```powershell
psql -U postgres -d RetailFlow -f sql/load_data.sql
```

### 6. Execute Relationships

```powershell
psql -U postgres -d RetailFlow -f sql/relationships.sql
```

### 7. Run Analytics

```powershell
psql -U postgres -d RetailFlow -f sql/analytics.sql
```

---

## Diagram Generation

The project includes a Python diagram renderer.

Run:

```powershell
py render_diagrams_session2.py
```

The program generates:

```text
docs/
├── entity-model-session2.png
├── entity-model-session2.dot
├── architecture-session2.png
└── architecture-session2.dot
```

Graphviz must be installed and the `dot` executable must be available.

Check Graphviz with:

```powershell
dot -V
```

---

## Data Integrity

The project should validate:

- Primary-key uniqueness
- Foreign-key relationships
- Missing foreign keys
- Duplicate records
- Invalid dates
- Negative quantities
- Invalid prices
- Inventory values
- Promotion date ranges

Example:

```sql
SELECT COUNT(*) AS invalid_sales
FROM bm_sales
WHERE quantity <= 0
   OR unit_price < 0;
```

---

## Expected Outputs

At the end of Session 2, the project should provide:

```text
PostgreSQL database
        +
Relational data model
        +
Entity Relationship Diagram
        +
System Architecture Diagram
        +
Event-processing workflow
        +
SQL analytical queries
        +
Retail KPI results
        +
GUI/Dashboard-ready data
```

---

## Session 2 Deliverables

The expected deliverables are:

1. PostgreSQL database named `RetailFlow`
2. Six `BM_*` relational tables
3. Primary and foreign key definitions
4. Entity Relationship Diagram
5. Session 2 architecture diagram
6. Event streaming/process design
7. SQL analytics queries
8. Retail KPI results
9. Data validation results
10. README documentation

---

## Notes

Session 2 builds on the RetailFlow dataset used in Session 1. The original project contains six CSV files, with sales as the main fact table and customers, stores, SKUs, inventory, and promotions as supporting data.

Session 1 focused on loading, joining, partitioning, benchmarking, and validating parallel computation. Session 2 changes the focus toward **database architecture, relational modeling, PostgreSQL, and event-oriented retail analytics**.

The architecture is designed so that the PostgreSQL database can serve as the central analytical data store while event-processing components provide a path toward near-real-time retail analytics.
