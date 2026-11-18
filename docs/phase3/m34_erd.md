# M3.4 Star Schema ERD

```mermaid
erDiagram
    dim_date ||--o{ fct_flights : "flight_date_key"
    dim_airline ||--o{ fct_flights : "airline_sk"
    dim_airport ||--o{ fct_flights : "origin_airport_sk"
    dim_airport ||--o{ fct_flights : "dest_airport_sk"

    dim_date {
        int date_key PK
        date flight_date UK
        smallint calendar_year
        smallint calendar_month
        smallint iso_day_of_week
    }
    dim_airline {
        int airline_sk PK
        int airline_dot_id UK
        text airline_code
        bool is_unknown
    }
    dim_airport {
        int airport_sk PK
        int airport_id UK
        text airport_code
        text city_name
        text state_code
        bool is_unknown
    }
    fct_flights {
        bigint flight_sk PK
        date source_month
        bigint source_row_number
        int flight_date_key FK
        int airline_sk FK
        int origin_airport_sk FK
        int dest_airport_sk FK
        text flight_status
        int eligible_arrival_count
        int arrival_delayed_15_count
    }
```

The two airport foreign keys both point to `dim_airport`. The star is
logical: dbt relationships tests validate foreign keys; PostgreSQL dbt
tables have a unique index on their surrogate keys, not physical
`FOREIGN KEY` constraints. The source identity is
`(source_month, source_row_number)`, preserved in `fct_flights` for audit.
