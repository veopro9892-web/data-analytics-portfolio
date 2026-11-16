-- =====================================================================
-- Database Schema: SAP-Aligned 3-Way Match Procurement Simulation
-- Simulating SAP S/4HANA (LFA1, MARA, EKKO, EKPO, MSEG/MATDOC, RBKP/RSEG)
-- Currency: INR (₹) throughout
-- SQLite 3 Compatible DDL
-- =====================================================================

DROP TABLE IF EXISTS rpt_3way_match_exceptions;
DROP TABLE IF EXISTS fact_invoice_lines;
DROP TABLE IF EXISTS fact_goods_receipts;
DROP TABLE IF EXISTS fact_po_lines;
DROP TABLE IF EXISTS fact_purchase_orders;
DROP TABLE IF EXISTS dim_materials;
DROP TABLE IF EXISTS dim_suppliers;

-- 1. Supplier Master (SAP: LFA1)
CREATE TABLE dim_suppliers (
    supplier_id TEXT PRIMARY KEY,       -- e.g. 'VEND-1001'
    supplier_name TEXT NOT NULL,
    vendor_code TEXT NOT NULL UNIQUE,   -- SAP Vendor Code e.g. '1000101'
    city TEXT NOT NULL,
    payment_terms TEXT NOT NULL,        -- 'Net 30', 'Net 45', 'Net 60'
    contact_email TEXT NOT NULL
);

-- 2. Material Master (SAP: MARA / MAKT)
CREATE TABLE dim_materials (
    material_code TEXT PRIMARY KEY,     -- e.g. 'MAT-101'
    material_description TEXT NOT NULL,
    material_group TEXT NOT NULL,       -- 'RAW_COFFEE', 'PACKAGING', 'EQUIPMENT_PARTS', 'DAIRY_SYRUP'
    base_uom TEXT NOT NULL              -- 'KG', 'BOX', 'EA', 'LTR'
);

-- 3. Purchasing Document Header (SAP: EKKO)
CREATE TABLE fact_purchase_orders (
    po_number TEXT PRIMARY KEY,         -- e.g. 'PO-45000001'
    supplier_id TEXT NOT NULL,
    company_code TEXT NOT NULL DEFAULT '1000',
    purchasing_org TEXT NOT NULL DEFAULT '1000',
    po_date DATE NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT NOT NULL,               -- 'APPROVED', 'CLOSED'
    FOREIGN KEY (supplier_id) REFERENCES dim_suppliers (supplier_id)
);

-- 4. Purchasing Document Item (SAP: EKPO)
CREATE TABLE fact_po_lines (
    po_number TEXT NOT NULL,
    line_item INTEGER NOT NULL,         -- 10, 20, 30...
    material_code TEXT NOT NULL,
    ordered_quantity REAL NOT NULL,
    po_unit_price REAL NOT NULL,        -- Price in INR
    uom TEXT NOT NULL,
    expected_delivery_date DATE NOT NULL,
    po_line_total REAL NOT NULL,        -- ordered_quantity * po_unit_price
    PRIMARY KEY (po_number, line_item),
    FOREIGN KEY (po_number) REFERENCES fact_purchase_orders (po_number),
    FOREIGN KEY (material_code) REFERENCES dim_materials (material_code)
);

-- 5. Goods Receipt Document Item (SAP: MSEG / MATDOC / MIGO)
CREATE TABLE fact_goods_receipts (
    gr_number TEXT NOT NULL,            -- e.g. 'GR-500001'
    material_doc_year INTEGER NOT NULL DEFAULT 2026,
    po_number TEXT NOT NULL,
    line_item INTEGER NOT NULL,
    gr_date DATE NOT NULL,
    received_quantity REAL NOT NULL,
    movement_type TEXT NOT NULL DEFAULT '101', -- 101: GR for PO into warehouse
    storage_location TEXT NOT NULL DEFAULT 'SL-01',
    PRIMARY KEY (gr_number, po_number, line_item),
    FOREIGN KEY (po_number, line_item) REFERENCES fact_po_lines (po_number, line_item)
);

-- 6. Incoming Invoice Document Item (SAP: RBKP / RSEG / MIRO)
CREATE TABLE fact_invoice_lines (
    invoice_number TEXT NOT NULL,       -- e.g. 'INV-900001'
    invoice_date DATE NOT NULL,
    supplier_id TEXT NOT NULL,
    po_number TEXT NOT NULL,
    line_item INTEGER NOT NULL,
    invoiced_quantity REAL NOT NULL,
    invoice_unit_price REAL NOT NULL,   -- Billed unit price in INR
    invoiced_amount REAL NOT NULL,      -- invoiced_quantity * invoice_unit_price
    tax_amount REAL NOT NULL,           -- GST 18% or 5%
    payment_status TEXT NOT NULL,       -- 'PENDING_MATCH', 'BLOCKED_AP_REVIEW', 'POSTED_CLEARED'
    PRIMARY KEY (invoice_number, po_number, line_item),
    FOREIGN KEY (po_number, line_item) REFERENCES fact_po_lines (po_number, line_item),
    FOREIGN KEY (supplier_id) REFERENCES dim_suppliers (supplier_id)
);

-- Indexes for performance
CREATE INDEX idx_po_supplier ON fact_purchase_orders (supplier_id);
CREATE INDEX idx_gr_po_line ON fact_goods_receipts (po_number, line_item);
CREATE INDEX idx_inv_po_line ON fact_invoice_lines (po_number, line_item);
