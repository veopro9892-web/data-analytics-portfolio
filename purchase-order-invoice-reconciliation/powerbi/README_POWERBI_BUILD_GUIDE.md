# Power BI Report Build Guide — Accounts Payable 3-Way Match

This guide provides exact step-by-step instructions to rebuild the **Accounts Payable 3-Way Match Reconciliation Dashboard** in Microsoft Power BI Desktop.

> [!NOTE]
> Power BI Desktop runs in a native Windows desktop GUI environment. All required data tables have been exported as clean, typed CSV files in `./ready_to_import_csv/`, verified against SQLite and Excel reconciliation totals. Follow the steps below to import and build the 2-page report in ~10 minutes.

---

## 1. Import Ready-to-Use Data

1. Open **Power BI Desktop**.
2. Click **Get Data** -> **Text/CSV**.
3. Import the tables from `powerbi/ready_to_import_csv/`:
   - `dim_suppliers.csv`
   - `dim_materials.csv`
   - `rpt_3way_match_exceptions.csv` (Primary reconciliation fact table)
   - `fact_purchase_orders.csv`
   - `fact_po_lines.csv`
4. In Power Query, set types:
   - Currency: `po_unit_price`, `invoice_unit_price`, `po_line_total`, `invoiced_amount`, `amount_at_risk_inr` as `Fixed Decimal Number (Currency)`.
   - Quantities: `ordered_quantity`, `received_quantity`, `invoiced_quantity` as `Decimal Number`.
   - Percentage: `price_variance_pct` as `Percentage`.
   - Dates: `expected_delivery_date`, `po_date` as `Date`.
5. Click **Close & Apply**.

---

## 2. Configure Model Relationships

In **Model View**, set up:
- `dim_suppliers[supplier_id]` (1) ——< (N) `rpt_3way_match_exceptions[supplier_id]`
- `dim_materials[material_code]` (1) ——< (N) `rpt_3way_match_exceptions[material_code]`
- `dim_suppliers[supplier_id]` (1) ——< (N) `fact_purchase_orders[supplier_id]`
- `fact_purchase_orders[po_number]` (1) ——< (N) `fact_po_lines[po_number]`

---

## 3. Add DAX Measures

Create a new table `_Measures` and copy-paste formulas from `DAX_Measures.dax`:
- `[Total PO Lines]`
- `[Clean Matched Lines]`
- `[Exception Lines]`
- `[Clean Match Rate %]` (Format: `0.0%`)
- `[Exception Rate %]` (Format: `0.0%`)
- `[Total PO Commitment (₹)]` (Format: `₹#,##0`)
- `[Total Invoiced Amount (₹)]` (Format: `₹#,##0`)
- `[Total Disputed Amount at Risk (₹)]` (Format: `₹#,##0`)
- `[Risk Exposure Rate %]` (Format: `0.0%`)
- `[Missing GR Lines]`
- `[Quantity Over-Invoiced Lines]`
- `[Price Variance Lines]`
- `[Overdue Open PO Lines]`

---

## 4. Report Page 1: "AP Executive Overview"

### Canvas Layout:
1. **Header Bar**:
   - Title: `ACCOUNTS PAYABLE 3-WAY MATCH DASHBOARD`
   - Subtitle: `SAP S/4HANA Procurement Simulation | Risk Exposure & Compliance`
   - Slicers: Supplier Name (`dim_suppliers[supplier_name]`), Material Group (`dim_materials[material_group]`), Match Status (`rpt_3way_match_exceptions[match_status]`).

2. **Top KPI Cards (Row 1)**:
   - Card 1: `[Total Invoiced Amount (₹)]` (₹1.05 Cr)
   - Card 2: `[Total Disputed Amount at Risk (₹)]` (₹15.2L)
   - Card 3: `[Clean Match Rate %]` (60.5%)
   - Card 4: `[Exception Lines]` (30 Held Lines)
   - Card 5: `[Total PO Lines]` (76 Lines)

3. **Visual 1 (Donut Chart - Exceptions by Root Cause)**:
   - **Legend**: `rpt_3way_match_exceptions[primary_exception_reason]`
   - **Values**: `[Total Disputed Amount at Risk (₹)]`
   - *Key takeaway*: Highlights which error category holds the largest financial exposure (Missing GR and Overdue Open POs).

4. **Visual 2 (Bar Chart - Supplier Risk Exposure)**:
   - **Y-Axis**: `dim_suppliers[supplier_name]`
   - **X-Axis**: `[Total Disputed Amount at Risk (₹)]`
   - **Color saturation**: Based on `[Exception Rate %]`
   - *Key takeaway*: Instantly spotlights worst-offending vendors for AP vendor management intervention.

5. **Visual 3 (Table - Supplier Scorecard Summary)**:
   - Columns: Supplier Name, Total PO Lines, Exception Lines, Exception Rate %, Total Invoiced, Disputed Risk (₹).

---

## 5. Report Page 2: "PO-Line Exception Audit Detail"

### Canvas Layout:
1. **Header Callout**:
   - Title: `PO-LINE EXCEPTION REVIEW & AP ACTION QUEUE`
   - Slicers: Primary Exception Reason (`primary_exception_reason`), Supplier (`supplier_name`), Delivery Date (`expected_delivery_date`).

2. **Visual 1 (Main Drill-Through Audit Matrix)**:
   - **Columns**:
     - `po_number` (PO Number)
     - `line_item` (Line)
     - `supplier_name` (Vendor)
     - `material_description` (Material)
     - `ordered_quantity` (Ordered)
     - `received_quantity` (Received)
     - `invoiced_quantity` (Invoiced)
     - `po_unit_price` (PO Rate ₹)
     - `invoice_unit_price` (Inv Rate ₹)
     - `price_variance_pct` (Variance %)
     - `amount_at_risk_inr` (Risk Exposure ₹)
     - `relevant_invoice_ids` (Invoices)
     - `suggested_next_action` (AP Next Action)
   - **Conditional Formatting**:
     - `amount_at_risk_inr`: Background color scale (White to Light Red).
     - `price_variance_pct`: Font color red if > 2.0%.

3. **Visual 2 (Decomposition Tree / Drill Down)**:
   - **Analyze**: `[Total Disputed Amount at Risk (₹)]`
   - **Explain By**: `primary_exception_reason` -> `supplier_name` -> `material_description` -> `po_number`.
   - *Interview Highlight*: Demonstrates executive root-cause exploration from high-level currency risk down to individual SAP purchase order line items.
