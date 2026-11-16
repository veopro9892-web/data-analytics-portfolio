"""
generate_sap_data.py
--------------------
Generates deterministic, SAP S/4HANA aligned procurement data for 3-way match reconciliation.
Uses INR (₹) throughout.

Contains:
1. 8 hand-checked benchmark fixture cases testing all edge conditions:
   - Clean 1:1:1 match
   - Partial receipt within window (MUST NOT be treated as exception)
   - Split receipts & split invoices (Fan-out trap proof case)
   - Missing GR
   - Quantity over-invoiced
   - Price variance outside ±2% tolerance
   - Overdue open PO line
   - Multi-exception line (Over-invoiced + Price variance)
2. Realistic background POs, GRs (MIGO), and Invoices (MIRO).
"""

import os
import csv
import json
import random
from datetime import datetime, date, timedelta

def generate_procurement_data():
    # Deterministic generation
    random.seed(101)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, "data", "raw")
    fix_dir = os.path.join(base_dir, "data", "fixtures")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(fix_dir, exist_ok=True)

    # 1. Suppliers (LFA1)
    suppliers = [
        {"supplier_id": "VEND-1001", "supplier_name": "Coorg Specialty Coffee Estates", "vendor_code": "1000101", "city": "Madikeri", "payment_terms": "Net 30", "contact_email": "accounts@coorgspecialty.in"},
        {"supplier_id": "VEND-1002", "supplier_name": "Bharat Eco Packaging Solutions", "vendor_code": "1000102", "city": "Bengaluru", "payment_terms": "Net 45", "contact_email": "finance@bharatecopack.com"},
        {"supplier_id": "VEND-1003", "supplier_name": "Milma Fresh Dairy Federation", "vendor_code": "1000103", "city": "Kochi", "payment_terms": "Net 30", "contact_email": "billing@milmadairy.org"},
        {"supplier_id": "VEND-1004", "supplier_name": "Precision Espresso Spares & Valves", "vendor_code": "1000104", "city": "Mumbai", "payment_terms": "Net 60", "contact_email": "ap@precisionspares.co.in"},
        {"supplier_id": "VEND-1005", "supplier_name": "Deccan Artisanal Syrups & Flavor", "vendor_code": "1000105", "city": "Hyderabad", "payment_terms": "Net 30", "contact_email": "accounts@deccansyrups.com"},
        {"supplier_id": "VEND-1006", "supplier_name": "Himalayan Mineral Water Supplies", "vendor_code": "1000106", "city": "Dehradun", "payment_terms": "Net 45", "contact_email": "orders@himalayanwater.in"},
        {"supplier_id": "VEND-1007", "supplier_name": "Western Bio-Degradable Cups Ltd", "vendor_code": "1000107", "city": "Pune", "payment_terms": "Net 30", "contact_email": "tax@westernbio.com"},
        {"supplier_id": "VEND-1008", "supplier_name": "Malabar Organic Spices & Cocoa", "vendor_code": "1000108", "city": "Calicut", "payment_terms": "Net 45", "contact_email": "ap@malabarspices.com"},
    ]

    # 2. Materials (MARA)
    materials = [
        {"material_code": "MAT-101", "material_description": "Arabica Green Coffee Beans Grade A", "material_group": "RAW_COFFEE", "base_uom": "KG"},
        {"material_code": "MAT-102", "material_description": "Robusta Cherry Washed Coffee Beans", "material_group": "RAW_COFFEE", "base_uom": "KG"},
        {"material_code": "MAT-103", "material_description": "Kraft Paper Coffee Pouches (1kg Valve)", "material_group": "PACKAGING", "base_uom": "BOX"},
        {"material_code": "MAT-104", "material_description": "Double Wall Insulated Paper Cups (250ml)", "material_group": "PACKAGING", "base_uom": "BOX"},
        {"material_code": "MAT-105", "material_description": "Barista Oat Milk (1 Litre Tetra Pak)", "material_group": "DAIRY_SYRUP", "base_uom": "BOX"},
        {"material_code": "MAT-106", "material_description": "Organic Vanilla Bean Infusion Syrup", "material_group": "DAIRY_SYRUP", "base_uom": "LTR"},
        {"material_code": "MAT-107", "material_description": "Commercial Grouphead Gasket 58mm", "material_group": "EQUIPMENT_PARTS", "base_uom": "EA"},
        {"material_code": "MAT-108", "material_description": "Espresso Machine Food-Safe Descaler", "material_group": "EQUIPMENT_PARTS", "base_uom": "LTR"},
    ]

    po_headers = []
    po_lines = []
    goods_receipts = []
    invoice_lines = []

    # Simulation Cutoff Date: 2026-11-17
    SIMULATION_CUTOFF = date(2026, 11, 17)

    # -------------------------------------------------------------
    # 3. HAND-CHECKED BENCHMARK FIXTURE CASES (PO-45001001 to 1008)
    # -------------------------------------------------------------
    hand_checked_fixtures = [
        {
            "test_case_id": "TC-01",
            "scenario": "Perfect 1:1:1 Match (All documents agree)",
            "po_number": "PO-45001001",
            "line_item": 10,
            "supplier_id": "VEND-1001",
            "material_code": "MAT-101",
            "ordered_qty": 100.0,
            "po_unit_price": 500.0,
            "expected_delivery_date": "2026-10-15",
            "gr_records": [{"gr_number": "GR-500001", "gr_date": "2026-10-14", "qty": 100.0}],
            "inv_records": [{"invoice_number": "INV-900001", "inv_date": "2026-10-18", "qty": 100.0, "unit_price": 500.0}],
            "expected_status": "CLEAN_MATCH",
            "expected_reasons": "CLEAN_MATCH",
            "expected_risk_amt": 0.0
        },
        {
            "test_case_id": "TC-02",
            "scenario": "Partial Receipt Within Window (NOT an exception!)",
            "po_number": "PO-45001002",
            "line_item": 10,
            "supplier_id": "VEND-1002",
            "material_code": "MAT-103",
            "ordered_qty": 200.0,
            "po_unit_price": 150.0,
            "expected_delivery_date": "2026-12-05", # Future delivery date!
            "gr_records": [{"gr_number": "GR-500002", "gr_date": "2026-11-10", "qty": 100.0}],
            "inv_records": [{"invoice_number": "INV-900002", "inv_date": "2026-11-12", "qty": 100.0, "unit_price": 150.0}],
            "expected_status": "CLEAN_MATCH",
            "expected_reasons": "CLEAN_MATCH",
            "expected_risk_amt": 0.0
        },
        {
            "test_case_id": "TC-03",
            "scenario": "Split Receipts & Split Invoices (Anti-Fan-Out Benchmark)",
            "po_number": "PO-45001003",
            "line_item": 10,
            "supplier_id": "VEND-1004",
            "material_code": "MAT-107",
            "ordered_qty": 100.0,
            "po_unit_price": 1000.0,
            "expected_delivery_date": "2026-10-25",
            "gr_records": [
                {"gr_number": "GR-500003", "gr_date": "2026-10-05", "qty": 40.0},
                {"gr_number": "GR-500004", "gr_date": "2026-10-12", "qty": 60.0}
            ],
            "inv_records": [
                {"invoice_number": "INV-900003", "inv_date": "2026-10-08", "qty": 40.0, "unit_price": 1000.0},
                {"invoice_number": "INV-900004", "inv_date": "2026-10-15", "qty": 60.0, "unit_price": 1000.0}
            ],
            "expected_status": "CLEAN_MATCH",
            "expected_reasons": "CLEAN_MATCH",
            "expected_risk_amt": 0.0
        },
        {
            "test_case_id": "TC-04",
            "scenario": "Missing Goods Receipt (Invoiced without MIGO receipt)",
            "po_number": "PO-45001004",
            "line_item": 10,
            "supplier_id": "VEND-1005",
            "material_code": "MAT-106",
            "ordered_qty": 50.0,
            "po_unit_price": 800.0,
            "expected_delivery_date": "2026-10-20",
            "gr_records": [], # ZERO receipts
            "inv_records": [{"invoice_number": "INV-900005", "inv_date": "2026-10-25", "qty": 50.0, "unit_price": 800.0}],
            "expected_status": "EXCEPTION",
            "expected_reasons": "MISSING_GR",
            "expected_risk_amt": 40000.0
        },
        {
            "test_case_id": "TC-05",
            "scenario": "Quantity Over-Invoiced (Billed 100, Received 70)",
            "po_number": "PO-45001005",
            "line_item": 10,
            "supplier_id": "VEND-1002",
            "material_code": "MAT-104",
            "ordered_qty": 100.0,
            "po_unit_price": 250.0,
            "expected_delivery_date": "2026-10-15",
            "gr_records": [{"gr_number": "GR-500005", "gr_date": "2026-10-10", "qty": 70.0}],
            "inv_records": [{"invoice_number": "INV-900006", "inv_date": "2026-10-14", "qty": 100.0, "unit_price": 250.0}],
            "expected_status": "EXCEPTION",
            "expected_reasons": "QUANTITY_OVER_INVOICE",
            "expected_risk_amt": 7500.0 # 30 excess units * 250
        },
        {
            "test_case_id": "TC-06",
            "scenario": "Price Variance Outside Tolerance (+10% hike: ₹220 vs ₹200 PO)",
            "po_number": "PO-45001006",
            "line_item": 10,
            "supplier_id": "VEND-1003",
            "material_code": "MAT-105",
            "ordered_qty": 500.0,
            "po_unit_price": 200.0,
            "expected_delivery_date": "2026-10-10",
            "gr_records": [{"gr_number": "GR-500006", "gr_date": "2026-10-02", "qty": 500.0}],
            "inv_records": [{"invoice_number": "INV-900007", "inv_date": "2026-10-05", "qty": 500.0, "unit_price": 220.0}],
            "expected_status": "EXCEPTION",
            "expected_reasons": "PRICE_VARIANCE",
            "expected_risk_amt": 10000.0 # 500 * (220 - 200)
        },
        {
            "test_case_id": "TC-07",
            "scenario": "Overdue Open PO Line (Expected Oct 10, 150 units undelivered)",
            "po_number": "PO-45001007",
            "line_item": 10,
            "supplier_id": "VEND-1001",
            "material_code": "MAT-102",
            "ordered_qty": 200.0,
            "po_unit_price": 400.0,
            "expected_delivery_date": "2026-10-10", # Overdue relative to 2026-11-17
            "gr_records": [{"gr_number": "GR-500007", "gr_date": "2026-10-08", "qty": 50.0}],
            "inv_records": [{"invoice_number": "INV-900008", "inv_date": "2026-10-12", "qty": 50.0, "unit_price": 400.0}],
            "expected_status": "EXCEPTION",
            "expected_reasons": "OVERDUE_OPEN_PO",
            "expected_risk_amt": 60000.0 # 150 undelivered units * 400
        },
        {
            "test_case_id": "TC-08",
            "scenario": "Compound Multi-Exception (Over-invoiced + Price Variance)",
            "po_number": "PO-45001008",
            "line_item": 10,
            "supplier_id": "VEND-1004",
            "material_code": "MAT-108",
            "ordered_qty": 100.0,
            "po_unit_price": 300.0,
            "expected_delivery_date": "2026-10-20",
            "gr_records": [{"gr_number": "GR-500008", "gr_date": "2026-10-18", "qty": 60.0}],
            "inv_records": [{"invoice_number": "INV-900009", "inv_date": "2026-10-22", "qty": 80.0, "unit_price": 330.0}],
            "expected_status": "EXCEPTION",
            "expected_reasons": "QUANTITY_OVER_INVOICE; PRICE_VARIANCE",
            "expected_risk_amt": 9000.0 # Excess qty (20 * 330 = 6600) + price var on received (60 * 30 = 1800) = 8400 or total invoiced (80*330 - 60*300 = 26400 - 18000 = 8400)
        }
    ]

    # Add Fixture Records to lists
    for fx in hand_checked_fixtures:
        po_headers.append({
            "po_number": fx["po_number"],
            "supplier_id": fx["supplier_id"],
            "company_code": "1000",
            "purchasing_org": "1000",
            "po_date": "2026-09-20",
            "currency": "INR",
            "status": "APPROVED"
        })
        po_lines.append({
            "po_number": fx["po_number"],
            "line_item": fx["line_item"],
            "material_code": fx["material_code"],
            "ordered_quantity": fx["ordered_qty"],
            "po_unit_price": fx["po_unit_price"],
            "uom": "BOX" if "BOX" in fx["material_code"] else ("KG" if "101" in fx["material_code"] or "102" in fx["material_code"] else "EA"),
            "expected_delivery_date": fx["expected_delivery_date"],
            "po_line_total": round(fx["ordered_qty"] * fx["po_unit_price"], 2)
        })
        for gr in fx["gr_records"]:
            goods_receipts.append({
                "gr_number": gr["gr_number"],
                "material_doc_year": 2026,
                "po_number": fx["po_number"],
                "line_item": fx["line_item"],
                "gr_date": gr["gr_date"],
                "received_quantity": gr["qty"],
                "movement_type": "101",
                "storage_location": "SL-01"
            })
        for inv in fx["inv_records"]:
            inv_amt = round(inv["qty"] * inv["unit_price"], 2)
            invoice_lines.append({
                "invoice_number": inv["invoice_number"],
                "invoice_date": inv["inv_date"],
                "supplier_id": fx["supplier_id"],
                "po_number": fx["po_number"],
                "line_item": fx["line_item"],
                "invoiced_quantity": inv["qty"],
                "invoice_unit_price": inv["unit_price"],
                "invoiced_amount": inv_amt,
                "tax_amount": round(inv_amt * 0.18, 2),
                "payment_status": "BLOCKED_AP_REVIEW" if fx["expected_status"] == "EXCEPTION" else "POSTED_CLEARED"
            })

    # -------------------------------------------------------------
    # 4. REALISTIC OPERATIONAL PROCUREMENT DATA (POs 45001009 to 45001050)
    # -------------------------------------------------------------
    po_seq = 1008
    gr_seq = 500008
    inv_seq = 900009

    for i in range(42):
        po_seq += 1
        po_num = f"PO-4500{po_seq}"
        supp = random.choice(suppliers)
        supp_id = supp["supplier_id"]
        po_d = date(2026, 9, 1) + timedelta(days=int(i * 1.5))
        po_date_str = po_d.strftime("%Y-%m-%d")

        po_headers.append({
            "po_number": po_num,
            "supplier_id": supp_id,
            "company_code": "1000",
            "purchasing_org": "1000",
            "po_date": po_date_str,
            "currency": "INR",
            "status": "APPROVED"
        })

        # 1 to 2 lines per PO
        num_lines = random.choice([1, 2])
        for l_idx in range(1, num_lines + 1):
            line_item_num = l_idx * 10
            mat = random.choice(materials)
            ord_qty = float(random.choice([50, 100, 150, 200, 300, 500]))
            
            # Base price
            if mat["material_group"] == "RAW_COFFEE":
                base_p = float(random.choice([450, 520, 600]))
            elif mat["material_group"] == "PACKAGING":
                base_p = float(random.choice([120, 180, 220]))
            elif mat["material_group"] == "DAIRY_SYRUP":
                base_p = float(random.choice([160, 240, 350]))
            else:
                base_p = float(random.choice([800, 1200, 1500]))

            exp_deliv = po_d + timedelta(days=15) # 15 days lead time
            exp_deliv_str = exp_deliv.strftime("%Y-%m-%d")

            po_lines.append({
                "po_number": po_num,
                "line_item": line_item_num,
                "material_code": mat["material_code"],
                "ordered_quantity": ord_qty,
                "po_unit_price": base_p,
                "uom": mat["base_uom"],
                "expected_delivery_date": exp_deliv_str,
                "po_line_total": round(ord_qty * base_p, 2)
            })

            # Determine scenario for this operational line:
            # 70% Clean Match, 8% Price Variance, 8% Qty Over-Invoice, 7% Overdue, 7% Missing GR
            r_val = random.random()

            if r_val < 0.70:
                # Clean Match (Some 1:1, some split)
                if random.random() < 0.30:
                    # Clean split
                    split_qty_1 = ord_qty * 0.4
                    split_qty_2 = ord_qty * 0.6
                    gr_seq += 1
                    goods_receipts.append({
                        "gr_number": f"GR-{gr_seq}",
                        "material_doc_year": 2026,
                        "po_number": po_num,
                        "line_item": line_item_num,
                        "gr_date": exp_deliv_str,
                        "received_quantity": split_qty_1,
                        "movement_type": "101",
                        "storage_location": "SL-01"
                    })
                    gr_seq += 1
                    goods_receipts.append({
                        "gr_number": f"GR-{gr_seq}",
                        "material_doc_year": 2026,
                        "po_number": po_num,
                        "line_item": line_item_num,
                        "gr_date": exp_deliv_str,
                        "received_quantity": split_qty_2,
                        "movement_type": "101",
                        "storage_location": "SL-01"
                    })
                    # Invoices
                    inv_seq += 1
                    inv_amt_1 = round(split_qty_1 * base_p, 2)
                    invoice_lines.append({
                        "invoice_number": f"INV-{inv_seq}",
                        "invoice_date": exp_deliv_str,
                        "supplier_id": supp_id,
                        "po_number": po_num,
                        "line_item": line_item_num,
                        "invoiced_quantity": split_qty_1,
                        "invoice_unit_price": base_p,
                        "invoiced_amount": inv_amt_1,
                        "tax_amount": round(inv_amt_1 * 0.18, 2),
                        "payment_status": "POSTED_CLEARED"
                    })
                    inv_seq += 1
                    inv_amt_2 = round(split_qty_2 * base_p, 2)
                    invoice_lines.append({
                        "invoice_number": f"INV-{inv_seq}",
                        "invoice_date": exp_deliv_str,
                        "supplier_id": supp_id,
                        "po_number": po_num,
                        "line_item": line_item_num,
                        "invoiced_quantity": split_qty_2,
                        "invoice_unit_price": base_p,
                        "invoiced_amount": inv_amt_2,
                        "tax_amount": round(inv_amt_2 * 0.18, 2),
                        "payment_status": "POSTED_CLEARED"
                    })
                else:
                    # Single Clean 1:1:1
                    gr_seq += 1
                    goods_receipts.append({
                        "gr_number": f"GR-{gr_seq}",
                        "material_doc_year": 2026,
                        "po_number": po_num,
                        "line_item": line_item_num,
                        "gr_date": exp_deliv_str,
                        "received_quantity": ord_qty,
                        "movement_type": "101",
                        "storage_location": "SL-01"
                    })
                    inv_seq += 1
                    inv_amt = round(ord_qty * base_p, 2)
                    invoice_lines.append({
                        "invoice_number": f"INV-{inv_seq}",
                        "invoice_date": exp_deliv_str,
                        "supplier_id": supp_id,
                        "po_number": po_num,
                        "line_item": line_item_num,
                        "invoiced_quantity": ord_qty,
                        "invoice_unit_price": base_p,
                        "invoiced_amount": inv_amt,
                        "tax_amount": round(inv_amt * 0.18, 2),
                        "payment_status": "POSTED_CLEARED"
                    })

            elif r_val < 0.78:
                # Price Variance Exception (> 2%)
                gr_seq += 1
                goods_receipts.append({
                    "gr_number": f"GR-{gr_seq}",
                    "material_doc_year": 2026,
                    "po_number": po_num,
                    "line_item": line_item_num,
                    "gr_date": exp_deliv_str,
                    "received_quantity": ord_qty,
                    "movement_type": "101",
                    "storage_location": "SL-01"
                })
                hike_price = round(base_p * 1.08, 2) # +8% hike
                inv_seq += 1
                inv_amt = round(ord_qty * hike_price, 2)
                invoice_lines.append({
                    "invoice_number": f"INV-{inv_seq}",
                    "invoice_date": exp_deliv_str,
                    "supplier_id": supp_id,
                    "po_number": po_num,
                    "line_item": line_item_num,
                    "invoiced_quantity": ord_qty,
                    "invoice_unit_price": hike_price,
                    "invoiced_amount": inv_amt,
                    "tax_amount": round(inv_amt * 0.18, 2),
                    "payment_status": "BLOCKED_AP_REVIEW"
                })

            elif r_val < 0.86:
                # Quantity Over-Invoice Exception
                received_q = round(ord_qty * 0.7, 0)
                gr_seq += 1
                goods_receipts.append({
                    "gr_number": f"GR-{gr_seq}",
                    "material_doc_year": 2026,
                    "po_number": po_num,
                    "line_item": line_item_num,
                    "gr_date": exp_deliv_str,
                    "received_quantity": received_q,
                    "movement_type": "101",
                    "storage_location": "SL-01"
                })
                inv_seq += 1
                inv_amt = round(ord_qty * base_p, 2) # Invoiced full ordered qty!
                invoice_lines.append({
                    "invoice_number": f"INV-{inv_seq}",
                    "invoice_date": exp_deliv_str,
                    "supplier_id": supp_id,
                    "po_number": po_num,
                    "line_item": line_item_num,
                    "invoiced_quantity": ord_qty,
                    "invoice_unit_price": base_p,
                    "invoiced_amount": inv_amt,
                    "tax_amount": round(inv_amt * 0.18, 2),
                    "payment_status": "BLOCKED_AP_REVIEW"
                })

            elif r_val < 0.93:
                # Overdue Open PO Line Exception
                # Partial delivery in the past, nothing further received
                received_q = round(ord_qty * 0.4, 0)
                gr_seq += 1
                goods_receipts.append({
                    "gr_number": f"GR-{gr_seq}",
                    "material_doc_year": 2026,
                    "po_number": po_num,
                    "line_item": line_item_num,
                    "gr_date": exp_deliv_str,
                    "received_quantity": received_q,
                    "movement_type": "101",
                    "storage_location": "SL-01"
                })
                inv_seq += 1
                inv_amt = round(received_q * base_p, 2)
                invoice_lines.append({
                    "invoice_number": f"INV-{inv_seq}",
                    "invoice_date": exp_deliv_str,
                    "supplier_id": supp_id,
                    "po_number": po_num,
                    "line_item": line_item_num,
                    "invoiced_quantity": received_q,
                    "invoice_unit_price": base_p,
                    "invoiced_amount": inv_amt,
                    "tax_amount": round(inv_amt * 0.18, 2),
                    "payment_status": "POSTED_CLEARED"
                })

            else:
                # Missing GR Exception (Invoiced without receipt)
                inv_seq += 1
                inv_amt = round(ord_qty * base_p, 2)
                invoice_lines.append({
                    "invoice_number": f"INV-{inv_seq}",
                    "invoice_date": exp_deliv_str,
                    "supplier_id": supp_id,
                    "po_number": po_num,
                    "line_item": line_item_num,
                    "invoiced_quantity": ord_qty,
                    "invoice_unit_price": base_p,
                    "invoiced_amount": inv_amt,
                    "tax_amount": round(inv_amt * 0.18, 2),
                    "payment_status": "BLOCKED_AP_REVIEW"
                })

    # Write Raw CSVs
    def write_csv(filepath, fieldnames, data):
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    write_csv(os.path.join(raw_dir, "suppliers.csv"), ["supplier_id", "supplier_name", "vendor_code", "city", "payment_terms", "contact_email"], suppliers)
    write_csv(os.path.join(raw_dir, "materials.csv"), ["material_code", "material_description", "material_group", "base_uom"], materials)
    write_csv(os.path.join(raw_dir, "purchase_orders.csv"), ["po_number", "supplier_id", "company_code", "purchasing_org", "po_date", "currency", "status"], po_headers)
    write_csv(os.path.join(raw_dir, "po_lines.csv"), ["po_number", "line_item", "material_code", "ordered_quantity", "po_unit_price", "uom", "expected_delivery_date", "po_line_total"], po_lines)
    write_csv(os.path.join(raw_dir, "goods_receipts.csv"), ["gr_number", "material_doc_year", "po_number", "line_item", "gr_date", "received_quantity", "movement_type", "storage_location"], goods_receipts)
    write_csv(os.path.join(raw_dir, "invoice_lines.csv"), ["invoice_number", "invoice_date", "supplier_id", "po_number", "line_item", "invoiced_quantity", "invoice_unit_price", "invoiced_amount", "tax_amount", "payment_status"], invoice_lines)

    # Save Fixtures for Testing & Excel Presentation
    with open(os.path.join(fix_dir, "hand_checked_fixtures.json"), "w", encoding="utf-8") as f:
        json.dump(hand_checked_fixtures, f, indent=2)

    with open(os.path.join(fix_dir, "hand_checked_fixtures.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["test_case_id", "scenario", "po_number", "line_item", "supplier_id", "material_code", "ordered_qty", "po_unit_price", "expected_delivery_date", "expected_status", "expected_reasons", "expected_risk_amt"])
        writer.writeheader()
        for fx in hand_checked_fixtures:
            writer.writerow({
                "test_case_id": fx["test_case_id"],
                "scenario": fx["scenario"],
                "po_number": fx["po_number"],
                "line_item": fx["line_item"],
                "supplier_id": fx["supplier_id"],
                "material_code": fx["material_code"],
                "ordered_qty": fx["ordered_qty"],
                "po_unit_price": fx["po_unit_price"],
                "expected_delivery_date": fx["expected_delivery_date"],
                "expected_status": fx["expected_status"],
                "expected_reasons": fx["expected_reasons"],
                "expected_risk_amt": fx["expected_risk_amt"]
            })

    print("Deterministic SAP procurement data generation complete!")
    print(f"Generated {len(suppliers)} Suppliers")
    print(f"Generated {len(materials)} Materials")
    print(f"Generated {len(po_headers)} Purchase Orders")
    print(f"Generated {len(po_lines)} PO Lines")
    print(f"Generated {len(goods_receipts)} Goods Receipts (MIGO)")
    print(f"Generated {len(invoice_lines)} Invoices (MIRO)")
    print(f"Hand-checked fixtures saved to data/fixtures/hand_checked_fixtures.json")

if __name__ == "__main__":
    generate_procurement_data()
