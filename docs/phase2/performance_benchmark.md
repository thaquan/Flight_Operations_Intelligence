# Phase 2 Measured Performance

Measurements were collected on **2026-11-15** on a Windows machine running Python 3.13.15, PyArrow 26.0.1 and Polars 1.44.2. This is a local portfolio benchmark, not a cloud-service performance claim.

## Full-period storage

| Measurement | Bytes |
| --- | ---: |
| Official 24 compressed monthly ZIPs | 709,735,704 |
| Original 24 CSV files, uncompressed | 6,370,981,019 |
| Published 24 ZSTD Parquet files | **445,109,486** |

- **CSV-to-Parquet size ratio:** 14.31:1.
- **Parquet vs source ZIP size:** approximately 37.3% fewer bytes.
- **Rows retained:** 14,080,680 / 14,080,680.
- **Bronze layout:** one Parquet file per calendar month.

## Ingestion and idempotency

| Measurement | Observed value |
| --- | ---: |
| Sum of the 24 recorded monthly ingestion durations | 233.589 s |
| Total rows / summed monthly ingestion duration | 60,279.7 rows/s |
| Repeated 24-month command (all partitions current) | 3.918 s |
| Number of skipped months on rerun | 24 |
| Ingestion manifest SHA-256 changed on rerun | No |

Each per-month ingestion duration includes source verification, ZIP-to-Parquet conversion, Parquet checksum, count/schema validation and manifest publication. The sum is **not** an end-to-end first-run wall-clock measurement; process startup and the gaps between separate invocations are excluded.

Peak process memory was **not measured**, so no RAM benchmark is claimed. The writer operates on bounded Arrow CSV batches rather than materializing the entire source CSV.

## Compression comparison: January 2024

Both candidates processed the same verified **547,271-row** BTS month (246,830,488 uncompressed source CSV bytes) with identical code and 30 Parquet row groups.

| Codec | Parquet bytes | Conversion + file-hashing time | Rows/s |
| --- | ---: | ---: | ---: |
| Snappy | 22,852,840 | 6.921 s | 79,068.8 |
| **ZSTD** | **17,833,166** | 7.228 s | 75,716.9 |

ZSTD produced a file approximately **22.0% smaller** while taking about **4.4% longer** in this single-month run. It is the chosen Bronze compression codec because the project prioritizes low-cost local storage and downstream reads.

This comparison is one run per codec on one month, not a statistically robust performance study. CPU load, cache state and storage conditions can affect timings. See [compression_benchmark.json](compression_benchmark.json) for the recorded measurements and source checksum.

## Reproduce

```bash
python -m src.phase2.benchmark --month 2024-01
python -m src.phase2.ingest --start 2024-01 --end 2025-12
python -m src.phase2.validate --deep --report docs/phase2/full_validation.json
```

Benchmark Parquet outputs are stored under ignored `data/tmp/phase2_benchmark/`, not committed to the repository.
