-- ==============================================================================
-- Query 03: Exception Classification & Financial Exposure
-- Purpose: Aggregate exceptions by primary category and assess accounts payable risk.
-- ==============================================================================

-- 1. Exception Summary by Primary Reason
SELECT 
    primary_exception_reason,
    COUNT(*) AS affected_po_lines,
    ROUND(SUM(ordered_quantity * po_unit_price), 2) AS total_po_commitment_inr,
    ROUND(SUM(invoiced_amount), 2) AS total_invoiced_inr,
    ROUND(SUM(amount_at_risk_inr), 2) AS total_amount_at_risk_inr,
    ROUND(
        100.0 * COUNT(*) / (SELECT COUNT(*) FROM rpt_3way_match_exceptions), 
        2
    ) AS pct_of_all_po_lines
FROM rpt_3way_match_exceptions
GROUP BY primary_exception_reason
ORDER BY total_amount_at_risk_inr DESC;

-- 2. Line Detail of High-Risk Exceptions (Pending AP Action)
SELECT 
    po_number,
    line_item,
    supplier_name,
    material_description,
    ordered_quantity,
    received_quantity,
    invoiced_quantity,
    po_unit_price,
    invoice_unit_price,
    price_variance_pct,
    relevant_invoice_ids,
    exception_reasons,
    amount_at_risk_inr,
    suggested_next_action
FROM rpt_3way_match_exceptions
WHERE match_status = 'EXCEPTION'
ORDER BY amount_at_risk_inr DESC;
