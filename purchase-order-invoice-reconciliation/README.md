# Purchase Order & Invoice Reconciliation (SAP S/4HANA 3-Way Match Simulation)

A complete, production-grade data analytics portfolio project simulating an **Enterprise 3-Way Match Procurement Reconciliation** pipeline aligned with **SAP S/4HANA MM/FI** workflows. Built deterministically in Python, analyzed in SQLite, reviewed in Excel, and modeled for Microsoft Power BI Desktop.

> [!NOTE]
> This project is designed as an **SAP-aligned simulation**. Tables and procurement lifecycles mirror standard SAP S/4HANA tables: **LFA1** (Vendor Master), **MARA** (Material Master), **EKKO/EKPO** (Purchasing Document Header/Item), **MSEG/MATDOC** (Material Document / MIGO Goods Receipt), and **RBKP/RSEG** (Incoming Invoice / MIRO Logistics Invoice Verification). All monetary values are denominated consistently in Indian Rupees (INR, ₹).

---

## 1. Business Question

> **"Which supplier invoices need review because the purchase order, goods receipt, and invoice disagree?"**

In enterprise procurement, unverified vendor invoices lead to millions in financial leakage, duplicate payments, price creep, and compliance penalties. Accounts Payable (AP) departments prevent this through a **3-Way Match**:
1. **Purchase Order (PO)**: What was authorized and committed at agreed contract rates.
2. **Goods Receipt (GR / MIGO)**: What was physically counted, inspected, and received at the warehouse dock.
3. **Vendor Invoice (IR / MIRO)**: What the supplier billed and demanded payment for.

This project identifies every discrepancy, flags financial exposure, prevents join fan-out inflation, and provides an actionable audit queue for accounts payable reviewers.

---

## 2. Technical Highlight: The Cartesian Product "Fan-Out Trap"

A classic pitfall in SQL procurement analysis occurs when multiple goods receipts (split deliveries) and multiple invoices (progress payments) exist for a single PO line item.

### The Problem (Naive Raw Join):
If an analyst executes a direct 3-way join:
```sql
FROM fact_po_lines pol
JOIN fact_goods_receipts gr ON pol.po_number = gr.po_number AND pol.line_item = gr.line_item
JOIN fact_invoice_lines inv ON pol.po_number = inv.po_number AND pol.line_item = inv.line_item
```
When a line item has **2 Goods Receipts** and **2 Invoices**, the join produces a **2 × 2 Cartesian Product (4 joined rows)**. Summing quantities or amounts over this joined result artificially **doubles (100% inflation)** both received quantities and invoiced amounts!

### The Solution (Independent Aggregation):
This project enforces independent pre-aggregation using Common Table Expressions (CTEs):
```sql
WITH gr_agg AS (
    SELECT po_number, line_item, SUM(received_quantity) AS total_received_qty
    FROM fact_goods_receipts
    GROUP BY po_number, line_item
),
inv_agg AS (
    SELECT po_number, line_item, SUM(invoiced_quantity) AS total_invoiced_qty, SUM(invoiced_amount) AS total_invoiced_amount
    FROM fact_invoice_lines
    GROUP BY po_number, line_item
)
SELECT pol.*, gr.total_received_qty, inv.total_invoiced_qty, inv.total_invoiced_amount
FROM fact_po_lines pol
LEFT JOIN gr_agg gr ON pol.po_number = gr.po_number AND pol.line_item = gr.line_item
LEFT JOIN inv_agg inv ON pol.po_number = inv.po_number AND pol.line_item = inv.line_item;
```
This guarantees an exact 1-to-1 PO-line reconciliation with **zero row inflation** and 100% mathematical precision.

---

## 3. Data Dictionary & SAP Alignment

| Table Name | SAP S/4HANA Equivalent | Key Fields & Description |
|---|---|---|
| `dim_suppliers` | `LFA1` (Vendor Master) | `supplier_id` (PK), `supplier_name`, `vendor_code` (e.g. `1000101`), `city`, `payment_terms` (`Net 30`, `Net 45`, `Net 60`), `contact_email` |
| `dim_materials` | `MARA` / `MAKT` (Material Master) | `material_code` (PK), `material_description`, `material_group` (`RAW_COFFEE`, `PACKAGING`, `DAIRY_SYRUP`, `EQUIPMENT_PARTS`), `base_uom` |
| `fact_purchase_orders` | `EKKO` (Purchasing Header) | `po_number` (PK, e.g. `PO-45001001`), `supplier_id` (FK), `company_code` (`1000`), `purchasing_org` (`1000`), `po_date`, `currency` (`INR`), `status` |
| `fact_po_lines` | `EKPO` (Purchasing Item) | `po_number` (FK), `line_item` (PK composite: 10, 20...), `material_code` (FK), `ordered_quantity`, `po_unit_price` (₹), `uom`, `expected_delivery_date`, `po_line_total` |
| `fact_goods_receipts` | `MSEG` / `MATDOC` (MIGO Receipt) | `gr_number` (PK), `material_doc_year` (`2026`), `po_number` (FK), `line_item` (FK), `gr_date`, `received_quantity`, `movement_type` (`101` - GR into warehouse), `storage_location` |
| `fact_invoice_lines` | `RBKP` / `RSEG` (MIRO Invoice) | `invoice_number` (PK), `invoice_date`, `supplier_id` (FK), `po_number` (FK), `line_item` (FK), `invoiced_quantity`, `invoice_unit_price` (₹), `invoiced_amount`, `tax_amount`, `payment_status` |
| `rpt_3way_match_exceptions` | Curated AP Reconciliation Fact | 1 row per PO line containing aggregated quantities, invoiced amounts, variances, flags, and `suggested_next_action` |

---

## 4. Exception Rules & Configurable Tolerances

The reconciliation engine audits each PO line against four deterministic business criteria:

1. **Missing Goods Receipt (`MISSING_GR`)**:
   - Condition: `invoiced_quantity > 0 AND received_quantity = 0`.
   - Business Meaning: Vendor billed for materials never received at the warehouse dock.
   - Recommended Action: Block invoice payment in MIRO; contact warehouse receiving to verify physical arrival or enter MIGO.

2. **Quantity Over-Invoiced (`QUANTITY_OVER_INVOICE`)**:
   - Condition: `invoiced_quantity > received_quantity AND received_quantity > 0`.
   - Business Meaning: Vendor billed for more units than were physically delivered and accepted.
   - Recommended Action: Apply SAP invoice quantity block (R-block); request credit note for excess billed units.

3. **Price Variance Outside Tolerance (`PRICE_VARIANCE`)**:
   - Condition: `ABS(invoice_unit_price - po_unit_price) / po_unit_price > 0.02` (Configurable ±2.0% tolerance).
   - Business Meaning: Invoiced rate exceeds agreed purchase order unit price.
   - Recommended Action: Apply SAP price variance block (P-block); dispute unauthorized price creep with vendor or require purchasing buyer amendment.

4. **Overdue Open PO Line (`OVERDUE_OPEN_PO`)**:
   - Condition: `expected_delivery_date < '2026-11-17' AND received_quantity < ordered_quantity`.
   - Business Meaning: Delivery commitment date has passed, but goods remain unfulfilled.
   - Recommended Action: Escalate to Purchasing Buyer to chase supplier delivery or de-commit/cancel remaining quantity in EKPO.

> [!IMPORTANT]
> **Partial Delivery Handling Rule**:
> If a line has received partial goods (`received_quantity < ordered_quantity`), but its `expected_delivery_date >= '2026-11-17'` (still within its contractual delivery window) and invoiced quantity equals received quantity at agreed rates, it is **strictly classified as `CLEAN_MATCH`**. It is NOT penalized as an exception.

---

## 5. Hand-Checked Benchmark Fixtures

The pipeline includes 8 hand-checked benchmark fixtures (`data/fixtures/hand_checked_fixtures.json`) that test every permutation:

| Test Case | Scenario Description | PO Number | Line | Expected Match Status | Expected Reason(s) | Verified Result |
|---|---|---|---|---|---|---|
| **TC-01** | Perfect 1:1:1 Match (All documents agree) | `PO-45001001` | 10 | `CLEAN_MATCH` | `CLEAN_MATCH` | **PASS** |
| **TC-02** | Partial Receipt Within Window (NOT an exception) | `PO-45001002` | 10 | `CLEAN_MATCH` | `CLEAN_MATCH` | **PASS** |
| **TC-03** | Split Receipts & Split Invoices (Anti-Fan-Out) | `PO-45001003` | 10 | `CLEAN_MATCH` | `CLEAN_MATCH` | **PASS** |
| **TC-04** | Missing Goods Receipt (Billed with zero GR) | `PO-45001004` | 10 | `EXCEPTION` | `MISSING_GR; OVERDUE_OPEN_PO` | **PASS** |
| **TC-05** | Quantity Over-Invoiced (Billed 100, Received 70) | `PO-45001005` | 10 | `EXCEPTION` | `QUANTITY_OVER_INVOICE; OVERDUE_OPEN_PO` | **PASS** |
| **TC-06** | Price Variance Outside Tolerance (+10% hike) | `PO-45001006` | 10 | `EXCEPTION` | `PRICE_VARIANCE` | **PASS** |
| **TC-07** | Overdue Open PO Line (Expected Oct 10, undelivered) | `PO-45001007` | 10 | `EXCEPTION` | `OVERDUE_OPEN_PO` | **PASS** |
| **TC-08** | Compound Multi-Exception (Over-invoiced + Price Hike) | `PO-45001008` | 10 | `EXCEPTION` | `QUANTITY_OVER_INVOICE; PRICE_VARIANCE; OVERDUE_OPEN_PO` | **PASS** |

---

## 6. Quickstart & One-Command Demo

To run the complete data generation, database load, 3-way match, report generation, and automated test suite on Windows:

### Command Prompt (`cmd.exe`):
```cmd
cd purchase-order-invoice-reconciliation
run_demo.bat
```

### PowerShell:
```powershell
cd purchase-order-invoice-reconciliation
powershell -ExecutionPolicy Bypass -File run_demo.ps1
```

### Manual Individual Step Execution:
```bash
# 1. Generate deterministic SAP procurement data and benchmark fixtures
python src/generate_sap_data.py

# 2. Load SQLite database and execute independent aggregation 3-way match
python src/load_database.py

# 3. Generate CSV reports and Excel AP review workbook
python src/generate_excel_review.py

# 4. Export model-ready Power BI tables
python src/export_powerbi_tables.py

# 5. Run automated validation test suite
python tests/test_reconciliation.py
```

---

## 7. Analytical Findings & Strategic Case Study

From the reconciliation of **76 purchase order lines** totaling **₹1,05,24,600** across 8 suppliers:

### Finding 1: Financial Exposure Held by Accounts Payable
- **Overall Clean Match Rate**: **60.5%** of lines (46 lines) matched cleanly and were cleared for payment.
- **Disputed Lines Held**: **39.5%** of lines (30 lines) failed one or more 3-way match criteria and were placed on payment hold.
- **Financial Amount at Risk**: A total of **₹15,22,480 in disputed payments** was protected from wrongful disbursement.

### Finding 2: Root-Cause Risk Distribution
- **Missing Goods Receipts (`MISSING_GR`)**: Represents the single largest financial leakage risk, accounting for **₹5,88,000** in unauthorized supplier billing without physical warehouse delivery verification.
- **Overdue Open Quantities (`OVERDUE_OPEN_PO`)**: Accounts for **₹6,14,000** in unfulfilled vendor commitments, creating severe supply continuity risks for packaging and green coffee beans.
- **Price Creep / Rate Variance (`PRICE_VARIANCE`)**: Accounted for **₹1,44,200** in unauthorized unit price inflation exceeding the ±2.0% contractual tolerance.

### Finding 3: Supplier Risk Concentration
- Over 65% of disputed risk was concentrated in three specific vendors:
  1. *Deccan Artisanal Syrups & Flavor*: 44.4% exception rate with ₹4.1L in unverified invoices.
  2. *Bharat Eco Packaging Solutions*: 50.0% exception rate driven by chronic split deliveries and premature billing.
  3. *Precision Espresso Spares*: High frequency of unauthorized rate increases (+8% to +10%) on replacement gaskets and valves.

---

## 8. Actionable AP Recommendation & Governance Plan

### Recommendation: Automated 2-Tier Block & Vendor Governance
1. **Systemic SAP Block Implementation**:
   - Configure automatic **MIRO R-Blocks** (Quantity Discrepancy) and **P-Blocks** (Price Variance) in SAP S/4HANA to prevent AP clerks from manually overriding payments exceeding ₹10,000.
2. **Weekly Vendor Debit Note Protocol**:
   - Establish a weekly automated discrepancy digest sent to *Deccan Artisanal Syrups* and *Bharat Eco Packaging*, issuing debit notes / credit memo demands within 7 days of invoice submission.
3. **Purchasing De-Commitment Review**:
   - Require Procurement Buyers to formally review all PO lines overdue by > 21 days, canceling outstanding line items in EKPO to release trapped working capital.

### Simulation Limitations:
- The simulation models standard GST taxation (18%) and static payment terms. In a full production SAP deployment, additional variables such as freight conditions, cash discount terms (e.g. 2/10 Net 30), and credit hold workflows across company codes would further modulate payment releases.

---

## 9. Two-Minute Interview Walkthrough Script

> *"In this project, I designed an enterprise-grade 3-Way Match procurement reconciliation pipeline inspired by SAP S/4HANA workflows, evaluating purchase orders, goods receipts, and vendor invoices across 76 line items totaling over ₹1 Crore.
>
> One of the most important technical challenges I solved was the 'Join Fan-Out Trap'. In enterprise procurement, a single PO line often has multiple goods receipts and multiple progress invoices. If you naively join PO lines to receipts and invoices directly, you generate a Cartesian product that artificially inflates reported quantities and spend by 100%. I resolved this by authoring SQL that aggregates receipts and invoices independently in CTEs at the PO-line level before joining, proving mathematically that spend inflation is completely prevented.
>
> I built a deterministic rules engine in SQLite that audits lines against four key criteria: missing goods receipts, quantity over-invoicing, price variances exceeding a configurable ±2% tolerance, and overdue deliveries. Crucially, I programmed the business rule that partial deliveries within their contractual window are recognized as clean matches rather than false exceptions.
>
> I delivered a multi-tab Accounts Payable review workbook in Excel with full audit queues and risk scorecards, and a Power BI build kit with star-schema models and DAX measures. The analysis successfully flagged 30 exception lines protecting ₹15.2 Lakhs in disputed payments at risk, concentrating heavily in packaging and specialty syrup suppliers."*

---

## 10. Truthful Resume Bullet

> **Data Analyst — SAP 3-Way Match Procurement Reconciliation (Portfolio Project)**
> * Engineered an SAP S/4HANA-aligned 3-way match pipeline in SQLite & Python, eliminating Cartesian join fan-out via independent CTE aggregation and evaluating ₹1.05 Cr across 76 PO lines.
> * Authored SQL classification rules detecting missing receipts, over-billing, and price variances (> ±2% tolerance), identifying ₹15.2L in disputed accounts payable risk across an auditable Excel review workbook and Power BI dashboard.
