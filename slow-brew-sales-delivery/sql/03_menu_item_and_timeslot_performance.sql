-- =====================================================================
-- Query 03: Menu Item & Time Slot Performance
-- Purpose: Evaluate item unit velocity, net revenue contribution,
--          and performance across the 4 dayparts/time slots.
-- =====================================================================

-- 1. Item Performance by Channel (Velocity & Sales)
SELECT 
    m.category,
    m.item_name,
    c.channel_name,
    SUM(foi.quantity) AS total_units_sold,
    ROUND(SUM(foi.gross_line_amount), 2) AS gross_item_sales_inr,
    ROUND(SUM(foi.allocated_line_net), 2) AS net_item_sales_inr,
    ROUND(
        100.0 * SUM(foi.allocated_line_net) / 
        SUM(SUM(foi.allocated_line_net)) OVER (PARTITION BY c.channel_name),
        2
    ) AS pct_channel_revenue_share
FROM fact_order_items foi
JOIN fact_orders fo ON foi.order_id = fo.order_id
JOIN dim_menu_items m ON foi.item_id = m.item_id
JOIN dim_channels c ON fo.channel_id = c.channel_id
WHERE fo.order_status = 'COMPLETED'
GROUP BY 
    m.category,
    m.item_name,
    c.channel_name
ORDER BY 
    m.category,
    net_item_sales_inr DESC;

-- 2. Time Slot Channel Breakdown (Traffic & Revenue Distribution)
SELECT 
    ts.slot_name,
    ts.slot_description,
    c.channel_name,
    COUNT(fo.order_id) AS completed_orders,
    ROUND(SUM(fo.net_sales_amount), 2) AS net_sales_inr,
    ROUND(
        SUM(fo.net_sales_amount) / NULLIF(COUNT(fo.order_id), 0),
        2
    ) AS aov_inr,
    ROUND(
        100.0 * COUNT(fo.order_id) / 
        SUM(COUNT(fo.order_id)) OVER (PARTITION BY c.channel_name),
        2
    ) AS pct_orders_within_channel
FROM fact_orders fo
JOIN dim_time_slots ts ON fo.slot_id = ts.slot_id
JOIN dim_channels c ON fo.channel_id = c.channel_id
WHERE fo.order_status = 'COMPLETED'
GROUP BY 
    ts.slot_id,
    ts.slot_name,
    ts.slot_description,
    c.channel_name
ORDER BY 
    ts.slot_id ASC,
    c.channel_name ASC;

-- 3. Item x Time Slot Cross-Tab Matrix (Total Quantity Sold)
SELECT 
    m.item_name,
    m.category,
    SUM(CASE WHEN fo.slot_id = 'SLOT-01' THEN foi.quantity ELSE 0 END) AS morning_rush_units,
    SUM(CASE WHEN fo.slot_id = 'SLOT-02' THEN foi.quantity ELSE 0 END) AS afternoon_slump_units,
    SUM(CASE WHEN fo.slot_id = 'SLOT-03' THEN foi.quantity ELSE 0 END) AS evening_social_units,
    SUM(CASE WHEN fo.slot_id = 'SLOT-04' THEN foi.quantity ELSE 0 END) AS night_chill_units,
    SUM(foi.quantity) AS total_units_sold,
    ROUND(SUM(foi.allocated_line_net), 2) AS total_net_sales_inr
FROM fact_order_items foi
JOIN fact_orders fo ON foi.order_id = fo.order_id
JOIN dim_menu_items m ON foi.item_id = m.item_id
WHERE fo.order_status = 'COMPLETED'
GROUP BY 
    m.item_id,
    m.item_name,
    m.category
ORDER BY 
    total_net_sales_inr DESC;
