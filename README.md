# Data Analytics Portfolio — Retail & Enterprise Reconciliation

This repository contains two complete, production-grade data analytics portfolio projects developed in Python, SQLite, Microsoft Excel, and Microsoft Power BI.

---

## Portfolio Projects Overview

| Project | Business Domain | Key Technologies | Core Analytical Highlight |
|---|---|---|---|
| **[1. Slow Brew Sales & Delivery](slow-brew-sales-delivery/)** | Retail / Specialty Café F&B | Python (ETL), SQLite, Excel, Power BI | Analyzes 90 days of multi-channel order data (8,700+ POS & 6,000+ Zomato rows). Identified a 35% delivery dip during the 12:00–16:00 afternoon slump and designed an A/B promotion test for cold brews. |
| **[2. PO & Invoice Reconciliation](purchase-order-invoice-reconciliation/)** | Enterprise Supply Chain / SAP Procurement | Python, SQLite, Excel (AP Queue), Power BI | Simulates SAP S/4HANA 3-way match across 76 PO lines (₹1.05 Cr). Proved prevention of Cartesian join fan-out via CTE pre-aggregation and protected ₹15.2L in disputed accounts payable risk. |

---

## Directory Structure

```text
├── slow-brew-sales-delivery/
│   ├── README.md                                  # Complete project documentation & business case
│   ├── run_demo.bat                               # Windows 1-click execution script
│   ├── data/
│   │   ├── raw/                                   # Raw POS and Zomato CSV exports (with anomalies)
│   │   ├── processed/                             # Cleaned orders, order items, and rejected row audit
│   │   └── templates/                             # CSV import path for real production café data
│   ├── database/
│   │   ├── slow_brew.db                           # SQLite 3 relational database
│   │   └── schema.sql                             # DDL schemas (dimensions, facts, audit tables)
│   ├── sql/                                       # Production SQL queries (cleaning, KPIs, dayparts)
│   ├── src/                                       # Python ETL, deduplication, and openpyxl scripts
│   ├── reports/
│   │   ├── Slow_Brew_Sales_Reconciliation.xlsx    # Multi-tab Excel reconciliation workbook
│   │   └── *.csv                                  # Analytical summary export tables
│   ├── powerbi/                                   # Power BI build kit, star-schema, and DAX measures
│   └── tests/                                     # Automated test suite (6/6 passing assertions)
│
└── purchase-order-invoice-reconciliation/
    ├── README.md                                  # SAP MM/FI 3-way match documentation & case study
    ├── run_demo.bat                               # Windows 1-click execution script
    ├── data/
    │   ├── raw/                                   # SAP-aligned CSV tables (Suppliers, POs, GRs, Invoices)
    │   └── fixtures/                              # Hand-checked benchmark test cases with known results
    ├── database/
    │   ├── sap_procurement.db                     # SQLite relational database
    │   └── schema.sql                             # SAP-aligned DDL schema
    ├── sql/                                       # Anti-fan-out proof, 3-way match, and vendor scorecard
    ├── src/                                       # Deterministic data generation and loading scripts
    ├── reports/
    │   ├── AP_Invoice_Reconciliation_Workbook.xlsx# Accounts Payable review workbook with dispute actions
    │   └── *.csv                                  # Analytical summary CSVs
    ├── powerbi/                                   # Power BI build kit, star-schema, and DAX measures
    └── tests/                                     # Automated test suite (5/5 passing assertions)
```

---

## Quickstart (Windows)

Each project can be run independently from within its folder:

```cmd
# Run Project 1
cd slow-brew-sales-delivery
run_demo.bat

# Run Project 2
cd purchase-order-invoice-reconciliation
run_demo.bat
```
