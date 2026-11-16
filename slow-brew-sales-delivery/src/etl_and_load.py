"""
etl_and_load.py
---------------
Extracts raw POS and Zomato CSV exports, applies data cleaning and deduplication,
logs rejected rows into an audit trail, populates dimensional and fact tables,
and saves the result to SQLite and processed CSVs.
"""

import os
import csv
import json
import sqlite3
from datetime import datetime

def parse_iso_timestamp(ts_str):
    try:
        dt = datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S")
        # Ensure within realistic project boundary (Aug 2026 - Nov 2026)
        if dt.year != 2026 or dt.month not in [8, 9, 10, 11]:
            return None
        return dt
    except Exception:
        return None

def get_slot_id(hour):
    if 8 <= hour <= 11:
        return "SLOT-01" # Morning Rush (08:00 - 11:59)
    elif 12 <= hour <= 15:
        return "SLOT-02" # Afternoon Slump (12:00 - 15:59)
    elif 16 <= hour <= 19:
        return "SLOT-03" # Evening Social (16:00 - 19:59)
    elif 20 <= hour <= 23:
        return "SLOT-04" # Night Chill (20:00 - 23:00)
    else:
        return "SLOT-OTHER"

def run_etl():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, "data", "raw")
    proc_dir = os.path.join(base_dir, "data", "processed")
    db_path = os.path.join(base_dir, "database", "slow_brew.db")
    schema_path = os.path.join(base_dir, "database", "schema.sql")
    os.makedirs(proc_dir, exist_ok=True)

    pos_file = os.path.join(raw_dir, "pos_exports.csv")
    zomato_file = os.path.join(raw_dir, "zomato_exports.csv")

    # Connect to SQLite and apply schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    with open(schema_path, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    # Populate Dimensions
    # 1. dim_channels
    channels = [
        ("CHN-POS", "In-Store POS", "Offline POS", 0.0),
        ("CHN-ZOM", "Zomato Delivery", "Online Delivery", 20.0),
    ]
    cursor.executemany("INSERT INTO dim_channels VALUES (?, ?, ?, ?)", channels)

    # 2. dim_time_slots
    slots = [
        ("SLOT-01", "Morning Rush", 8, 11, "08:00 - 11:59 Breakfast and morning coffee peak"),
        ("SLOT-02", "Afternoon Slump", 12, 15, "12:00 - 15:59 Post-lunch dip, iced coffee, workday refresh"),
        ("SLOT-03", "Evening Social", 16, 19, "16:00 - 19:59 Post-work socializing, specialty drinks, toasts"),
        ("SLOT-04", "Night Chill", 20, 23, "20:00 - 23:00 Late-night relaxation, desserts, hot chocolates"),
    ]
    cursor.executemany("INSERT INTO dim_time_slots VALUES (?, ?, ?, ?, ?)", slots)

    # 3. dim_menu_items
    menu_items = [
        ("COF-01", "Espresso Single Origin", "Coffee", 160.0),
        ("COF-02", "Classic Americano", "Coffee", 190.0),
        ("COF-03", "Velvet Cappuccino", "Coffee", 230.0),
        ("COF-04", "Artisan Flat White", "Coffee", 250.0),
        ("COF-05", "Vanilla Cold Brew", "Coffee", 260.0),
        ("COF-06", "Hazelnut Praline Latte", "Coffee", 270.0),
        ("COF-07", "Single Origin Pour Over", "Coffee", 290.0),
        ("COF-08", "Iced Caramel Macchiato", "Coffee", 280.0),
        ("BAK-01", "Butter Flaky Croissant", "Bakery", 180.0),
        ("BAK-02", "Toasted Almond Biscotti", "Bakery", 140.0),
        ("BAK-03", "Blueberry Crumble Muffin", "Bakery", 200.0),
        ("FOD-01", "Sourdough Avocado Toast", "Food", 320.0),
        ("FOD-02", "Paneer Tikka Focaccia", "Food", 290.0),
        ("FOD-03", "Truffle Mushroom Melt", "Food", 340.0),
        ("SPC-01", "Cascara Berry Spritzer", "Specialty", 220.0),
        ("SPC-02", "Uji Ceremonial Matcha", "Specialty", 310.0),
        ("SPC-03", "Belgian Dark Hot Chocolate", "Specialty", 270.0),
    ]
    cursor.executemany("INSERT INTO dim_menu_items VALUES (?, ?, ?, ?)", menu_items)
    item_catalog_ids = {m[0] for m in menu_items}

    # Reading and Validating Raw POS
    rejected_rows = []
    seen_pos_rows = set()
    accepted_pos_records = []

    with open(pos_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_tuple = tuple(sorted(row.items()))
            if row_tuple in seen_pos_rows:
                rejected_rows.append({
                    "source_system": "POS",
                    "raw_order_id": row.get("pos_order_id"),
                    "raw_timestamp": row.get("order_timestamp"),
                    "rejection_reason": "DUPLICATE_SOURCE_ROW",
                    "raw_payload": json.dumps(row),
                    "rejected_at": datetime.now().isoformat()
                })
                continue
            seen_pos_rows.add(row_tuple)

            # Check timestamp
            dt = parse_iso_timestamp(row.get("order_timestamp", ""))
            if not dt:
                rejected_rows.append({
                    "source_system": "POS",
                    "raw_order_id": row.get("pos_order_id"),
                    "raw_timestamp": row.get("order_timestamp"),
                    "rejection_reason": "CORRUPTED_OR_OUT_OF_BOUNDS_TIMESTAMP",
                    "raw_payload": json.dumps(row),
                    "rejected_at": datetime.now().isoformat()
                })
                continue

            # Check quantity and unit price
            try:
                qty = int(row.get("quantity", 0))
                price = float(row.get("unit_price", 0.0))
                if qty <= 0 or price < 0:
                    raise ValueError("Non-positive quantity or price")
            except Exception:
                rejected_rows.append({
                    "source_system": "POS",
                    "raw_order_id": row.get("pos_order_id"),
                    "raw_timestamp": row.get("order_timestamp"),
                    "rejection_reason": "INVALID_QUANTITY_OR_PRICE",
                    "raw_payload": json.dumps(row),
                    "rejected_at": datetime.now().isoformat()
                })
                continue

            # Check menu item mapping
            item_id = row.get("item_id", "").strip()
            if not item_id or item_id not in item_catalog_ids:
                rejected_rows.append({
                    "source_system": "POS",
                    "raw_order_id": row.get("pos_order_id"),
                    "raw_timestamp": row.get("order_timestamp"),
                    "rejection_reason": "MISSING_OR_UNMAPPED_ITEM",
                    "raw_payload": json.dumps(row),
                    "rejected_at": datetime.now().isoformat()
                })
                continue

            accepted_pos_records.append({
                "order_id": row["pos_order_id"],
                "channel_id": "CHN-POS",
                "dt": dt,
                "item_seq": int(row.get("item_seq", 1)),
                "item_id": item_id,
                "quantity": qty,
                "unit_price": price,
                "discount_amt": float(row.get("order_discount_amt", 0.0)),
                "refund_amt": float(row.get("order_refund_amt", 0.0)),
                "status": row.get("order_status", "COMPLETED"),
                "payment_info": row.get("payment_mode", "Cash")
            })

    # Reading and Validating Raw Zomato
    seen_zomato_rows = set()
    accepted_zomato_records = []
    known_pos_order_ids = {r["order_id"] for r in accepted_pos_records}

    with open(zomato_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_tuple = tuple(sorted(row.items()))
            if row_tuple in seen_zomato_rows:
                rejected_rows.append({
                    "source_system": "ZOMATO",
                    "raw_order_id": row.get("zomato_order_id"),
                    "raw_timestamp": row.get("order_timestamp"),
                    "rejection_reason": "DUPLICATE_SOURCE_ROW",
                    "raw_payload": json.dumps(row),
                    "rejected_at": datetime.now().isoformat()
                })
                continue
            seen_zomato_rows.add(row_tuple)

            # Check cross-channel collisions
            z_id = row.get("zomato_order_id", "")
            if z_id in known_pos_order_ids or z_id.startswith("POS-"):
                rejected_rows.append({
                    "source_system": "ZOMATO",
                    "raw_order_id": z_id,
                    "raw_timestamp": row.get("order_timestamp"),
                    "rejection_reason": "CROSS_CHANNEL_ID_COLLISION",
                    "raw_payload": json.dumps(row),
                    "rejected_at": datetime.now().isoformat()
                })
                continue

            # Check timestamp
            dt = parse_iso_timestamp(row.get("order_timestamp", ""))
            if not dt:
                rejected_rows.append({
                    "source_system": "ZOMATO",
                    "raw_order_id": z_id,
                    "raw_timestamp": row.get("order_timestamp"),
                    "rejection_reason": "CORRUPTED_OR_OUT_OF_BOUNDS_TIMESTAMP",
                    "raw_payload": json.dumps(row),
                    "rejected_at": datetime.now().isoformat()
                })
                continue

            # Check quantity and unit price
            try:
                qty = int(row.get("quantity", 0))
                price = float(row.get("unit_price", 0.0))
                if qty <= 0 or price < 0:
                    raise ValueError("Non-positive quantity or price")
            except Exception:
                rejected_rows.append({
                    "source_system": "ZOMATO",
                    "raw_order_id": z_id,
                    "raw_timestamp": row.get("order_timestamp"),
                    "rejection_reason": "INVALID_QUANTITY_OR_PRICE",
                    "raw_payload": json.dumps(row),
                    "rejected_at": datetime.now().isoformat()
                })
                continue

            # Check item mapping
            item_id = row.get("item_id", "").strip()
            if not item_id or item_id not in item_catalog_ids:
                rejected_rows.append({
                    "source_system": "ZOMATO",
                    "raw_order_id": z_id,
                    "raw_timestamp": row.get("order_timestamp"),
                    "rejection_reason": "MISSING_OR_UNMAPPED_ITEM",
                    "raw_payload": json.dumps(row),
                    "rejected_at": datetime.now().isoformat()
                })
                continue

            accepted_zomato_records.append({
                "order_id": z_id,
                "channel_id": "CHN-ZOM",
                "dt": dt,
                "item_seq": int(row.get("item_seq", 1)),
                "item_id": item_id,
                "quantity": qty,
                "unit_price": price,
                "discount_amt": float(row.get("order_discount_amt", 0.0)),
                "refund_amt": float(row.get("order_refund_amt", 0.0)),
                "status": row.get("order_status", "COMPLETED"),
                "payment_info": row.get("delivery_partner_id", "Zomato Partner")
            })

    # Combine accepted records and group by order
    all_records = accepted_pos_records + accepted_zomato_records
    orders_dict = {}
    for r in all_records:
        oid = r["order_id"]
        if oid not in orders_dict:
            orders_dict[oid] = {
                "order_id": oid,
                "channel_id": r["channel_id"],
                "dt": r["dt"],
                "status": r["status"],
                "discount_amt": r["discount_amt"],
                "refund_amt": r["refund_amt"],
                "payment_info": r["payment_info"],
                "items": []
            }
        orders_dict[oid]["items"].append(r)

    # Populate dim_dates from date range
    unique_dates = set()
    for o in orders_dict.values():
        unique_dates.add(o["dt"].date())

    dates_data = []
    for d in sorted(list(unique_dates)):
        date_key = d.strftime("%Y-%m-%d")
        day_of_week = d.weekday() # 0 = Monday, 6 = Sunday
        day_name = d.strftime("%A")
        is_weekend = 1 if day_of_week in [5, 6] else 0
        week_num = d.isocalendar()[1]
        month_name = d.strftime("%B")
        dates_data.append((date_key, date_key, day_of_week, day_name, is_weekend, week_num, month_name))
    cursor.executemany("INSERT INTO dim_dates VALUES (?, ?, ?, ?, ?, ?, ?)", dates_data)

    # Process Orders and Order Items
    fact_orders_rows = []
    fact_items_rows = []

    for oid, o in orders_dict.items():
        dt = o["dt"]
        order_date_str = dt.strftime("%Y-%m-%d")
        order_hour = dt.hour
        slot_id = get_slot_id(order_hour)
        status = o["status"]
        discount_amt = o["discount_amt"]
        refund_amt = o["refund_amt"]
        
        gross_total = sum(it["quantity"] * it["unit_price"] for it in o["items"])
        item_count = len(o["items"])
        total_quantity = sum(it["quantity"] for it in o["items"])

        if status == "CANCELLED":
            net_sales = 0.0
        else:
            net_sales = max(0.0, round(gross_total - discount_amt - refund_amt, 2))

        fact_orders_rows.append((
            oid,
            o["channel_id"],
            dt.strftime("%Y-%m-%d %H:%M:%S"),
            order_date_str,
            order_hour,
            slot_id,
            status,
            round(gross_total, 2),
            round(discount_amt, 2),
            round(refund_amt, 2),
            round(net_sales, 2),
            item_count,
            total_quantity,
            o["payment_info"]
        ))

        # Line items
        for it in o["items"]:
            gross_line = round(it["quantity"] * it["unit_price"], 2)
            if gross_total > 0 and status == "COMPLETED":
                line_share = gross_line / gross_total
                line_net = round(line_share * net_sales, 2)
            else:
                line_net = 0.0

            order_item_id = f"{oid}_{it['item_seq']}"
            fact_items_rows.append((
                order_item_id,
                oid,
                it["item_seq"],
                it["item_id"],
                it["quantity"],
                it["unit_price"],
                gross_line,
                line_net
            ))

    # Insert into Fact Tables
    cursor.executemany(
        "INSERT INTO fact_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        fact_orders_rows
    )
    cursor.executemany(
        "INSERT INTO fact_order_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        fact_items_rows
    )

    # Insert Rejected Rows into Audit Table
    rejected_db_rows = [
        (
            r["source_system"],
            r["raw_order_id"],
            r["raw_timestamp"],
            r["rejection_reason"],
            r["raw_payload"],
            r["rejected_at"]
        )
        for r in rejected_rows
    ]
    cursor.executemany(
        """INSERT INTO rejected_rows_audit 
           (source_system, raw_order_id, raw_timestamp, rejection_reason, raw_payload, rejected_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        rejected_db_rows
    )

    conn.commit()
    conn.close()

    # Save Processed CSVs for transparency and Excel / Power BI loading
    # 1. Cleaned Orders
    with open(os.path.join(proc_dir, "cleaned_orders.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "order_id", "channel_id", "order_timestamp", "order_date", "order_hour",
            "slot_id", "order_status", "gross_order_total", "order_discount_amt",
            "order_refund_amt", "net_sales_amount", "item_count", "total_quantity", "payment_info"
        ])
        writer.writerows(fact_orders_rows)

    # 2. Cleaned Order Items
    with open(os.path.join(proc_dir, "cleaned_order_items.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "order_item_id", "order_id", "item_seq", "item_id", "quantity",
            "unit_price", "gross_line_amount", "allocated_line_net"
        ])
        writer.writerows(fact_items_rows)

    # 3. Rejected Rows
    with open(os.path.join(proc_dir, "rejected_rows.csv"), "w", newline="", encoding="utf-8") as f:
        fieldnames = ["source_system", "raw_order_id", "raw_timestamp", "rejection_reason", "raw_payload", "rejected_at"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rejected_rows)

    print("ETL and Database Load successfully completed!")
    print(f"Total Accepted Orders: {len(fact_orders_rows)}")
    print(f"Total Accepted Order Items: {len(fact_items_rows)}")
    print(f"Total Rejected Rows Logged: {len(rejected_rows)}")

if __name__ == "__main__":
    run_etl()
