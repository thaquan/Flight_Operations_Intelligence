# Bronze Data Contract

## Dataset and grain

Each Bronze row corresponds to **one row in an official BTS Reporting Carrier On-Time Performance monthly CSV**. No source observations are deduplicated, filtered or aggregated.

- Period: January 2024 through December 2025.
- Source: 24 verified monthly ZIPs in `data/raw/bts/<YEAR>/`.
- Output: exactly one Parquet file per month, currently `part-00000.parquet`.
- Partition layout: `data/bronze/bts/flight_year=YYYY/flight_month=MM/`.
- The partition month is checked against every source `FlightDate` before publication.

## Fields

| Field group | Columns | Storage type | Rule |
| --- | ---: | --- | --- |
| All named BTS source fields | 109 | Parquet UTF-8 string, nullable | Preserve nonempty CSV text without inferred numeric/date conversions |
| `source_file` | 1 | String | Exact source ZIP filename |
| `source_sha256` | 1 | String | SHA-256 of the full official ZIP |
| `source_row_number` | 1 | Int64 | One-based CSV **data** row number, excluding the header |
| `ingested_at_utc` | 1 | Timestamp (microseconds, UTC) | Time of the conversion run |
| **Total** | **113** | | |

The source has an extra **unnamed, final CSV header field**. It is the only field removed; ingestion rejects any row that contains a nonempty value there. Duplicate or changed named headers are rejected.

Empty CSV text fields become Parquet NULL. All other source values remain strings, so leading zeros, values such as `2400` in HHMM columns, and untyped identifiers are not lost to early type conversion. The [Phase 1 field catalog](../phase1/2024_2025/field_catalog.md) describes the 109 original attributes.

## Lineage and identity

The pair (`source_file`, `source_row_number`) identifies the physical source observation. The SHA-256 identifies the exact ZIP version. Candidate business keys are not assumed to be unique in future source revisions.

The Bronze layer intentionally does **not**:

- infer UTC flight timestamps or interpret `2400`;
- fill missing flight numbers or delay measurements;
- remove cancelled/diverted flights;
- calculate delay KPIs or model airline/airport dimensions.

Those responsibilities belong to the PostgreSQL Silver and dbt Gold layers in Phase 3.

## Encoding and compression

- Parquet compression: **ZSTD**.
- CSV input block size: 8 MiB.
- Requested row-group maximum: 100,000 rows per write.
- Observed January 2024 output: 30 row groups for 547,271 rows (batch boundaries yield smaller groups).

ZSTD was chosen after a controlled comparison with Snappy on the same verified January 2024 source. See [measured benchmark](performance_benchmark.md).
