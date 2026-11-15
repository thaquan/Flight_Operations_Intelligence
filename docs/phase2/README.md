# Phase 2 — Ingestion and Bronze Parquet

**Status: COMPLETE — 24/24 official BTS months ingested and reconciled.**

Phase 2 turns the verified January 2024–December 2025 source ZIPs into a partitioned, lineage-aware local Bronze dataset. This is a batch ingestion layer, not a cleaned analytical model.

## Verified outcome

| Measure | Result |
| --- | ---: |
| Source months / Bronze partitions | 24 / 24 |
| Source observations retained | 14,080,680 |
| 2024 observations | 7,079,061 |
| 2025 observations | 7,001,619 |
| Source fields + lineage fields | 109 + 4 |
| Total Bronze Parquet bytes | 445,109,486 |
| Full deep validation | PASS |
| Repeated full-period ingestion | 24 skips, zero writes |
| Python tests (Phase 1 + Phase 2) | 33 passed |

## Data flow

1. **Raw:** The 24 official monthly ZIPs are stored under `data/raw/bts/`.
2. **Source verification:** The file must match the Phase 1 SHA-256, byte count, CSV member and ZIP CRC.
3. **Streaming conversion:** PyArrow reads the ZIP member in bounded batches and writes a temporary Parquet file.
4. **Quality gate:** Record count and Parquet schema must match the verified Phase 1 baseline.
5. **Publish:** The validated partition is moved into `data/bronze/bts/`; successful state is recorded in the ingestion manifest.
6. **Read:** Polars or PyArrow can query the resulting Parquet files. PostgreSQL loading begins in Phase 3.

## Phase 2 documentation

- [Bronze schema and partition layout](bronze_schema.md)
- [Incremental ingestion and recovery design](ingestion_design.md)
- [Operational runbook](runbook.md)
- [Data validation and test evidence](data_validation.md)
- [Measured performance and compression benchmark](performance_benchmark.md)
- [Full validation report (JSON)](full_validation.json)
- [Compression comparison (JSON)](compression_benchmark.json)

The source [Phase 1 handoff](../phase1/2024_2025/phase2_handoff.md) defines the acceptance criteria. Raw ZIPs, Bronze Parquet files, local manifests, staging files and backups are ignored by Git. The small reports and executable pipeline code are versioned.
