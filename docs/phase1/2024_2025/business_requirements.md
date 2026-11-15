# Business Requirements

## Problem statement

Airlines and airports face recurring flight delays, cancellations and diversions. An analytics team needs a consistent historical view of those outcomes across carriers, locations, routes and seasons. This portfolio platform uses the public BTS reporting-carrier dataset to answer those questions with traceable source records.

## Target users

| User | Decision supported |
| --- | --- |
| Airline operations analyst | Identify routes and monthly periods with elevated 15-minute arrival delay rates. |
| Airport operations analyst | Compare cancellation and punctuality outcomes across major origin airports. |
| Operations manager | Monitor year-over-year shifts in flight volumes and service reliability. |
| Data platform engineer | Verify source completeness, rerun historical months and trace a KPI back to its source file. |

## Required business questions

1. How many scheduled flights, completed flights, cancellations and diversions were reported each month in 2024 and 2025?
2. How did arrival punctuality change from 2024 to 2025, overall and by matched calendar month?
3. Which airlines and airports had the largest reported traffic volumes? How do their delay and cancellation rates compare?
4. Which directed origin-to-destination routes experienced elevated arrival delays, and how stable are the findings when minimum flight-count thresholds are applied?
5. How do BTS-classified carrier, weather, NAS, security and late-aircraft delay minutes contribute to reported delays?
6. What seasonal or day-of-week patterns are visible in the 24-month period?
7. In Phase 6, how do recorded weather conditions near an airport correlate with delays when observations are joined as-of scheduled departure time?

## Functional requirements

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| BR-01 | Acquire all 24 official BTS month files. | Month-complete acquisition manifest with checksums and ZIP validation. |
| BR-02 | Retain all airports, carriers and flight outcomes. | Raw files and unfiltered row-count reconciliation. |
| BR-03 | Measure full-period data quality. | 24 month profiles and an aggregate report with missingness and anomaly counts. |
| BR-04 | Provide common KPI definitions. | Documented numerators, denominators and NULL-handling rules. |
| BR-05 | Support 2024 versus 2025 comparisons. | Yearly totals and volume-weighted performance measures. |
| BR-06 | Focus BI on approximately 20 high-volume origin airports while retaining complete data. | Dynamic dashboard ranking or a documented fixed cohort derived from the full population. |
| BR-07 | Enable rerunnable batch processing. | File hashes, idempotent source-file handling, unit tests and later transactional loads. |
| BR-08 | Keep costs sustainable for an intern portfolio. | Local Python, Parquet, PostgreSQL, dbt Core, Power BI Desktop and Dagster OSS. |

## Non-functional requirements

- **Traceability:** every curated flight row must retain source month, filename and original row position in Phase 2 onward.
- **Correctness:** source-row totals must reconcile with Bronze and warehouse totals or an explicit quarantine ledger.
- **Idempotency:** reprocessing one month must not duplicate warehouse records.
- **Maintainability:** clear Python modules, tests, configuration, logs and concise English documentation.
- **Performance:** Phase 8 will measure actual runtimes, storage and query plans; no unmeasured target is presented as achieved.
- **Security:** do not commit credentials, raw data or local database files.
- **Portability:** the MVP must run without paid Microsoft Fabric or cloud infrastructure.

## Out of scope for the MVP

Real-time streaming, flight prediction models, airfare/pricing, airline profitability, passenger-level journey analytics and causal claims about weather effects.
