-- ==============================================================================
-- Query 04: Supplier Risk & Compliance Scorecard
-- Purpose: Evaluate supplier billing accuracy, mismatch frequency, and exposure.
-- ==============================================================================

SELECT 
    s.supplier_id,
    s.supplier_name,
    s.city,
    s.payment_terms,
    COUNT(r.po_number) AS total_po_lines,
    SUM(CASE WHEN r.match_status = 'CLEAN_MATCH' THEN 1 ELSE 0 END) AS clean_matched_lines,
    SUM(CASE WHEN r.match_status = 'EXCEPTION' THEN 1 ELSE 0 END) AS exception_lines,
    ROUND(
        100.0 * SUM(CASE WHEN r.match_status = 'EXCEPTION' THEN 1 ELSE 0 END) / COUNT(r.po_number),
        1
    ) AS exception_rate_pct,
    ROUND(SUM(r.invoiced_amount), 2) AS total_invoiced_inr,
    ROUND(SUM(r.amount_at_risk_inr), 2) AS total_disputed_risk_inr,
    CASE 
        WHEN SUM(CASE WHEN r.match_status = 'EXCEPTION' THEN 1 ELSE 0 END) = 0 THEN 'LOW RISK (Preferred)'
        WHEN ROUND(100.0 * SUM(CASE WHEN r.match_status = 'EXCEPTION' THEN 1 ELSE 0 END) / COUNT(r.po_number), 1) <= 25.0 THEN 'MEDIUM RISK (Monitor)'
        ELSE 'HIGH RISK (Audit Required)'
    END AS supplier_risk_tier
FROM dim_suppliers s
JOIN rpt_3way_match_exceptions r ON s.supplier_id = r.supplier_id
GROUP BY 
    s.supplier_id,
    s.supplier_name,
    s.city,
    s.payment_terms
ORDER BY 
    total_disputed_risk_inr DESC,
    exception_rate_pct DESC;
