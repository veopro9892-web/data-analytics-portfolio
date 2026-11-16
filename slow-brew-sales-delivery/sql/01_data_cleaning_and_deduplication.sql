-- =====================================================================
-- Query 01: Data Quality & Rejection Audit
-- Purpose: Verify accepted vs rejected rows, deduplication counts,
--          and cross-channel data integrity.
-- =====================================================================

-- 1. Summary of rejected records by source system and reason
SELECT 
    source_system,
    rejection_reason,
    COUNT(*) AS rejected_row_count,
    MIN(raw_timestamp) AS sample_earliest_timestamp,
    MAX(raw_timestamp) AS sample_latest_timestamp
FROM rejected_rows_audit
GROUP BY 
    source_system,
    rejection_reason
ORDER BY 
    source_system,
    rejected_row_count DESC;

-- 2. Audit check: Ensure fact_orders has zero duplicate order IDs
SELECT 
    order_id,
    COUNT(*) AS occurrence_count
FROM fact_orders
GROUP BY order_id
HAVING COUNT(*) > 1;

-- 3. Audit check: Ensure zero negative prices or quantities in fact_order_items
SELECT 
    COUNT(*) AS invalid_line_count
FROM fact_order_items
WHERE quantity <= 0 OR unit_price < 0;

-- 4. Reconcile raw row count vs accepted order lines + rejected rows
-- (Verified in Excel Reconciliation schedule)
SELECT 
    'POS' AS source,
    (SELECT COUNT(*) FROM fact_order_items foi JOIN fact_orders fo ON foi.order_id = fo.order_id WHERE fo.channel_id = 'CHN-POS') AS accepted_lines,
    (SELECT COUNT(*) FROM rejected_rows_audit WHERE source_system = 'POS') AS rejected_lines
UNION ALL
SELECT 
    'ZOMATO' AS source,
    (SELECT COUNT(*) FROM fact_order_items foi JOIN fact_orders fo ON foi.order_id = fo.order_id WHERE fo.channel_id = 'CHN-ZOM') AS accepted_lines,
    (SELECT COUNT(*) FROM rejected_rows_audit WHERE source_system = 'ZOMATO') AS rejected_lines;
