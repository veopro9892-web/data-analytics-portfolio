-- =====================================================================
-- Database Schema: Slow Brew Coffee Sales & Delivery Performance
-- SQLite 3 Compatible DDL
-- =====================================================================

DROP TABLE IF EXISTS rejected_rows_audit;
DROP TABLE IF EXISTS fact_order_items;
DROP TABLE IF EXISTS fact_orders;
DROP TABLE IF EXISTS dim_dates;
DROP TABLE IF EXISTS dim_time_slots;
DROP TABLE IF EXISTS dim_menu_items;
DROP TABLE IF EXISTS dim_channels;

-- 1. Dimension: Channels
CREATE TABLE dim_channels (
    channel_id TEXT PRIMARY KEY,
    channel_name TEXT NOT NULL,
    channel_type TEXT NOT NULL, -- 'Offline POS', 'Online Delivery'
    commission_pct REAL NOT NULL DEFAULT 0.0 -- 0.0% for In-store, 20.0% for Zomato
);

-- 2. Dimension: Menu Items
CREATE TABLE dim_menu_items (
    item_id TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    category TEXT NOT NULL, -- 'Coffee', 'Bakery', 'Food', 'Specialty'
    base_price_in_store REAL NOT NULL
);

-- 3. Dimension: Time Slots
CREATE TABLE dim_time_slots (
    slot_id TEXT PRIMARY KEY,
    slot_name TEXT NOT NULL,
    start_hour INTEGER NOT NULL,
    end_hour INTEGER NOT NULL,
    slot_description TEXT NOT NULL
);

-- 4. Dimension: Dates
CREATE TABLE dim_dates (
    date_key TEXT PRIMARY KEY, -- 'YYYY-MM-DD'
    full_date DATE NOT NULL,
    day_of_week INTEGER NOT NULL, -- 0=Monday, 6=Sunday
    day_name TEXT NOT NULL,
    is_weekend INTEGER NOT NULL, -- 1=True, 0=False
    week_of_year INTEGER NOT NULL,
    month_name TEXT NOT NULL
);

-- 5. Fact Table: Orders
CREATE TABLE fact_orders (
    order_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    order_timestamp TEXT NOT NULL,
    order_date TEXT NOT NULL,
    order_hour INTEGER NOT NULL,
    slot_id TEXT NOT NULL,
    order_status TEXT NOT NULL, -- 'COMPLETED', 'CANCELLED'
    gross_order_total REAL NOT NULL,
    order_discount_amt REAL NOT NULL,
    order_refund_amt REAL NOT NULL,
    net_sales_amount REAL NOT NULL,
    item_count INTEGER NOT NULL,
    total_quantity INTEGER NOT NULL,
    payment_mode_or_partner TEXT,
    FOREIGN KEY (channel_id) REFERENCES dim_channels (channel_id),
    FOREIGN KEY (order_date) REFERENCES dim_dates (date_key),
    FOREIGN KEY (slot_id) REFERENCES dim_time_slots (slot_id)
);

-- 6. Fact Table: Order Items
CREATE TABLE fact_order_items (
    order_item_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    item_seq INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    gross_line_amount REAL NOT NULL,
    allocated_line_net REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES fact_orders (order_id),
    FOREIGN KEY (item_id) REFERENCES dim_menu_items (item_id)
);

-- 7. Audit Table: Rejected Rows
CREATE TABLE rejected_rows_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_system TEXT NOT NULL, -- 'POS', 'ZOMATO'
    raw_order_id TEXT,
    raw_timestamp TEXT,
    rejection_reason TEXT NOT NULL,
    raw_payload TEXT NOT NULL,
    rejected_at TEXT NOT NULL
);

-- Indexes for query performance
CREATE INDEX idx_orders_date ON fact_orders (order_date);
CREATE INDEX idx_orders_channel ON fact_orders (channel_id);
CREATE INDEX idx_orders_slot ON fact_orders (slot_id);
CREATE INDEX idx_orders_status ON fact_orders (order_status);
CREATE INDEX idx_items_order ON fact_order_items (order_id);
CREATE INDEX idx_items_item ON fact_order_items (item_id);
