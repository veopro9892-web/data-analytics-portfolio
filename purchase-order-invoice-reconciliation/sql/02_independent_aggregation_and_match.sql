-- ==============================================================================
-- Query 02: Full 3-Way Match Reconciliation Query (Independent Aggregation)
-- Simulating SAP S/4HANA PO (EKPO) vs MIGO GR (MSEG) vs MIRO Invoice (RSEG)
-- ==============================================================================

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
        ROUND(COALESCE(SUM(invoiced_amount) / NULLIF(SUM(invoiced_quantity), 0), 0.0), 2) AS avg_invoice_unit_price,
        MAX(invoice_date) AS latest_invoice_date
    FROM fact_invoice_lines
    GROUP BY po_number, line_item
)
SELECT 
    pol.po_number,
    pol.line_item,
    po.po_date,
    s.supplier_id,
    s.supplier_name,
    pol.material_code,
    m.material_description,
    pol.ordered_quantity,
    pol.po_unit_price,
    pol.po_line_total,
    COALESCE(gr.total_received_qty, 0.0) AS received_quantity,
    COALESCE(inv.total_invoiced_qty, 0.0) AS invoiced_quantity,
    COALESCE(inv.avg_invoice_unit_price, 0.0) AS invoice_unit_price,
    COALESCE(inv.total_invoiced_amount, 0.0) AS invoiced_amount,
    COALESCE(inv.relevant_invoice_ids, 'NONE') AS relevant_invoice_ids,
    
    -- Discrepancies
    ROUND(COALESCE(inv.total_invoiced_qty, 0.0) - COALESCE(gr.total_received_qty, 0.0), 2) AS qty_variance,
    ROUND(COALESCE(inv.avg_invoice_unit_price, 0.0) - pol.po_unit_price, 2) AS unit_price_variance,
    
    -- Match Status
    CASE 
        WHEN COALESCE(inv.total_invoiced_qty, 0.0) > 0 AND COALESCE(gr.total_received_qty, 0.0) = 0 THEN 'EXCEPTION'
        WHEN COALESCE(inv.total_invoiced_qty, 0.0) > COALESCE(gr.total_received_qty, 0.0) THEN 'EXCEPTION'
        WHEN COALESCE(inv.total_invoiced_qty, 0.0) > 0 AND ABS((COALESCE(inv.avg_invoice_unit_price, 0.0) - pol.po_unit_price) / pol.po_unit_price) > 0.02 THEN 'EXCEPTION'
        WHEN pol.expected_delivery_date < '2026-11-17' AND COALESCE(gr.total_received_qty, 0.0) < pol.ordered_quantity THEN 'EXCEPTION'
        ELSE 'CLEAN_MATCH'
    END AS match_status
FROM fact_po_lines pol
JOIN fact_purchase_orders po ON pol.po_number = po.po_number
JOIN dim_suppliers s ON po.supplier_id = s.supplier_id
JOIN dim_materials m ON pol.material_code = m.material_code
LEFT JOIN gr_agg gr ON pol.po_number = gr.po_number AND pol.line_item = gr.line_item
LEFT JOIN inv_agg inv ON pol.po_number = inv.po_number AND pol.line_item = inv.line_item
ORDER BY pol.po_number, pol.line_item;
