# BTS Flight Data Samples (2024-2025)

These CSV files contain **real rows from the official U.S. DOT/BTS Reporting Carrier On-Time Performance source**, not generated or synthetic flight observations.

## Files

| File | Rows | Intended use |
| --- | ---: | --- |
| `bts_flights_preview_1200.csv` | 1,200 | Compact file for direct viewing on GitHub. |
| `bts_flights_2024_2025_sample_10000.csv` | 10,000 | Small offline exploration and schema inspection. |
| `sample_manifest.json` | - | Sampling rules, source-month hashes, counts and output SHA-256. |
| `preview_manifest.json` | - | Preview selection rules and SHA-256. |

## How the sample was selected

- Period: all 24 months from January 2024 through December 2025.
- Full sample: 416 or 417 rows per month, using independent deterministic reservoir sampling within flight outcome categories; seed `42`.
- Full-sample outcome quotas per month: 6 cancelled, 3 diverted, and the remaining rows completed.
- Preview: 50 rows per month, including 46 completed, 3 cancelled and 1 diverted; selected deterministically from the full sample.
- All selected source fields are copied as original CSV text. Blank source fields remain blank.
- `source_month` and one-based `source_row_number` identify the original source record; `sample_status` is derived from `Cancelled` and `Diverted`.
- Every source month is reconciled against the original acquisition checksum and full-month profiling counts before generating the 10,000-row sample.

**Important:** This is an intentionally **stratified illustration**, not a statistically representative sample. Rare diverted flights are oversampled so that the reviewer can inspect them. **Do not calculate airline, airport, cancellation or on-time performance KPIs using these sample files.** Use the full source data and the [verified aggregate profile](../../docs/phase1/2024_2025/aggregate_profile.json) for population metrics.

## Reproduce the CSV files

After downloading the 24 official BTS monthly ZIP files:

```bash
python -m src.phase1.build_sample
python -m src.phase1.build_preview
```

The scripts require only Python's standard library. Run from the project root.

## Full dataset

- [Official BTS monthly downloads](https://transtats.bts.gov/PREZIP/).
- [BTS field definitions](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ).
- [Source acquisition manifest](../../docs/phase1/2024_2025/acquisition_manifest.json) contains every month, URL, SHA-256 and byte count.
- To download the exact source period, run `python -m src.phase1.download_bts --start 2024-01 --end 2025-12`.

The full raw-data package is distributed separately from Git history to avoid making every repository clone download hundreds of megabytes of immutable source ZIP files.
