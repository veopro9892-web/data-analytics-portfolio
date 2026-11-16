# Power BI Report Build Guide — Slow Brew Coffee

This guide provides exact step-by-step instructions to rebuild the **Slow Brew Sales & Delivery Performance Dashboard** in Microsoft Power BI Desktop.

> [!NOTE]
> Power BI Desktop runs in a native Windows desktop GUI environment. All required data tables have been exported as clean, typed CSV files in `./ready_to_import_csv/`, verified against SQLite and Excel reconciliation totals. Follow the steps below to import and build the 2-page report in ~10 minutes.

---

## 1. Import Ready-to-Use Data

1. Open **Power BI Desktop**.
2. Click **Get Data** -> **Text/CSV**.
3. Import the 6 CSV files from `powerbi/ready_to_import_csv/`:
   - `dim_dates.csv`
   - `dim_channels.csv`
   - `dim_time_slots.csv`
   - `dim_menu_items.csv`
   - `fact_orders.csv`
   - `fact_order_items.csv`
4. In Power Query, verify data types:
   - Dates: `order_date` as `Date`, `order_timestamp` as `Date/Time`.
   - Numerics: `gross_order_total`, `order_discount_amt`, `order_refund_amt`, `net_sales_amount`, `unit_price`, `gross_line_amount`, `allocated_line_net` as `Fixed Decimal Number (Currency)`.
   - Quantities / Counts: `quantity`, `item_count`, `total_quantity` as `Whole Number`.
5. Click **Close & Apply**.

---

## 2. Configure Star-Schema Relationships

Switch to the **Model View** and verify or create the following 5 one-to-many relationships (Single cross-filter direction):

1. `dim_dates[date_key]` (1) ——< (N) `fact_orders[order_date]`
2. `dim_channels[channel_id]` (1) ——< (N) `fact_orders[channel_id]`
3. `dim_time_slots[slot_id]` (1) ——< (N) `fact_orders[slot_id]`
4. `fact_orders[order_id]` (1) ——< (N) `fact_order_items[order_id]`
5. `dim_menu_items[item_id]` (1) ——< (N) `fact_order_items[item_id]`

---

## 3. Add DAX Measures

Create a new blank table named `_Measures` and copy-paste the DAX formulas from `DAX_Measures.dax`:
- `[Total Orders Placed]`
- `[Completed Orders]`
- `[Cancelled Orders]`
- `[Cancellation Rate]` (Format: `0.0%`)
- `[Gross Sales]` (Format: `₹#,##0`)
- `[Total Discounts]` (Format: `₹#,##0`)
- `[Total Refunds]` (Format: `₹#,##0`)
- `[Net Sales]` (Format: `₹#,##0`)
- `[Average Order Value (AOV)]` (Format: `₹#,##0.00`)
- `[In-Store Net Sales]` (Format: `₹#,##0`)
- `[Zomato Net Sales]` (Format: `₹#,##0`)
- `[Delivery Order Mix %]` (Format: `0.0%`)
- `[Delivery Revenue Mix %]` (Format: `0.0%`)
- `[Estimated Zomato Platform Commissions]` (Format: `₹#,##0`)
- `[Estimated Zomato Net Payout]` (Format: `₹#,##0`)

---

## 4. Report Page 1: "Executive Overview & Channel Health"

### Canvas Layout:
1. **Header Bar**:
   - Title: `SLOW BREW COFFEE — SALES & DELIVERY PERFORMANCE`
   - Subtitle: `90-Day Operational Snapshot | In-Store POS vs Zomato Delivery`
   - Slicers: Date Range (`dim_dates[full_date]`), Day of Week (`dim_dates[day_name]`), Channel (`dim_channels[channel_name]`).

2. **Top KPI Cards (Row 1)**:
   - Card 1: `[Net Sales]` (₹50.3L)
   - Card 2: `[Completed Orders]` (7,613)
   - Card 3: `[Average Order Value (AOV)]` (₹661)
   - Card 4: `[Cancellation Rate]` (4.5% overall; POS ~3.0%, Zomato ~6.9%)
   - Card 5: `[Delivery Revenue Mix %]` (44.6%)

3. **Visual 1 (Clustered Bar Chart)**:
   - **X-Axis**: `dim_time_slots[slot_name]`
   - **Y-Axis**: `[Completed Orders]`
   - **Legend**: `dim_channels[channel_name]`
   - *Key takeaway*: Illustrates how Morning Rush dominates In-Store, Evening Social dominates Delivery, and Afternoon Slump represents a major dip in Delivery.

4. **Visual 2 (Line Chart - Weekly Sales Trend)**:
   - **X-Axis**: `dim_dates[week_of_year]`
   - **Y-Axis**: `[Net Sales]`
   - **Legend**: `dim_channels[channel_name]`
   - *Key takeaway*: Shows consistent weekly revenue stability across both channels with healthy weekend spikes.

5. **Visual 3 (Table / Matrix - Channel Comparison)**:
   - Rows: `dim_channels[channel_name]`
   - Values: `[Completed Orders]`, `[Gross Sales]`, `[Total Discounts]`, `[Total Refunds]`, `[Net Sales]`, `[AOV]`, `[Cancellation Rate]`

---

## 5. Report Page 2: "Menu & Time Slot Promotion Opportunity"

### Canvas Layout:
1. **Header Callout**:
   - Title: `ZOMATO PROMOTION TARGETING: AFTERNOON WORK REFRESH`
   - Slicers: Category (`dim_menu_items[category]`), Time Slot (`dim_time_slots[slot_name]`).

2. **Visual 1 (Scatter Plot / Quadrant Analysis)**:
   - **X-Axis**: `[In-Store Net Sales]` (In-Store demand / popularity)
   - **Y-Axis**: `[Zomato Net Sales]` (Delivery demand)
   - **Details**: `dim_menu_items[item_name]`
   - **Color Legend**: `dim_menu_items[category]`
   - *Observation*: Vanilla Cold Brew sits far right on the X-axis (high in-store demand) but near the bottom on the Y-axis (low delivery sales). This visually proves the promotion opportunity!

3. **Visual 2 (100% Stacked Bar Chart - Daypart Distribution by Channel)**:
   - **Y-Axis**: `dim_channels[channel_name]`
   - **X-Axis**: `[Completed Orders]` (Percent of total)
   - **Legend**: `dim_time_slots[slot_name]`
   - *Key takeaway*: Afternoon Slump is 15.0% of In-Store orders, but only 9.8% of Zomato orders.

4. **Visual 3 (Matrix Grid - Item × Time Slot Volume)**:
   - **Rows**: `dim_menu_items[category]`, `dim_menu_items[item_name]`
   - **Columns**: `dim_time_slots[slot_name]`
   - **Values**: `[Total Units Sold]`
   - Conditional formatting: Data bars or gradient shading.

5. **Promotion Business Case Card**:
   - Proposed Offer: `Afternoon Work Refresh: Vanilla Cold Brew + Butter Flaky Croissant`
   - Target Slot: `Afternoon Slump (12:00 - 16:00)` on Zomato.
   - Mechanism: 15% combo discount + featured carousel banner.
   - Financial Constraint: Requires maintaining food cost ≤ 28% to absorb Zomato's 20% take rate.
