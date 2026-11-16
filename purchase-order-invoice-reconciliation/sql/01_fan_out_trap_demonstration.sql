-- ==============================================================================
-- Query 01: The Cartesian Product / Join Fan-Out Trap Demonstration
-- Scenario: PO-45001003 has 2 Goods Receipts (40 qty, 60 qty = 100 total)
--                      and 2 Invoices (40 qty, 60 qty @ ₹1000 = ₹100,000 total).
-- ==============================================================================

-- A. THE INCORRECT (NAIVE) JOIN QUERY
-- Direct 3-way join of raw tables produces a 2x2 Cartesian product (4 rows)!
-- As a result, SUM(received_quantity) and SUM(invoiced_amount) are DOUBLED (100% inflation).
SELECT 
    'NAIVE RAW JOIN (INCORRECT)' AS query_method,
    pol.po_number,
    pol.line_item,
    pol.ordered_quantity,
    pol.po_unit_price,
    COUNT(*) AS joined_row_count, -- Inflated to 4 rows!
    SUM(gr.received_quantity) AS inflated_received_qty, -- Inflated to 200!
    SUM(inv.invoiced_quantity) AS inflated_invoiced_qty, -- Inflated to 200!
    SUM(inv.invoiced_amount) AS inflated_invoiced_amount_inr -- Inflated to ₹200,000!
FROM fact_po_lines pol
JOIN fact_goods_receipts gr 
    ON pol.po_number = gr.po_number AND pol.line_item = gr.line_item
JOIN fact_invoice_lines inv 
    ON pol.po_number = inv.po_number AND pol.line_item = inv.line_item
WHERE pol.po_number = 'PO-45001003'
GROUP BY 
    pol.po_number, pol.line_item, pol.ordered_quantity, pol.po_unit_price;

-- B. THE CORRECT QUERY (INDEPENDENT AGGREGATION BEFORE JOINING)
-- Receipts and Invoices are pre-aggregated in separate CTEs at (po_number, line_item) level.
-- Result: Exact 1-to-1 match, accurate received qty (100) and invoiced amount (₹100,000).
WITH gr_summary AS (
    SELECT 
        po_number,
        line_item,
        COUNT(DISTINCT gr_number) AS distinct_gr_count,
        SUM(received_quantity) AS correct_received_qty
    FROM fact_goods_receipts
    WHERE po_number = 'PO-45001003'
    GROUP BY po_number, line_item
),
inv_summary AS (
    SELECT 
        po_number,
        line_item,
        COUNT(DISTINCT invoice_number) AS distinct_inv_count,
        SUM(invoiced_quantity) AS correct_invoiced_qty,
        SUM(invoiced_amount) AS correct_invoiced_amount_inr
    FROM fact_invoice_lines
    WHERE po_number = 'PO-45001003'
    GROUP BY po_number, line_item
)
SELECT 
    'INDEPENDENT AGGREGATION (CORRECT)' AS query_method,
    pol.po_number,
    pol.line_item,
    pol.ordered_quantity,
    pol.po_unit_price,
    1 AS joined_row_count,
    gr.correct_received_qty,
    inv.correct_invoiced_qty,
    inv.correct_invoiced_amount_inr
FROM fact_po_lines pol
LEFT JOIN gr_summary gr 
    ON pol.po_number = gr.po_number AND pol.line_item = gr.line_item
LEFT JOIN inv_summary inv 
    ON pol.po_number = inv.po_number AND pol.line_item = inv.line_item
WHERE pol.po_number = 'PO-45001003';
