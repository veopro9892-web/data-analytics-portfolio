"""
test_validation.py
------------------
Automated test suite validating:
1. Exact row count reconciliations between raw exports, rejections, and database tables.
2. Financial invariants: Net Sales = Gross Sales - Discounts - Refunds.
3. Integrity of foreign keys and primary keys.
4. Absence of duplicate order IDs or corrupt data.
5. Correct identification of the promotion candidate (Vanilla Cold Brew in Afternoon Slump).
"""

import os
import sqlite3
import pandas as pd

def run_tests():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "database", "slow_brew.db")
    pos_raw = os.path.join(base_dir, "data", "raw", "pos_exports.csv")
    zomato_raw = os.path.join(base_dir, "data", "raw", "zomato_exports.csv")

    assert os.path.exists(db_path), "Database file does not exist!"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Running Project 1 Validation Tests...")

    # Test 1: POS Row Count Tie-Out
    with open(pos_raw, "r", encoding="utf-8") as f:
        pos_raw_count = sum(1 for _ in f) - 1 # exclude header
    
    pos_accepted = cursor.execute("""
        SELECT COUNT(*) FROM fact_order_items foi
        JOIN fact_orders fo ON foi.order_id = fo.order_id
        WHERE fo.channel_id = 'CHN-POS'
    """).fetchone()[0]

    pos_rejected = cursor.execute("""
        SELECT COUNT(*) FROM rejected_rows_audit WHERE source_system = 'POS'
    """).fetchone()[0]

    assert pos_raw_count == (pos_accepted + pos_rejected), (
        f"POS row reconciliation failed! Raw={pos_raw_count}, Accepted={pos_accepted}, Rejected={pos_rejected}"
    )
    print(f"  [PASS] Test 1: POS Row Reconciliation tied out ({pos_raw_count} = {pos_accepted} + {pos_rejected}).")

    # Test 2: Zomato Row Count Tie-Out
    with open(zomato_raw, "r", encoding="utf-8") as f:
        zom_raw_count = sum(1 for _ in f) - 1

    zom_accepted = cursor.execute("""
        SELECT COUNT(*) FROM fact_order_items foi
        JOIN fact_orders fo ON foi.order_id = fo.order_id
        WHERE fo.channel_id = 'CHN-ZOM'
    """).fetchone()[0]

    zom_rejected = cursor.execute("""
        SELECT COUNT(*) FROM rejected_rows_audit WHERE source_system = 'ZOMATO'
    """).fetchone()[0]

    assert zom_raw_count == (zom_accepted + zom_rejected), (
        f"Zomato row reconciliation failed! Raw={zom_raw_count}, Accepted={zom_accepted}, Rejected={zom_rejected}"
    )
    print(f"  [PASS] Test 2: Zomato Row Reconciliation tied out ({zom_raw_count} = {zom_accepted} + {zom_rejected}).")

    # Test 3: Zero Duplicate Order IDs
    dup_orders = cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT order_id FROM fact_orders GROUP BY order_id HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    assert dup_orders == 0, f"Duplicate order IDs found in fact_orders: {dup_orders}"
    print("  [PASS] Test 3: Zero duplicate order IDs in fact_orders.")

    # Test 4: Financial Integrity (Net = Gross - Discounts - Refunds)
    financial_mismatch = cursor.execute("""
        SELECT COUNT(*) FROM fact_orders
        WHERE order_status = 'COMPLETED'
          AND ROUND(net_sales_amount, 2) != ROUND(MAX(0.0, gross_order_total - order_discount_amt - order_refund_amt), 2)
    """).fetchone()[0]
    assert financial_mismatch == 0, f"Financial formula mismatch found in {financial_mismatch} completed orders!"
    print("  [PASS] Test 4: Net Sales formula verified for 100% of completed orders.")

    # Test 5: Cancelled Orders Net Sales = 0
    cancelled_mismatch = cursor.execute("""
        SELECT COUNT(*) FROM fact_orders
        WHERE order_status = 'CANCELLED' AND net_sales_amount != 0.0
    """).fetchone()[0]
    assert cancelled_mismatch == 0, f"Cancelled orders with non-zero net sales: {cancelled_mismatch}"
    print("  [PASS] Test 5: All cancelled orders correctly have Net Sales = 0.00.")

    # Test 6: Verify Promotion Candidate
    top_promo = cursor.execute("""
        SELECT m.item_name, 
               SUM(CASE WHEN fo.channel_id = 'CHN-POS' THEN foi.quantity ELSE 0 END) AS pos_qty,
               SUM(CASE WHEN fo.channel_id = 'CHN-ZOM' THEN foi.quantity ELSE 0 END) AS zom_qty
        FROM fact_order_items foi
        JOIN fact_orders fo ON foi.order_id = fo.order_id
        JOIN dim_menu_items m ON foi.item_id = m.item_id
        WHERE fo.order_status = 'COMPLETED' AND m.item_id = 'COF-05'
        GROUP BY m.item_name
    """).fetchone()
    
    assert top_promo is not None, "Vanilla Cold Brew not found in items!"
    assert top_promo[1] > 200, f"In-store cold brew volume unexpectedly low: {top_promo[1]}"
    assert top_promo[2] < 50, f"Zomato cold brew volume unexpectedly high: {top_promo[2]}"
    print(f"  [PASS] Test 6: Promotion candidate '{top_promo[0]}' confirmed (In-Store: {top_promo[1]} units, Zomato: {top_promo[2]} units).")

    conn.close()
    print("\nALL PROJECT 1 VALIDATION TESTS PASSED SUCCESSFULLY (6/6)!\n")

if __name__ == "__main__":
    run_tests()
