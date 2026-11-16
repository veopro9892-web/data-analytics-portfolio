# Power BI Data Model Architecture — SAP Procurement 3-Way Match

```mermaid
erDiagram
    dim_suppliers ||--o{ fact_purchase_orders : "supplier_id (1:N)"
    dim_suppliers ||--o{ rpt_3way_match_exceptions : "supplier_id (1:N)"
    dim_materials ||--o{ fact_po_lines : "material_code (1:N)"
    dim_materials ||--o{ rpt_3way_match_exceptions : "material_code (1:N)"
    fact_purchase_orders ||--o{ fact_po_lines : "po_number (1:N)"
    fact_po_lines ||--o{ fact_goods_receipts : "po_number + line_item (1:N)"
    fact_po_lines ||--o{ fact_invoice_lines : "po_number + line_item (1:N)"
    fact_po_lines ||--|| rpt_3way_match_exceptions : "po_number + line_item (1:1)"

    dim_suppliers {
        string supplier_id PK
        string supplier_name
        string vendor_code
        string city
        string payment_terms
        string contact_email
    }

    dim_materials {
        string material_code PK
        string material_description
        string material_group
        string base_uom
    }

    rpt_3way_match_exceptions {
        string po_number PK
        int line_item PK
        string supplier_id FK
        string supplier_name
        string material_code FK
        string material_description
        float ordered_quantity
        float received_quantity
        float invoiced_quantity
        float po_unit_price
        float invoice_unit_price
        float price_variance_pct
        date expected_delivery_date
        float po_line_total
        float invoiced_amount
        float amount_at_risk_inr
        string match_status
        string primary_exception_reason
        string exception_reasons
        string relevant_invoice_ids
        string suggested_next_action
    }
```

## Power BI Relationship Configuration

| From Table (`*` Many) | Foreign Key | To Table (`1` One) | Primary Key | Cardinality | Cross Filter Direction | Active |
|---|---|---|---|---|---|---|
| `rpt_3way_match_exceptions` | `supplier_id` | `dim_suppliers` | `supplier_id` | Many to One (*:1) | Single (`dim_suppliers` filters Exceptions) | Yes |
| `rpt_3way_match_exceptions` | `material_code` | `dim_materials` | `material_code` | Many to One (*:1) | Single (`dim_materials` filters Exceptions) | Yes |
| `fact_purchase_orders` | `supplier_id` | `dim_suppliers` | `supplier_id` | Many to One (*:1) | Single (`dim_suppliers` filters Orders) | Yes |
| `fact_po_lines` | `po_number` | `fact_purchase_orders` | `po_number` | Many to One (*:1) | Single | Yes |
| `fact_po_lines` | `material_code` | `dim_materials` | `material_code` | Many to One (*:1) | Single | Yes |
| `fact_goods_receipts` | `po_number` | `fact_po_lines` | `po_number` | Many to One (*:1) | Single | No (Pre-aggregated in reporting table) |
| `fact_invoice_lines` | `po_number` | `fact_po_lines` | `po_number` | Many to One (*:1) | Single | No (Pre-aggregated in reporting table) |

> [!IMPORTANT]
> Notice that `fact_goods_receipts` and `fact_invoice_lines` are NOT joined directly to each other in Power BI. Joining them directly in the data model would re-introduce the fan-out / cartesian product trap. All multi-document aggregations are pre-resolved in the curated reporting table `rpt_3way_match_exceptions.csv`.
