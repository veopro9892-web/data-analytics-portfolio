"""
export_powerbi_tables.py
------------------------
Exports clean star-schema and reporting tables from SQLite (`sap_procurement.db`)
to CSV files ready for 1-click import into Microsoft Power BI Desktop.
"""

import os
import sqlite3
import pandas as pd

def export_powerbi():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "database", "sap_procurement.db")
    pbi_dir = os.path.join(base_dir, "powerbi", "ready_to_import_csv")
    os.makedirs(pbi_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)

    tables = [
        "dim_suppliers",
        "dim_materials",
        "fact_purchase_orders",
        "fact_po_lines",
        "fact_goods_receipts",
        "fact_invoice_lines",
        "rpt_3way_match_exceptions"
    ]

    for tbl in tables:
        df = pd.read_sql_query(f"SELECT * FROM {tbl}", conn)
        out_csv = os.path.join(pbi_dir, f"{tbl}.csv")
        df.to_csv(out_csv, index=False)
        print(f"Exported {len(df)} rows to {out_csv}")

    conn.close()
    print("All Project 2 Power BI ready CSVs exported successfully!")

if __name__ == "__main__":
    export_powerbi()
