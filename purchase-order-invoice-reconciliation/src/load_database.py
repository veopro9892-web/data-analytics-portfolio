"""
load_database.py
----------------
Loads generated SAP procurement CSV data into SQLite (`sap_procurement.db`),
and executes the independent aggregation 3-way match query to populate the
exception review table `rpt_3way_match_exceptions`.
"""

import os
import csv
import sqlite3
import pandas as pd

def load_sap_database():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, "data", "raw")
    db_path = os.path.join(base_dir, "database", "sap_procurement.db")
    schema_path = os.path.join(base_dir, "database", "schema.sql")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open(schema_path, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    # Load Dimensions
    def load_table(csv_name, table_name, columns):
        file_path = os.path.join(raw_dir, csv_name)
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [tuple(row[col] for col in columns) for row in reader]
        placeholders = ",".join(["?"] * len(columns))
        cursor.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", rows)

    load_table("suppliers.csv", "dim_suppliers", ["supplier_id", "supplier_name", "vendor_code", "city", "payment_terms", "contact_email"])
    load_table("materials.csv", "dim_materials", ["material_code", "material_description", "material_group", "base_uom"])
    load_table("purchase_orders.csv", "fact_purchase_orders", ["po_number", "supplier_id", "company_code", "purchasing_org", "po_date", "currency", "status"])
    load_table("po_lines.csv", "fact_po_lines", ["po_number", "line_item", "material_code", "ordered_quantity", "po_unit_price", "uom", "expected_delivery_date", "po_line_total"])
    load_table("goods_receipts.csv", "fact_goods_receipts", ["gr_number", "material_doc_year", "po_number", "line_item", "gr_date", "received_quantity", "movement_type", "storage_location"])
    load_table("invoice_lines.csv", "fact_invoice_lines", ["invoice_number", "invoice_date", "supplier_id", "po_number", "line_item", "invoiced_quantity", "invoice_unit_price", "invoiced_amount", "tax_amount", "payment_status"])

    conn.commit()

    # Create the Reconciled Exception Table via Independent Aggregation
    # Configurable Price Tolerance: 0.02 (+/- 2.0%)
    # Current Reference Date for Overdue Check: 2026-11-17
    match_sql = """
    CREATE TABLE rpt_3way_match_exceptions AS
    WITH gr_agg AS (
        SELECT 
            po_number,
            line_item,
            COUNT(DISTINCT gr_number) AS gr_count,
            GROUP_CONCAT(DISTINCT gr_number) AS gr_numbers,
            COALESCE(SUM(received_quantity), 0.0) AS total_received_qty,
            MAX(gr_date) AS latest_gr_date
        FROM fact_goods_receipts
        GROUP BY po_number, line_item
    ),
    inv_agg AS (
        SELECT 
            po_number,
            line_item,
            COUNT(DISTINCT invoice_number) AS invoice_count,
            GROUP_CONCAT(DISTINCT invoice_number) AS relevant_invoice_ids,
            COALESCE(SUM(invoiced_quantity), 0.0) AS total_invoiced_qty,
            COALESCE(SUM(invoiced_amount), 0.0) AS total_invoiced_amount,
            -- Effective average invoiced unit price
            ROUND(COALESCE(SUM(invoiced_amount) / NULLIF(SUM(invoiced_quantity), 0), 0.0), 2) AS avg_invoice_unit_price,
            MAX(invoice_date) AS latest_invoice_date
        FROM fact_invoice_lines
        GROUP BY po_number, line_item
    ),
    reconciliation_base AS (
        SELECT 
            pol.po_number,
            pol.line_item,
            po.supplier_id,
            s.supplier_name,
            s.contact_email,
            pol.material_code,
            m.material_description,
            pol.ordered_quantity,
            pol.po_unit_price,
            pol.expected_delivery_date,
            pol.po_line_total,
            COALESCE(gr.total_received_qty, 0.0) AS received_quantity,
            COALESCE(gr.gr_count, 0) AS gr_count,
            COALESCE(gr.gr_numbers, 'NONE') AS gr_numbers,
            COALESCE(inv.total_invoiced_qty, 0.0) AS invoiced_quantity,
            COALESCE(inv.invoice_count, 0) AS invoice_count,
            COALESCE(inv.relevant_invoice_ids, 'NONE') AS relevant_invoice_ids,
            COALESCE(inv.avg_invoice_unit_price, 0.0) AS invoice_unit_price,
            COALESCE(inv.total_invoiced_amount, 0.0) AS invoiced_amount,
            
            -- Discrepancy calculations
            ROUND(COALESCE(inv.total_invoiced_qty, 0.0) - COALESCE(gr.total_received_qty, 0.0), 2) AS qty_discrepancy,
            ROUND(COALESCE(inv.avg_invoice_unit_price, 0.0) - pol.po_unit_price, 2) AS price_variance,
            CASE 
                WHEN pol.po_unit_price > 0 
                THEN ROUND(100.0 * (COALESCE(inv.avg_invoice_unit_price, 0.0) - pol.po_unit_price) / pol.po_unit_price, 2)
                ELSE 0.0 
            END AS price_variance_pct
        FROM fact_po_lines pol
        JOIN fact_purchase_orders po ON pol.po_number = po.po_number
        JOIN dim_suppliers s ON po.supplier_id = s.supplier_id
        JOIN dim_materials m ON pol.material_code = m.material_code
        LEFT JOIN gr_agg gr ON pol.po_number = gr.po_number AND pol.line_item = gr.line_item
        LEFT JOIN inv_agg inv ON pol.po_number = inv.po_number AND pol.line_item = inv.line_item
    ),
    flagged_reasons AS (
        SELECT 
            *,
            -- Exception 1: Missing Goods Receipt
            CASE 
                WHEN invoiced_quantity > 0 AND received_quantity = 0 
                THEN 'MISSING_GR' 
                ELSE NULL 
            END AS reason_missing_gr,

            -- Exception 2: Quantity Over-Invoiced (billed strictly > received)
            CASE 
                WHEN invoiced_quantity > received_quantity AND received_quantity > 0 
                THEN 'QUANTITY_OVER_INVOICE' 
                ELSE NULL 
            END AS reason_qty_over,

            -- Exception 3: Price Variance Outside Tolerance (+/- 2%)
            CASE 
                WHEN invoiced_quantity > 0 AND (price_variance_pct > 2.0 OR price_variance_pct < -2.0)
                THEN 'PRICE_VARIANCE' 
                ELSE NULL 
            END AS reason_price_var,

            -- Exception 4: Overdue Open PO Line (Expected delivery date has passed, and open quantity remains)
            -- Crucial: If expected delivery date is in future, NOT overdue!
            CASE 
                WHEN expected_delivery_date < '2026-11-17' AND received_quantity < ordered_quantity
                THEN 'OVERDUE_OPEN_PO' 
                ELSE NULL 
            END AS reason_overdue
        FROM reconciliation_base
    ),
    consolidated_exceptions AS (
        SELECT 
            po_number,
            line_item,
            supplier_id,
            supplier_name,
            contact_email,
            material_code,
            material_description,
            ordered_quantity,
            received_quantity,
            invoiced_quantity,
            po_unit_price,
            invoice_unit_price,
            expected_delivery_date,
            po_line_total,
            invoiced_amount,
            qty_discrepancy,
            price_variance,
            price_variance_pct,
            gr_count,
            gr_numbers,
            invoice_count,
            relevant_invoice_ids,

            -- Multi-reason concatenation without inflating rows
            TRIM(
                COALESCE(reason_missing_gr || '; ', '') ||
                COALESCE(reason_qty_over || '; ', '') ||
                COALESCE(reason_price_var || '; ', '') ||
                COALESCE(reason_overdue, ''),
                '; '
            ) AS exception_reasons,

            -- Primary Exception Classification
            CASE 
                WHEN reason_missing_gr IS NOT NULL AND reason_price_var IS NOT NULL THEN 'MISSING_GR_AND_PRICE_VARIANCE'
                WHEN reason_qty_over IS NOT NULL AND reason_price_var IS NOT NULL THEN 'QTY_OVER_INVOICE_AND_PRICE_VARIANCE'
                WHEN reason_missing_gr IS NOT NULL THEN 'MISSING_GR'
                WHEN reason_qty_over IS NOT NULL THEN 'QUANTITY_OVER_INVOICE'
                WHEN reason_price_var IS NOT NULL THEN 'PRICE_VARIANCE'
                WHEN reason_overdue IS NOT NULL THEN 'OVERDUE_OPEN_PO'
                ELSE 'CLEAN_MATCH'
            END AS primary_exception_reason,

            -- Match Status
            CASE 
                WHEN reason_missing_gr IS NOT NULL 
                  OR reason_qty_over IS NOT NULL 
                  OR reason_price_var IS NOT NULL 
                  OR reason_overdue IS NOT NULL 
                THEN 'EXCEPTION' 
                ELSE 'CLEAN_MATCH' 
            END AS match_status,

            -- Disputed / Financial Amount at Risk (₹)
            ROUND(
                CASE 
                    WHEN reason_missing_gr IS NOT NULL THEN invoiced_amount
                    WHEN reason_qty_over IS NOT NULL AND reason_price_var IS NOT NULL 
                         THEN (invoiced_quantity * invoice_unit_price) - (received_quantity * po_unit_price)
                    WHEN reason_qty_over IS NOT NULL THEN (invoiced_quantity - received_quantity) * invoice_unit_price
                    WHEN reason_price_var IS NOT NULL THEN invoiced_quantity * MAX(0.0, invoice_unit_price - po_unit_price)
                    WHEN reason_overdue IS NOT NULL THEN (ordered_quantity - received_quantity) * po_unit_price
                    ELSE 0.0 
                END, 
                2
            ) AS amount_at_risk_inr,

            -- Actionable Next Step for Accounts Payable Reviewer
            CASE 
                WHEN reason_missing_gr IS NOT NULL 
                THEN 'Block invoice payment in MIRO; contact warehouse receiving dock to verify physical delivery or enter MIGO.'
                WHEN reason_qty_over IS NOT NULL AND reason_price_var IS NOT NULL 
                THEN 'Immediate payment block; request supplier credit memo for both unauthorized price increase and unreceived quantity.'
                WHEN reason_qty_over IS NOT NULL 
                THEN 'Apply SAP invoice quantity block (R-block); contact vendor for credit note or wait for second GR delivery.'
                WHEN reason_price_var IS NOT NULL 
                THEN 'Place AP price variance block (P-block); dispute unit rate with supplier or seek Buyer PO price amendment.'
                WHEN reason_overdue IS NOT NULL 
                THEN 'Notify Purchasing Buyer; expedite overdue shipment or de-commit/cancel outstanding PO quantity in EKPO.'
                ELSE 'Post invoice for payment (Clear for payment).'
            END AS suggested_next_action
        FROM flagged_reasons
    )
    SELECT * FROM consolidated_exceptions;
    """

    cursor.execute(match_sql)
    conn.commit()
    conn.close()

    print("SAP Procurement database successfully loaded and 3-way match exception table generated!")

if __name__ == "__main__":
    load_sap_database()
