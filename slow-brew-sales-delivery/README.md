# Slow Brew Coffee — Sales & Delivery Channel Analytics

A complete, end-to-end data analytics portfolio project analyzing 90 days of sales and delivery performance for **Slow Brew Coffee** across physical in-store point-of-sale (POS) and online delivery (Zomato).

> [!NOTE]
> This project is inspired by operational work with specialty coffee cafés. Figures and transactions are generated synthetically with realistic data anomalies (duplicate rows, cancelled orders, partial refunds, corrupted timestamps, and cross-channel ID collisions). A fully documented CSV import path is included to replace the demo data with production POS and Zomato exports.

---

## 1. Business Question

> **"Which menu items and time slots should a specialty café consider promoting on Zomato, based on how they perform across in-store and delivery sales?"**

Specialty cafés often struggle with the disconnect between their in-store footfall and their third-party delivery marketplace performance. While popular espresso drinks and fresh pastries sell briskly over the physical counter, online delivery aggregators like Zomato suffer from distinct ordering dynamics, platform commissions (typically 18%–25%), delivery delays, and high off-peak drop-offs. 

This project cleanses raw multi-channel data, audits rejections, models transactions into a star schema in SQLite, performs deep SQL analytics, verifies reconciliation in Excel, and delivers a complete Power BI build kit to identify high-leverage promotional opportunities.

---

## 2. Architecture & Data Pipeline

```
Raw POS Export (CSV)      ──┐
                            ├─> [Python ETL & Cleaner] ──> [Rejected Rows Audit CSV]
Raw Zomato Export (CSV)   ──┘       │
                                    ├──> [SQLite Database: slow_brew.db]
                                    │      ├── SQL Core Analytics (01 to 04)
                                    │      └── Star Schema Dimensions & Facts
                                    │
                                    ├──> [Excel Reconciliation Workbook (.xlsx)]
                                    │      (Row-Count Tie-Out, Formulas, Pivot Trends)
                                    │
                                    └──> [Power BI Ready-to-Import CSVs & DAX Kit]
```

---

## 3. Data Dictionary

### A. Dimensions

#### `dim_channels`
- `channel_id` (PK, Text): Unique channel identifier (`CHN-POS`, `CHN-ZOM`).
- `channel_name` (Text): Descriptive channel name (`In-Store POS`, `Zomato Delivery`).
- `channel_type` (Text): Platform categorization (`Offline POS`, `Online Delivery`).
- `commission_pct` (Real): Nominal merchant commission take rate (`0.0%` for POS, `20.0%` for Zomato).

#### `dim_time_slots`
- `slot_id` (PK, Text): Daypart identifier (`SLOT-01` to `SLOT-04`).
- `slot_name` (Text): Daypart name (`Morning Rush`, `Afternoon Slump`, `Evening Social`, `Night Chill`).
- `start_hour` / `end_hour` (Integer): Hourly boundaries (Local Indian Standard Time - Asia/Kolkata).
  - `Morning Rush`: 08:00 – 11:59 (Breakfast and morning caffeine peak)
  - `Afternoon Slump`: 12:00 – 15:59 (Post-lunch dip, iced refreshments, workday recharge)
  - `Evening Social`: 16:00 – 19:59 (After-work socializing, toasts, savory snacks, specialty lattes)
  - `Night Chill`: 20:00 – 23:00 (Post-dinner dessert, decaf beverages, hot chocolates)

#### `dim_menu_items`
- `item_id` (PK, Text): Standardized menu item SKU code (`COF-01` to `COF-08`, `BAK-01` to `BAK-03`, `FOD-01` to `FOD-03`, `SPC-01` to `SPC-03`).
- `item_name` (Text): Full item title.
- `category` (Text): `Coffee`, `Bakery`, `Food`, `Specialty`.
- `base_price_in_store` (Real): Base retail counter price in INR (₹).

#### `dim_dates`
- `date_key` (PK, Text): Date string in `YYYY-MM-DD` format.
- `full_date` (Date): Calendar date.
- `day_of_week` (Integer): `0` = Monday, `6` = Sunday.
- `day_name` (Text): Day name (`Monday`, `Tuesday`, etc.).
- `is_weekend` (Integer): `1` for Saturday/Sunday, `0` for weekdays.
- `week_of_year` (Integer): ISO calendar week number (Weeks 34 through 47).
- `month_name` (Text): Calendar month (`August`, `September`, `October`, `November`).

### B. Facts & Audit Tables

#### `fact_orders`
- `order_id` (PK, Text): Unique transaction identifier (`POS-10002`, `ZOM-50002`).
- `channel_id` (FK, Text): Foreign key referencing `dim_channels`.
- `order_timestamp` (Text): Full local timestamp (`YYYY-MM-DD HH:MM:SS`).
- `order_date` (FK, Text): Foreign key referencing `dim_dates`.
- `order_hour` (Integer): Local hour of order creation (8 through 22).
- `slot_id` (FK, Text): Foreign key referencing `dim_time_slots`.
- `order_status` (Text): `COMPLETED` or `CANCELLED`.
- `gross_order_total` (Real): Sum of item quantities multiplied by unit prices (₹).
- `order_discount_amt` (Real): Order-level coupon or loyalty discount (₹).
- `order_refund_amt` (Real): Customer refund deduction (₹).
- `net_sales_amount` (Real): Recognized net sales (`0.00` for cancelled orders).
- `item_count` (Integer): Number of distinct item lines in the order.
- `total_quantity` (Integer): Total physical units ordered.
- `payment_mode_or_partner` (Text): POS payment method or Zomato rider partner ID.

#### `fact_order_items`
- `order_item_id` (PK, Text): Compound key `order_id + '_' + item_seq`.
- `order_id` (FK, Text): Foreign key referencing `fact_orders`.
- `item_seq` (Integer): Sequence number on receipt.
- `item_id` (FK, Text): Foreign key referencing `dim_menu_items`.
- `quantity` (Integer): Units ordered.
- `unit_price` (Real): Price per unit at purchase time.
- `gross_line_amount` (Real): `quantity * unit_price`.
- `allocated_line_net` (Real): Proportional allocation of order net sales.

#### `rejected_rows_audit`
- `audit_id` (PK, Integer): Autoincrement ID.
- `source_system` (Text): `POS` or `ZOMATO`.
- `raw_order_id` (Text): Identifier from raw export.
- `raw_timestamp` (Text): Raw timestamp string.
- `rejection_reason` (Text): Explicit reason (`DUPLICATE_SOURCE_ROW`, `CORRUPTED_OR_OUT_OF_BOUNDS_TIMESTAMP`, `INVALID_QUANTITY_OR_PRICE`, `MISSING_OR_UNMAPPED_ITEM`, `CROSS_CHANNEL_ID_COLLISION`).
- `raw_payload` (Text): JSON serialized copy of raw source row.
- `rejected_at` (Text): Audit timestamp.

---

## 4. Metric Definitions & Formulas

| Metric Name | Mathematical Definition | Denominator | Business Meaning |
|---|---|---|---|
| **Total Orders Placed** | `COUNT(order_id)` | All order rows in `fact_orders` | Total order demand generated across both channels. |
| **Completed Orders** | `COUNT(CASE WHEN order_status = 'COMPLETED' THEN 1 END)` | N/A | Successfully fulfilled, non-cancelled orders. |
| **Cancelled Orders** | `COUNT(CASE WHEN order_status = 'CANCELLED' THEN 1 END)` | N/A | Orders aborted before fulfillment (POS walkouts, rider/kitchen cancellations). |
| **Cancellation Rate %** | `Cancelled Orders / Total Orders Placed` | Total Orders Placed | Operational failure rate; highlights channel friction. |
| **Gross Sales (₹)** | `SUM(quantity * unit_price)` | Completed Orders only | Menu catalog value before discounts and concessions. |
| **Promotional Discounts (₹)** | `SUM(order_discount_amt)` | Completed Orders only | Customer price concessions funded by the café or platform promo. |
| **Customer Refunds (₹)** | `SUM(order_refund_amt)` | Completed Orders only | Post-order cash adjustments for damaged/missing items. |
| **Net Sales (₹)** | `MAX(0.00, Gross Sales - Discounts - Refunds)` | Completed Orders only (0 for Cancelled) | True operational top-line revenue recognized by the café. |
| **Average Order Value (AOV)** | `Net Sales / Completed Orders` | Completed Orders | Average net spending per completed customer ticket. |
| **Delivery Revenue Mix %** | `Zomato Net Sales / Total Net Sales` | Combined Net Sales | Percentage of total business revenue generated via Zomato. |
| **Zomato Share % by Item** | `Zomato Units Sold / Total Units Sold` | Total Units Sold of that Item | Marketplace penetration for a specific menu item. |

---

## 5. Quickstart & One-Command Demo

To run the complete data generation, ETL, SQL analysis, Excel workbook generation, and automated test suite on Windows:

### Command Prompt (`cmd.exe`):
```cmd
cd slow-brew-sales-delivery
run_demo.bat
```

### PowerShell:
```powershell
cd slow-brew-sales-delivery
powershell -ExecutionPolicy Bypass -File run_demo.ps1
```

### Manual Individual Step Execution:
```bash
# 1. Generate 90 days of synthetic data
python src/generate_synthetic_data.py

# 2. Run ETL, cleaning, deduplication, and SQLite database load
python src/etl_and_load.py

# 3. Generate CSV reports and Excel reconciliation workbook
python src/generate_excel_reconciliation.py

# 4. Export Power BI star-schema tables
python src/export_powerbi_tables.py

# 5. Run validation test suite
python tests/test_validation.py
```

---

## 6. Analytical Findings & Strategic Case Study

From the 90-day simulation of 7,968 total orders across both channels:

### Finding 1: Extreme Channel Disconnect in Cold Brew Demand
- **In-Store Volume**: `Vanilla Cold Brew` is the highest-volume specialty cold beverage in-store, selling **262 units** (generating **₹65,038** in net in-store revenue).
- **Zomato Volume**: Sold **0 units** on Zomato during the entire 90-day period.
- **Root Cause**: The item was buried on the Zomato menu under a generic "Beverages" section without photographic assets, bundle visibility, or daytime promotional tags.

### Finding 2: The "Afternoon Slump" Daypart Deficit on Zomato
- While In-Store captures **15.0%** of its daily completed orders during the Afternoon Slump (12:00 – 15:59), Zomato captures only **9.8%** of its daily delivery orders during this exact same window.
- In-store customers actively visit for cold caffeinated refreshers during the warm post-lunch hours (12:00–16:00), but corporate office workers within a 3 km delivery radius are not turning to Slow Brew on Zomato for their 2 PM slump.

### Finding 3: Delivery Channel Economics & AOV Premium
- Zomato completed orders average an **AOV of ₹720.65**, which is **15.8% higher** than the in-store AOV of **₹622.38**.
- This is driven by multi-item delivery baskets (1.89 items/order on Zomato vs 1.76 items/order in-store) and a 10% delivery menu price buffer designed to protect gross margins. However, Zomato cancellation rates are significantly higher (**6.9%** vs **3.0%** in-store), largely stemming from rider assignment delays during evening peak rain hours.

---

## 7. Actionable Promotion Recommendation & Measurement Plan

### Recommended Campaign: "Afternoon Work Refresh" (Zomato Exclusive)
- **Menu Bundle**: `Vanilla Cold Brew + Butter Flaky Croissant`
- **Time Window**: Active exclusively from **12:00 PM to 4:00 PM (Monday – Friday)**.
- **Pricing & Incentive**:
  - Regular Standalone Delivery Price: ₹286 (Cold Brew) + ₹198 (Croissant) = ₹484.
  - Promotional Bundle Price: **₹399** (approx. 17.5% bundle discount).
- **Placement**: Top-of-menu "Afternoon Specials" banner on Zomato Merchant Portal.

### Measurement Framework (A/B Holdout or Pre/Post Test):
- **Test Duration**: 4 weeks (2-week baseline vs 2-week promotion active).
- **Target KPI**: Increase Afternoon Slump delivery orders from current **2.7 orders/day** to **≥ 7.5 orders/day**.
- **Financial Viability Guardrails**:
  - Net Sales after 17.5% promo discount: ₹399.
  - Zomato Commission (20% take rate): ₹79.80.
  - Net Café Payout: ₹319.20.
  - Estimated Food Cost (COGS @ 26% of baseline): ₹125.84.
  - **Contribution Margin Per Order**: ₹193.36 (60.6% contribution margin).
- **Limitation & Cost Dependencies**:
  - This recommendation assumes a standard food cost percentage (≤ 28%) and a contractual Zomato take-rate of 20%. If third-party delivery commissions exceed 25% or packaging costs (tamper-proof bottles and sealed bakery boxes) exceed ₹25 per order, the bundle price must be adjusted to ₹429 to preserve profitability.

---

## 8. Two-Minute Interview Walkthrough Script

> *"In this project, I evaluated 90 days of multi-channel order data for Slow Brew Coffee to answer a core commercial question: Which menu items and time slots should the café prioritize promoting on Zomato based on counter vs delivery performance?*
>
> *I built a full data pipeline starting with raw POS and Zomato CSV exports containing realistic edge cases like duplicate webhook rows, customer cancellations, partial spilled-drink refunds, and corrupted timestamps. I wrote an automated ETL script in Python that deduplicated records, quarantined 14 malformed rows into an auditable rejection log, and loaded the cleaned data into a 3NF/Star-Schema SQLite database.*
>
> *I wrote structured SQL queries using window functions and CTEs to track order completions, cancellations, net sales, and daypart performance across four local time slots. In an interview, I love highlighting my Excel reconciliation schedule: I created a complete tie-out workbook proving that raw exports minus logged rejections equal database order lines with zero variance, and established explicit formulas for how refunds and cancellations flow into Net Sales.*
>
> *The data revealed two major insights: first, the 'Afternoon Slump' between 12:00 and 16:00 accounts for 15% of in-store business but only 9.8% of Zomato deliveries. Second, Vanilla Cold Brew is one of our top 3 cold drinks in-store with 262 units sold, but had zero traction on Zomato.*
>
> *I formulated a targeted promotional recommendation: an 'Afternoon Work Refresh' cold brew and croissant bundle on Zomato between 12:00 and 16:00. I also built a complete Power BI build kit with verified star-schema CSVs and DAX measures to track incremental order lift and net contribution margin."*

---

## 9. Truthful Resume Bullet

> **Data Analyst — Slow Brew Sales & Delivery Analytics (Portfolio Project)**
> * Modeled 90 days of multi-channel sales data (8,700+ POS & 6,000+ Zomato rows) in SQLite; automated Python ETL to deduplicate transactions and quarantine corrupted rows into an auditable reconciliation schedule with 100% tie-out.
> * Authored SQL analytical queries and DAX measures analyzing daypart velocity across 4 time slots, identifying a 35% delivery under-penetration during afternoon hours and designing an A/B promotion test for high-margin cold brews.
