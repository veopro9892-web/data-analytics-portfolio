# Power BI Star Schema Data Model

```mermaid
erDiagram
    dim_dates ||--o{ fact_orders : "order_date -> date_key (1:N)"
    dim_channels ||--o{ fact_orders : "channel_id -> channel_id (1:N)"
    dim_time_slots ||--o{ fact_orders : "slot_id -> slot_id (1:N)"
    fact_orders ||--o{ fact_order_items : "order_id -> order_id (1:N)"
    dim_menu_items ||--o{ fact_order_items : "item_id -> item_id (1:N)"

    dim_dates {
        string date_key PK
        date full_date
        int day_of_week
        string day_name
        int is_weekend
        int week_of_year
        string month_name
    }

    dim_channels {
        string channel_id PK
        string channel_name
        string channel_type
        float commission_pct
    }

    dim_time_slots {
        string slot_id PK
        string slot_name
        int start_hour
        int end_hour
        string slot_description
    }

    dim_menu_items {
        string item_id PK
        string item_name
        string category
        float base_price_in_store
    }

    fact_orders {
        string order_id PK
        string channel_id FK
        datetime order_timestamp
        string order_date FK
        int order_hour
        string slot_id FK
        string order_status
        float gross_order_total
        float order_discount_amt
        float order_refund_amt
        float net_sales_amount
        int item_count
        int total_quantity
        string payment_info
    }

    fact_order_items {
        string order_item_id PK
        string order_id FK
        int item_seq
        string item_id FK
        int quantity
        float unit_price
        float gross_line_amount
        float allocated_line_net
    }
```

## Relationship Configuration Matrix

| From Table (`*` Many) | Foreign Key | To Table (`1` One) | Primary Key | Cardinality | Cross Filter Direction | Active |
|---|---|---|---|---|---|---|
| `fact_orders` | `order_date` | `dim_dates` | `date_key` | Many to One (*:1) | Single (`dim_dates` filters `fact_orders`) | Yes |
| `fact_orders` | `channel_id` | `dim_channels` | `channel_id` | Many to One (*:1) | Single (`dim_channels` filters `fact_orders`) | Yes |
| `fact_orders` | `slot_id` | `dim_time_slots` | `slot_id` | Many to One (*:1) | Single (`dim_time_slots` filters `fact_orders`) | Yes |
| `fact_order_items` | `order_id` | `fact_orders` | `order_id` | Many to One (*:1) | Single (`fact_orders` filters `fact_order_items`) | Yes |
| `fact_order_items` | `item_id` | `dim_menu_items` | `item_id` | Many to One (*:1) | Single (`dim_menu_items` filters `fact_order_items`) | Yes |
