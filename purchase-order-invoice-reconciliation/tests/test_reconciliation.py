"""
test_reconciliation.py
----------------------
Automated test suite validating:
1. Complete accuracy against the 8 hand-checked benchmark fixtures.
2. Verification that partial receipt within window is NOT an exception.
3. Proof that Cartesian join fan-out is completely prevented on split receipts/invoices.
4. 1-to-1 PO-line reconciliation count (no row inflation).
5. Accurate detection of compound multi-exception lines.
"""

import os
import json
import sqlite3
import pandas as pd

def run_tests():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "database", "sap_procurement.db")
    fix_path = os.path.join(base_dir, "data", "fixtures", "hand_checked_fixtures.json")

    assert os.path.exists(db_path), "Database file does not exist!"
    assert os.path.exists(fix_path), "Fixtures file does not exist!"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Running Project 2 Reconciliation Validation Tests...")

    # Load fixtures
    with open(fix_path, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    # Test 1: Validate 8 Hand-Checked Benchmark Fixtures
    for fx in fixtures:
        tc_id = fx["test_case_id"]
        po_num = fx["po_number"]
        line_num = fx["line_item"]
        expected_status = fx["expected_status"]
        expected_reasons = fx["expected_reasons"]

        row = cursor.execute("""
            SELECT match_status, primary_exception_reason, exception_reasons, amount_at_risk_inr
            FROM rpt_3way_match_exceptions
            WHERE po_number = ? AND line_item = ?
        """, (po_num, line_num)).fetchone()

        assert row is not None, f"Fixture {tc_id} ({po_num}) not found in reconciliation table!"
        actual_status, actual_primary, actual_reasons, actual_risk = row

        assert actual_status == expected_status, (
            f"Fixture {tc_id} status mismatch! Expected {expected_status}, got {actual_status}"
        )

        if expected_status == "CLEAN_MATCH":
            assert actual_status == "CLEAN_MATCH", f"Fixture {tc_id} should be clean match!"
            print(f"  [PASS] Test Case {tc_id}: '{fx['scenario']}' verified as CLEAN_MATCH.")
        else:
            # Check reasons
            for r in expected_reasons.split("; "):
                assert r in actual_reasons, f"Fixture {tc_id} missing expected reason '{r}' in '{actual_reasons}'"
            print(f"  [PASS] Test Case {tc_id}: '{fx['scenario']}' verified with reasons '{actual_reasons}'.")

    # Test 2: Crucial Business Rule Test — Partial Receipt Within Delivery Window
    # TC-02 has expected delivery date 2026-12-05 (in future relative to 2026-11-17)
    tc2 = cursor.execute("""
        SELECT match_status, received_quantity, ordered_quantity, expected_delivery_date
        FROM rpt_3way_match_exceptions
        WHERE po_number = 'PO-45001002' AND line_item = 10
    """).fetchone()
    assert tc2[0] == "CLEAN_MATCH", f"Partial delivery within window was incorrectly flagged: {tc2}"
    assert tc2[1] < tc2[2], "Test condition invalid: should be partial receipt"
    print("  [PASS] Business Rule Verified: Partial receipt within open delivery window is NOT an exception.")

    # Test 3: Mathematical Proof of Fan-Out Trap Prevention
    # Run naive join vs independent aggregation on PO-45001003
    naive_join_res = cursor.execute("""
        SELECT COUNT(*), SUM(gr.received_quantity), SUM(inv.invoiced_amount)
        FROM fact_po_lines pol
        JOIN fact_goods_receipts gr ON pol.po_number = gr.po_number AND pol.line_item = gr.line_item
        JOIN fact_invoice_lines inv ON pol.po_number = inv.po_number AND pol.line_item = inv.line_item
        WHERE pol.po_number = 'PO-45001003'
    """).fetchone()

    correct_res = cursor.execute("""
        SELECT COUNT(*), received_quantity, invoiced_amount
        FROM rpt_3way_match_exceptions
        WHERE po_number = 'PO-45001003'
    """).fetchone()

    assert naive_join_res[0] == 4, f"Naive join expected 4 rows (2x2 Cartesian), got {naive_join_res[0]}"
    assert naive_join_res[1] == 200.0, f"Naive join expected 200 inflated qty, got {naive_join_res[1]}"
    assert naive_join_res[2] == 200000.0, f"Naive join expected ₹200,000 inflated amount, got {naive_join_res[2]}"

    assert correct_res[0] == 1, f"Correct query should yield 1 row, got {correct_res[0]}"
    assert correct_res[1] == 100.0, f"Correct received qty should be 100, got {correct_res[1]}"
    assert correct_res[2] == 100000.0, f"Correct invoiced amount should be ₹100,000, got {correct_res[2]}"
    print("  [PASS] Anti-Fan-Out Verified: Naive raw join artificially doubles totals (4 rows, ₹200k), whereas independent aggregation yields exact 1 row and ₹100k.")

    # Test 4: 1-to-1 PO Line Integrity (No row inflation across entire dataset)
    total_po_lines = cursor.execute("SELECT COUNT(*) FROM fact_po_lines").fetchone()[0]
    total_recon_lines = cursor.execute("SELECT COUNT(*) FROM rpt_3way_match_exceptions").fetchone()[0]
    assert total_po_lines == total_recon_lines, (
        f"Row count mismatch! fact_po_lines={total_po_lines}, rpt_3way_match_exceptions={total_recon_lines}"
    )
    print(f"  [PASS] Line Count Integrity: Exactly {total_po_lines} PO lines in both base and reconciliation tables.")

    # Test 5: Compound Multi-Exception Line Verified (No row duplication)
    tc8_count = cursor.execute("SELECT COUNT(*) FROM rpt_3way_match_exceptions WHERE po_number = 'PO-45001008'").fetchone()[0]
    assert tc8_count == 1, f"Multi-exception line was inflated to {tc8_count} rows!"
    print("  [PASS] Multi-Reason Integrity: Compound exception line evaluated without inflating line count (1 row).")

    conn.close()
    print("\nALL PROJECT 2 RECONCILIATION TESTS PASSED SUCCESSFULLY (5/5)!\n")

if __name__ == "__main__":
    run_tests()
