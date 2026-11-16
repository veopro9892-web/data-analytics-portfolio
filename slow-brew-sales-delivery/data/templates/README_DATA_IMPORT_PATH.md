# Real Data Replacement & CSV Import Path

To replace the fictional 90-day demo dataset with real-world point-of-sale (POS) and Zomato merchant exports from Slow Brew Coffee:

## 1. Export File Requirements

Place your raw CSV files in `data/raw/` matching the expected schemas below:

### A. In-Store POS Export (`data/raw/pos_exports.csv`)
| Column Name | Expected Type | Description |
|---|---|---|
| `pos_order_id` | Text | Unique bill/receipt ID from POS terminal (e.g. `POS-10024`) |
| `terminal_id` | Text | Terminal or counter identifier (e.g. `TERM-01`) |
| `order_timestamp` | YYYY-MM-DD HH:MM:SS | Local café time of transaction (IST UTC+05:30) |
| `item_seq` | Integer | Sequence number of the item on the bill (1, 2, 3...) |
| `item_id` | Text | Standardized menu item SKU code (e.g. `COF-05`) |
| `item_name` | Text | Display name of the menu item |
| `category` | Text | Category (`Coffee`, `Bakery`, `Food`, `Specialty`) |
| `quantity` | Integer | Units ordered (must be > 0) |
| `unit_price` | Numeric | Selling price per unit before discounts |
| `order_discount_amt` | Numeric | Order-level discount applied to the bill |
| `order_refund_amt` | Numeric | Amount refunded to the customer (if any) |
| `order_status` | Text | `COMPLETED` or `CANCELLED` |
| `payment_mode` | Text | Tender mode (`UPI`, `Card`, `Cash`) |

### B. Zomato Merchant Export (`data/raw/zomato_exports.csv`)
| Column Name | Expected Type | Description |
|---|---|---|
| `zomato_order_id` | Text | Unique Zomato order ID (e.g. `ZOM-50024`) |
| `delivery_partner_id` | Text | Rider ID assigned to pickup |
| `order_timestamp` | YYYY-MM-DD HH:MM:SS | Local order creation timestamp |
| `item_seq` | Integer | Line sequence number |
| `item_id` | Text | Standardized menu item SKU code |
| `item_name` | Text | Name of the ordered item |
| `category` | Text | Category |
| `quantity` | Integer | Units ordered |
| `unit_price` | Numeric | Platform menu price |
| `order_discount_amt` | Numeric | Merchant promotional discount / promo code subsidy |
| `order_refund_amt` | Numeric | Amount refunded for missing/damaged food |
| `order_status` | Text | `COMPLETED` or `CANCELLED` |
| `delivery_rating` | Numeric / Blank | Customer delivery rating (1 to 5) |

---

## 2. Execution Steps

1. Copy your real files over `pos_exports.csv` and `zomato_exports.csv` in `data/raw/`.
2. Run the ETL script:
   ```cmd
   python src/etl_and_load.py
   ```
3. Run report generation:
   ```cmd
   python src/generate_excel_reconciliation.py
   python src/export_powerbi_tables.py
   ```
4. Check `data/processed/rejected_rows.csv` to review any unmapped menu items, corrupted timestamps, or duplicate rows flagged by the pipeline.
