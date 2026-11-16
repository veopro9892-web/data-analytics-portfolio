-- =====================================================================
-- Query 02: Channel & Daily Core KPIs
-- Purpose: Calculate completed orders, net sales, AOV, cancellations,
--          and channel mix across in-store and delivery channels.
-- =====================================================================

-- 1. High-Level Executive Channel Summary (90-Day Aggregate)
SELECT 
    c.channel_name,
    COUNT(o.order_id) AS total_orders_placed,
    SUM(CASE WHEN o.order_status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_orders,
    SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled_orders,
    ROUND(
        100.0 * SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1 ELSE 0 END) / COUNT(o.order_id), 
        2
    ) AS cancellation_rate_pct,
    ROUND(SUM(o.gross_order_total), 2) AS gross_sales_inr,
    ROUND(SUM(o.order_discount_amt), 2) AS total_discounts_inr,
    ROUND(SUM(o.order_refund_amt), 2) AS total_refunds_inr,
    ROUND(SUM(o.net_sales_amount), 2) AS net_sales_inr,
    ROUND(
        SUM(o.net_sales_amount) / NULLIF(SUM(CASE WHEN o.order_status = 'COMPLETED' THEN 1 ELSE 0 END), 0), 
        2
    ) AS aov_inr,
    ROUND(
        1.0 * SUM(CASE WHEN o.order_status = 'COMPLETED' THEN o.total_quantity ELSE 0 END) / 
        NULLIF(SUM(CASE WHEN o.order_status = 'COMPLETED' THEN 1 ELSE 0 END), 0),
        2
    ) AS avg_items_per_completed_order
FROM fact_orders o
JOIN dim_channels c ON o.channel_id = c.channel_id
GROUP BY 
    c.channel_name;

-- 2. Weekly Trend by Channel (For time-series monitoring & reconciliation)
SELECT 
    d.week_of_year,
    c.channel_name,
    COUNT(o.order_id) AS total_orders,
    SUM(CASE WHEN o.order_status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_orders,
    SUM(CASE WHEN o.order_status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled_orders,
    ROUND(SUM(o.gross_order_total), 2) AS gross_sales_inr,
    ROUND(SUM(o.order_discount_amt), 2) AS discounts_inr,
    ROUND(SUM(o.order_refund_amt), 2) AS refunds_inr,
    ROUND(SUM(o.net_sales_amount), 2) AS net_sales_inr,
    ROUND(
        SUM(o.net_sales_amount) / NULLIF(SUM(CASE WHEN o.order_status = 'COMPLETED' THEN 1 ELSE 0 END), 0), 
        2
    ) AS weekly_aov_inr
FROM fact_orders o
JOIN dim_dates d ON o.order_date = d.date_key
JOIN dim_channels c ON o.channel_id = c.channel_id
GROUP BY 
    d.week_of_year,
    c.channel_name
ORDER BY 
    d.week_of_year ASC,
    c.channel_name ASC;

-- 3. Day of Week Performance (In-Store vs Zomato)
SELECT 
    d.day_name,
    d.day_of_week,
    d.is_weekend,
    c.channel_name,
    SUM(CASE WHEN o.order_status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_orders,
    ROUND(SUM(o.net_sales_amount), 2) AS net_sales_inr,
    ROUND(
        SUM(o.net_sales_amount) / NULLIF(SUM(CASE WHEN o.order_status = 'COMPLETED' THEN 1 ELSE 0 END), 0), 
        2
    ) AS aov_inr
FROM fact_orders o
JOIN dim_dates d ON o.order_date = d.date_key
JOIN dim_channels c ON o.channel_id = c.channel_id
GROUP BY 
    d.day_of_week,
    d.day_name,
    d.is_weekend,
    c.channel_name
ORDER BY 
    d.day_of_week ASC,
    c.channel_name ASC;
