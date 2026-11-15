# Source, Scope and Acquisition Decisions

## Primary source

- Publisher: U.S. Department of Transportation, Bureau of Transportation Statistics (BTS).
- Dataset: **Reporting Carrier On-Time Performance (1987-present)**.
- Official selection interface: https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=&gnoyr_VQ=FGJ
- Monthly pre-zipped files: https://transtats.bts.gov/PREZIP/
- Fields and definitions: https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ
- Grain: one row per reported scheduled domestic non-stop flight operated by a reporting carrier.
- Historical service dates included in this project: **2024-01-01 through 2025-12-31**, exactly 24 calendar months.

This source is **not** a worldwide flight feed. Its population is the flights that fall within BTS on-time reporting requirements. Reporting-carrier and marketing-carrier products must not be unioned as independent flight observations.

## Inclusion and exclusion decisions

| Decision | Rule |
| --- | --- |
| Airlines | Retain every reporting carrier present in the 24 source files. |
| Airports | Retain all reported origin and destination airports. |
| Flight outcomes | Retain completed, cancelled and diverted records. |
| Analysis period | Exactly 2024-01 through 2025-12, no partial-month replacement. |
| Dashboard focus | Rank origin airports by total 2024-2025 scheduled departures; highlight the highest 20 without filtering the underlying fact table. |
| Geographic scope | U.S. domestic non-stop routes represented in the BTS source. |
| Exclusions | Revenue, ticket prices, passenger counts, international arrivals not represented in the source, and live aircraft locations. |
| Secondary data | NOAA GHCNh hourly weather is deferred to Phase 6. |

## Acquisition and provenance contract

Each month has exactly one expected BTS ZIP filename:

`On_Time_Reporting_Carrier_On_Time_Performance_1987_present_<YEAR>_<MONTH>.zip`

The month in this filename is not zero-padded. ZIP files are stored under `data/raw/bts/<YEAR>/`. The acquisition script:

1. Downloads directly from the official BTS PREZIP directory.
2. Streams bytes to a temporary file and renames only after verification.
3. Requires exactly one CSV member in each archive.
4. Checks the CRC of every member and records SHA-256, file bytes and CSV member bytes.
5. Verifies an existing ZIP without silently replacing it.
6. Produces `acquisition_manifest.json`, one entry per requested month.

Raw ZIPs are excluded from version control and project release archives. The manifest and documented command allow reproducible reacquisition.

## Source caveats

- The source is released as periodic historical batches, not as a real-time flight event stream.
- Scheduled and actual departure/arrival times are airport-local HHMM clock values. They are **not** UTC instants.
- Many delay-cause, cancellation and diversion fields are conditionally populated; high null rates can be valid business semantics.
- A flight's `ArrDelay` can be negative for an early arrival; NULL does not mean zero.
- A key formed from carrier, flight number, date, airports and scheduled departure is only a **candidate** until source collisions are reconciled.
- NOAA observations in Phase 6 require an explicit airport-to-station mapping, time-zone resolution and point-in-time selection.

## Reproducibility

From the repository root:

```bash
python -m src.phase1.download_bts --start 2024-01 --end 2025-12 --workers 3
python -m src.phase1.run_phase1 --workers 4
python -m src.phase1.build_report
python -m unittest discover -s tests -v
```

The final command fails when a required month is absent or source reconciliation detects a blocking error. The exact list of verified files and their checksums is in `acquisition_manifest.json`.
