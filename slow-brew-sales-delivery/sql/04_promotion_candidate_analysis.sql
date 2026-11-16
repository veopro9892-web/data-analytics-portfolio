-- =====================================================================
-- Query 04: Zomato Promotion Candidate Analysis
-- Purpose: Pinpoint the optimal menu item and time slot to promote on Zomato
--          by analyzing the performance gap between In-Store and Delivery.
-- =====================================================================

-- 1. Identify "In-Store Champions" with low Zomato penetration
WITH item_channel_summary AS (
    SELECT 
        m.item_id,
        m.item_name,
        m.category,
        SUM(CASE WHEN fo.channel_id = 'CHN-POS' THEN foi.quantity ELSE 0 END) AS in_store_units,
        ROUND(SUM(CASE WHEN fo.channel_id = 'CHN-POS' THEN foi.allocated_line_net ELSE 0 END), 2) AS in_store_net_inr,
        SUM(CASE WHEN fo.channel_id = 'CHN-ZOM' THEN foi.quantity ELSE 0 END) AS zomato_units,
        ROUND(SUM(CASE WHEN fo.channel_id = 'CHN-ZOM' THEN foi.allocated_line_net ELSE 0 END), 2) AS zomato_net_inr,
        SUM(foi.quantity) AS total_units_sold,
        ROUND(SUM(foi.allocated_line_net), 2) AS total_net_inr
    FROM fact_order_items foi
    JOIN fact_orders fo ON foi.order_id = fo.order_id
    JOIN dim_menu_items m ON foi.item_id = m.item_id
    WHERE fo.order_status = 'COMPLETED'
    GROUP BY 
        m.item_id,
        m.item_name,
        m.category
)
SELECT 
    item_id,
    item_name,
    category,
    in_store_units,
    zomato_units,
    total_units_sold,
    ROUND(100.0 * zomato_units / NULLIF(total_units_sold, 0), 1) AS zomato_share_pct,
    in_store_net_inr,
    zomato_net_inr,
    total_net_inr,
    CASE 
        WHEN in_store_units >= 200 AND (100.0 * zomato_units / total_units_sold) < 15.0 
        THEN 'HIGH PRIORITY: Proven In-Store, Severe Zomato Deficit'
        WHEN zomato_units > in_store_units 
        THEN 'Delivery Leader'
        ELSE 'Balanced / Niche'
    END AS promotion_candidacy_status
FROM item_channel_summary
ORDER BY 
    in_store_units DESC;

-- 2. Time Slot Gap Analysis: In-Store Traffic vs Zomato Delivery
WITH slot_channel_agg AS (
    SELECT 
        ts.slot_id,
        ts.slot_name,
        SUM(CASE WHEN fo.channel_id = 'CHN-POS' THEN 1 ELSE 0 END) AS instore_orders,
        SUM(CASE WHEN fo.channel_id = 'CHN-POS' THEN fo.net_sales_amount ELSE 0 END) AS instore_net_sales,
        SUM(CASE WHEN fo.channel_id = 'CHN-ZOM' THEN 1 ELSE 0 END) AS zomato_orders,
        SUM(CASE WHEN fo.channel_id = 'CHN-ZOM' THEN fo.net_sales_amount ELSE 0 END) AS zomato_net_sales,
        COUNT(fo.order_id) AS total_orders,
        SUM(fo.net_sales_amount) AS total_net_sales
    FROM fact_orders fo
    JOIN dim_time_slots ts ON fo.slot_id = ts.slot_id
    WHERE fo.order_status = 'COMPLETED'
    GROUP BY 
        ts.slot_id,
        ts.slot_name
)
SELECT 
    slot_id,
    slot_name,
    instore_orders,
    ROUND(100.0 * instore_orders / SUM(instore_orders) OVER (), 1) AS instore_order_pct,
    zomato_orders,
    ROUND(100.0 * zomato_orders / SUM(zomato_orders) OVER (), 1) AS zomato_order_pct,
    ROUND(instore_net_sales, 2) AS instore_net_sales_inr,
    ROUND(zomato_net_sales, 2) AS zomato_net_sales_inr,
    ROUND(100.0 * zomato_orders / total_orders, 1) AS zomato_delivery_mix_pct
FROM slot_channel_agg
ORDER BY slot_id ASC;

-- 3. Targeted Recommendation Query:
-- Cross-tab of Vanilla Cold Brew & Butter Croissant during Afternoon Slump
SELECT 
    ts.slot_name,
    c.channel_name,
    m.item_name,
    SUM(foi.quantity) AS units_sold,
    ROUND(SUM(foi.allocated_line_net), 2) AS net_sales_inr
FROM fact_order_items foi
JOIN fact_orders fo ON foi.order_id = fo.order_id
JOIN dim_menu_items m ON foi.item_id = m.item_id
JOIN dim_channels c ON fo.channel_id = c.channel_id
JOIN dim_time_slots ts ON fo.slot_id = ts.slot_id
WHERE fo.order_status = 'COMPLETED'
  AND fo.slot_id = 'SLOT-02' -- Afternoon Slump
  AND m.item_id IN ('COF-05', 'BAK-01') -- Vanilla Cold Brew, Butter Croissant
GROUP BY 
    ts.slot_name,
    c.channel_name,
    m.item_name;
