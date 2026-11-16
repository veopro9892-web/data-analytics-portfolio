"""
generate_synthetic_data.py
--------------------------
Generates 90 days of realistic, labeled synthetic sales and delivery data
for Slow Brew Coffee (In-Store POS and Zomato delivery).

Includes realistic data anomalies:
- Exact duplicate export rows
- Cancelled orders
- Partial and full refunds
- Corrupted timestamps
- Negative quantity / price entries
- Missing required fields
- Cross-channel ID collisions

Deterministic execution via fixed random seed (42).
"""

import os
import random
import csv
from datetime import datetime, timedelta

def generate_data():
    random.seed(42)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_data_dir = os.path.join(base_dir, "data", "raw")
    os.makedirs(raw_data_dir, exist_ok=True)

    pos_file = os.path.join(raw_data_dir, "pos_exports.csv")
    zomato_file = os.path.join(raw_data_dir, "zomato_exports.csv")

    start_date = datetime(2026, 8, 19, 8, 0, 0) # 90 days up to 2026-11-16
    days = 90

    # Menu Catalog with category, item_name, base_price
    catalog = [
        {"item_id": "COF-01", "category": "Coffee", "item_name": "Espresso Single Origin", "price": 160.0},
        {"item_id": "COF-02", "category": "Coffee", "item_name": "Classic Americano", "price": 190.0},
        {"item_id": "COF-03", "category": "Coffee", "item_name": "Velvet Cappuccino", "price": 230.0},
        {"item_id": "COF-04", "category": "Coffee", "item_name": "Artisan Flat White", "price": 250.0},
        {"item_id": "COF-05", "category": "Coffee", "item_name": "Vanilla Cold Brew", "price": 260.0},
        {"item_id": "COF-06", "category": "Coffee", "item_name": "Hazelnut Praline Latte", "price": 270.0},
        {"item_id": "COF-07", "category": "Coffee", "item_name": "Single Origin Pour Over", "price": 290.0},
        {"item_id": "COF-08", "category": "Coffee", "item_name": "Iced Caramel Macchiato", "price": 280.0},
        {"item_id": "BAK-01", "category": "Bakery", "item_name": "Butter Flaky Croissant", "price": 180.0},
        {"item_id": "BAK-02", "category": "Bakery", "item_name": "Toasted Almond Biscotti", "price": 140.0},
        {"item_id": "BAK-03", "category": "Bakery", "item_name": "Blueberry Crumble Muffin", "price": 200.0},
        {"item_id": "FOD-01", "category": "Food", "item_name": "Sourdough Avocado Toast", "price": 320.0},
        {"item_id": "FOD-02", "category": "Food", "item_name": "Paneer Tikka Focaccia", "price": 290.0},
        {"item_id": "FOD-03", "category": "Food", "item_name": "Truffle Mushroom Melt", "price": 340.0},
        {"item_id": "SPC-01", "category": "Specialty", "item_name": "Cascara Berry Spritzer", "price": 220.0},
        {"item_id": "SPC-02", "category": "Specialty", "item_name": "Uji Ceremonial Matcha", "price": 310.0},
        {"item_id": "SPC-03", "category": "Specialty", "item_name": "Belgian Dark Hot Chocolate", "price": 270.0},
    ]

    item_lookup = {item["item_id"]: item for item in catalog}

    pos_rows = []
    zomato_rows = []

    pos_order_counter = 10001
    zomato_order_counter = 50001

    # Daily generation loop
    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)
        day_of_week = current_date.strftime("%A")
        is_weekend = day_of_week in ["Saturday", "Sunday"]

        # Base order counts per channel
        # POS: 40-75 orders/day (weekends higher)
        pos_daily_orders = random.randint(55, 80) if is_weekend else random.randint(40, 60)
        # Zomato: 25-50 orders/day (weekends higher)
        zomato_daily_orders = random.randint(35, 55) if is_weekend else random.randint(22, 40)

        # 1. Generate POS Orders
        for _ in range(pos_daily_orders):
            pos_order_counter += 1
            order_id = f"POS-{pos_order_counter}"
            
            # Time slot weighting for In-Store:
            # Morning Rush (8-11:59): 45%
            # Afternoon Slump (12-15:59): 15%
            # Evening Social (16-19:59): 30%
            # Night Chill (20-22:59): 10%
            slot_choice = random.choices(
                ["Morning Rush", "Afternoon Slump", "Evening Social", "Night Chill"],
                weights=[0.45, 0.15, 0.30, 0.10]
            )[0]

            if slot_choice == "Morning Rush":
                hour = random.randint(8, 11)
            elif slot_choice == "Afternoon Slump":
                hour = random.randint(12, 15)
            elif slot_choice == "Evening Social":
                hour = random.randint(16, 19)
            else:
                hour = random.randint(20, 22)

            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            order_dt = current_date.replace(hour=hour, minute=minute, second=second)
            order_timestamp_str = order_dt.strftime("%Y-%m-%d %H:%M:%S")

            # Status: 97% Completed, 3% Cancelled
            is_cancelled = random.random() < 0.03
            status = "CANCELLED" if is_cancelled else "COMPLETED"

            # Number of items (1 to 4)
            num_items = random.choices([1, 2, 3, 4], weights=[0.45, 0.35, 0.15, 0.05])[0]
            
            # Pick items based on slot preference
            if slot_choice == "Morning Rush":
                item_pool = ["COF-01", "COF-02", "COF-03", "COF-04", "BAK-01", "BAK-02", "BAK-03"]
            elif slot_choice == "Afternoon Slump":
                item_pool = ["COF-05", "COF-07", "COF-02", "SPC-01", "BAK-01"]
            elif slot_choice == "Evening Social":
                item_pool = ["COF-03", "COF-06", "COF-08", "FOD-01", "FOD-02", "FOD-03", "SPC-02"]
            else:
                item_pool = ["SPC-03", "COF-03", "BAK-01", "BAK-03", "COF-06"]

            chosen_item_ids = random.choices(item_pool, k=num_items)
            
            # Calculate line items
            order_gross = 0.0
            line_details = []
            for item_idx, it_id in enumerate(chosen_item_ids, 1):
                item_meta = item_lookup[it_id]
                qty = random.choices([1, 2], weights=[0.9, 0.1])[0]
                unit_price = item_meta["price"]
                line_subtotal = qty * unit_price
                order_gross += line_subtotal
                line_details.append({
                    "item_seq": item_idx,
                    "item_id": it_id,
                    "item_name": item_meta["item_name"],
                    "category": item_meta["category"],
                    "qty": qty,
                    "unit_price": unit_price
                })

            # In-store discounts: occasional loyalty discount 5-10% (10% chance)
            order_discount = 0.0
            if not is_cancelled and random.random() < 0.10:
                order_discount = round(order_gross * random.choice([0.05, 0.10]), 2)

            # Refunds:
            # If cancelled, refund = gross - discount (or 0 if uncharged, but let's record 0 sales)
            # If completed, 1% chance of partial refund (e.g. spilled drink or incorrect bakery item)
            refund_amount = 0.0
            if not is_cancelled and random.random() < 0.015:
                # partial refund of first item
                refund_amount = round(min(line_details[0]["unit_price"], order_gross - order_discount), 2)

            for line in line_details:
                pos_rows.append({
                    "pos_order_id": order_id,
                    "terminal_id": random.choice(["TERM-01", "TERM-02"]),
                    "order_timestamp": order_timestamp_str,
                    "item_seq": line["item_seq"],
                    "item_id": line["item_id"],
                    "item_name": line["item_name"],
                    "category": line["category"],
                    "quantity": line["qty"],
                    "unit_price": line["unit_price"],
                    "order_discount_amt": order_discount,
                    "order_refund_amt": refund_amount,
                    "order_status": status,
                    "payment_mode": random.choice(["UPI", "Card", "Cash"])
                })

        # 2. Generate Zomato Orders
        for _ in range(zomato_daily_orders):
            zomato_order_counter += 1
            order_id = f"ZOM-{zomato_order_counter}"

            # Time slot weighting for Zomato Delivery:
            # Morning Rush (8-11:59): 20%
            # Afternoon Slump (12-15:59): 10% (LOW DELIVERY VOLUME - Underperforming!)
            # Evening Social (16-19:59): 45% (High delivery)
            # Night Chill (20-22:59): 25% (High delivery)
            slot_choice = random.choices(
                ["Morning Rush", "Afternoon Slump", "Evening Social", "Night Chill"],
                weights=[0.20, 0.10, 0.45, 0.25]
            )[0]

            if slot_choice == "Morning Rush":
                hour = random.randint(8, 11)
            elif slot_choice == "Afternoon Slump":
                hour = random.randint(12, 15)
            elif slot_choice == "Evening Social":
                hour = random.randint(16, 19)
            else:
                hour = random.randint(20, 22)

            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            order_dt = current_date.replace(hour=hour, minute=minute, second=second)
            order_timestamp_str = order_dt.strftime("%Y-%m-%d %H:%M:%S")

            # Status: 93% Completed, 7% Cancelled (Delivery has higher cancellations)
            is_cancelled = random.random() < 0.07
            status = "CANCELLED" if is_cancelled else "COMPLETED"

            # Number of items (1 to 4, higher avg items on delivery)
            num_items = random.choices([1, 2, 3, 4], weights=[0.35, 0.40, 0.20, 0.05])[0]

            # Zomato item pool: Note: Vanilla Cold Brew has LOW sales on Zomato right now
            if slot_choice == "Morning Rush":
                item_pool = ["COF-03", "COF-04", "COF-02", "BAK-01", "BAK-03"]
            elif slot_choice == "Afternoon Slump":
                # Currently very low Cold Brew visibility on Zomato
                item_pool = ["COF-02", "COF-03", "SPC-01", "BAK-01"]
            elif slot_choice == "Evening Social":
                item_pool = ["COF-03", "COF-06", "COF-08", "FOD-01", "FOD-02", "FOD-03", "BAK-01"]
            else:
                item_pool = ["SPC-03", "COF-06", "FOD-02", "BAK-03", "COF-08"]

            chosen_item_ids = random.choices(item_pool, k=num_items)

            order_gross = 0.0
            line_details = []
            for item_idx, it_id in enumerate(chosen_item_ids, 1):
                item_meta = item_lookup[it_id]
                qty = random.choices([1, 2], weights=[0.85, 0.15])[0]
                # Delivery menu prices are 10% higher to buffer commissions
                unit_price = round(item_meta["price"] * 1.10, 0)
                line_subtotal = qty * unit_price
                order_gross += line_subtotal
                line_details.append({
                    "item_seq": item_idx,
                    "item_id": it_id,
                    "item_name": item_meta["item_name"],
                    "category": item_meta["category"],
                    "qty": qty,
                    "unit_price": unit_price
                })

            # Zomato promo discount: Zomato Gold / promo code 15% off (35% probability)
            order_discount = 0.0
            if not is_cancelled and random.random() < 0.35:
                order_discount = round(min(100.0, order_gross * 0.15), 2)

            # Refunds on Zomato: Delivery leak or cold drink complaint (3% probability)
            refund_amount = 0.0
            if not is_cancelled and random.random() < 0.03:
                refund_amount = round(random.choice([150.0, 200.0, line_details[0]["unit_price"]]), 2)
                refund_amount = min(refund_amount, order_gross - order_discount)

            for line in line_details:
                zomato_rows.append({
                    "zomato_order_id": order_id,
                    "delivery_partner_id": f"DP-{random.randint(100, 999)}",
                    "order_timestamp": order_timestamp_str,
                    "item_seq": line["item_seq"],
                    "item_id": line["item_id"],
                    "item_name": line["item_name"],
                    "category": line["category"],
                    "quantity": line["qty"],
                    "unit_price": line["unit_price"],
                    "order_discount_amt": order_discount,
                    "order_refund_amt": refund_amount,
                    "order_status": status,
                    "delivery_rating": random.choice([4, 5, 5, 4, 3, 5]) if status == "COMPLETED" else ""
                })

    # 3. Inject Realistic Dirty Data / Anomalies

    # A. Exact duplicate rows in POS (terminal re-sync)
    dup_pos_indices = [15, 82, 190, 450, 780]
    for idx in dup_pos_indices:
        if idx < len(pos_rows):
            pos_rows.append(pos_rows[idx].copy())

    # B. Exact duplicate rows in Zomato (webhook retry)
    dup_zomato_indices = [25, 110, 310, 620]
    for idx in dup_zomato_indices:
        if idx < len(zomato_rows):
            zomato_rows.append(zomato_rows[idx].copy())

    # C. Corrupted / invalid timestamp (e.g. POS clock battery failure: '2026-99-99' or 'CORRUPTED')
    pos_rows.append({
        "pos_order_id": "POS-ERR-001",
        "terminal_id": "TERM-01",
        "order_timestamp": "2026-13-45 25:99:00", # invalid timestamp
        "item_seq": 1,
        "item_id": "COF-03",
        "item_name": "Velvet Cappuccino",
        "category": "Coffee",
        "quantity": 1,
        "unit_price": 230.0,
        "order_discount_amt": 0.0,
        "order_refund_amt": 0.0,
        "order_status": "COMPLETED",
        "payment_mode": "Card"
    })

    # D. Negative quantity error (clerical typo)
    pos_rows.append({
        "pos_order_id": "POS-ERR-002",
        "terminal_id": "TERM-02",
        "order_timestamp": "2026-09-15 10:15:00",
        "item_seq": 1,
        "item_id": "COF-01",
        "item_name": "Espresso Single Origin",
        "category": "Coffee",
        "quantity": -2, # Invalid negative quantity
        "unit_price": 160.0,
        "order_discount_amt": 0.0,
        "order_refund_amt": 0.0,
        "order_status": "COMPLETED",
        "payment_mode": "Cash"
    })

    # E. Negative unit price
    zomato_rows.append({
        "zomato_order_id": "ZOM-ERR-001",
        "delivery_partner_id": "DP-101",
        "order_timestamp": "2026-09-20 18:30:00",
        "item_seq": 1,
        "item_id": "COF-05",
        "item_name": "Vanilla Cold Brew",
        "category": "Coffee",
        "quantity": 1,
        "unit_price": -280.0, # Invalid negative unit price
        "order_discount_amt": 0.0,
        "order_refund_amt": 0.0,
        "order_status": "COMPLETED",
        "delivery_rating": 5
    })

    # F. Missing required item name & item_id
    zomato_rows.append({
        "zomato_order_id": "ZOM-ERR-002",
        "delivery_partner_id": "DP-102",
        "order_timestamp": "2026-10-05 14:20:00",
        "item_seq": 1,
        "item_id": "", # Missing item id
        "item_name": "", # Missing item name
        "category": "Unmapped",
        "quantity": 1,
        "unit_price": 250.0,
        "order_discount_amt": 0.0,
        "order_refund_amt": 0.0,
        "order_status": "COMPLETED",
        "delivery_rating": 4
    })

    # G. Ambiguous ID collision: A synthetic row in Zomato using POS order id prefix
    zomato_rows.append({
        "zomato_order_id": "POS-10025", # Colliding ID
        "delivery_partner_id": "DP-999",
        "order_timestamp": "2026-10-12 11:00:00",
        "item_seq": 1,
        "item_id": "COF-03",
        "item_name": "Velvet Cappuccino",
        "category": "Coffee",
        "quantity": 1,
        "unit_price": 250.0,
        "order_discount_amt": 0.0,
        "order_refund_amt": 0.0,
        "order_status": "COMPLETED",
        "delivery_rating": 5
    })

    # Write POS Raw CSV
    pos_fields = [
        "pos_order_id", "terminal_id", "order_timestamp", "item_seq",
        "item_id", "item_name", "category", "quantity", "unit_price",
        "order_discount_amt", "order_refund_amt", "order_status", "payment_mode"
    ]
    with open(pos_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=pos_fields)
        writer.writeheader()
        writer.writerows(pos_rows)

    # Write Zomato Raw CSV
    zomato_fields = [
        "zomato_order_id", "delivery_partner_id", "order_timestamp", "item_seq",
        "item_id", "item_name", "category", "quantity", "unit_price",
        "order_discount_amt", "order_refund_amt", "order_status", "delivery_rating"
    ]
    with open(zomato_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=zomato_fields)
        writer.writeheader()
        writer.writerows(zomato_rows)

    print(f"Data generation complete!")
    print(f"Generated {len(pos_rows)} raw POS records -> {pos_file}")
    print(f"Generated {len(zomato_rows)} raw Zomato records -> {zomato_file}")

if __name__ == "__main__":
    generate_data()
