"""Read-only Bronze/Silver/Gold quality report with PASS/REVIEW/FAIL gates.

Full mode validates the actual 2024-2025 BTS source manifest; fixture mode
checks the tiny isolated CI database without pretending it has 24 months.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import psycopg

from src.phase3.config import PROJECT_ROOT, read_env

from .ci_fixture import EXPECTED_MONTHLY_ROWS, require_fixture_environment

METRICS = (
    "scheduled_flights",
    "completed_flights",
    "cancelled_flights",
    "diverted_flights",
    "eligible_arrivals",
    "late_arrivals_15",
    "on_time_arrivals",
)

PROFILE_FIELDS = {
    "scheduled_flights": "scheduled_flights",
    "completed_flights": "completed_flights",
    "cancelled_flights": "cancelled_flights",
    "diverted_flights": "diverted_not_cancelled_flights",
    "eligible_arrivals": "arrival_delay15_eligible_flights",
    "late_arrivals_15": "arrival_delayed_15min",
    "on_time_arrivals": "on_time_arrivals",
}


def check(name: str, valid: bool, detail: str) -> dict[str, str]:
    return {"name": name, "status": "PASS" if valid else "FAIL", "detail": detail}


def as_monthly(rows: list[tuple], *, key: int = 0) -> dict[str, tuple]:
    """Reject duplicate month keys instead of silently overwriting them."""
    result: dict[str, tuple] = {}
    for row in rows:
        month = str(row[key])
        if month in result:
            raise ValueError(f"Duplicate month in quality input: {month}")
        result[month] = tuple(row[:key] + row[key + 1 :])
    return result


def evaluate(
    network: dict[str, tuple],
    fact: dict[str, int],
    silver: dict[str, int],
    audit: dict[str, tuple],
    segment_rows: list[tuple],
    *,
    expected_months: set[str],
    profile: dict | None,
    manifest: dict | None,
    baseline_monthly: dict[str, int] | None,
) -> dict:
    """Pure validation logic, also exercised with intentionally broken inputs."""
    findings: list[dict[str, str]] = []
    all_sets = {
        "network": set(network), "fact": set(fact),
        "silver": set(silver), "audit": set(audit),
    }
    valid_coverage = all(months == expected_months for months in all_sets.values())
    findings.append(check(
        "source_month_coverage", valid_coverage,
        f"Expected {len(expected_months)} months; actual: "
        + ", ".join(f"{name}={len(months)}" for name, months in all_sets.items()),
    ))

    count_issues: list[str] = []
    lineage_issues: list[str] = []
    for month in sorted(expected_months):
        counters = network.get(month)
        if counters is None:
            continue
        scheduled = int(counters[0])
        if scheduled != fact.get(month):
            count_issues.append(f"{month}: network={scheduled}, fact={fact.get(month)}")
        audit_record = audit.get(month)
        if audit_record is not None:
            source_sha, bronze_count, silver_audit_count = audit_record
            actual_silver = silver.get(month)
            if not (bronze_count == silver_audit_count == actual_silver == scheduled):
                lineage_issues.append(
                    f"{month}: bronze={bronze_count}, audited_silver={silver_audit_count}, "
                    f"actual_silver={actual_silver}, network={scheduled}"
                )
            if manifest is not None and source_sha != manifest.get(month):
                lineage_issues.append(f"{month}: source SHA-256 differs from manifest")
        if baseline_monthly is not None and scheduled != baseline_monthly.get(month):
            count_issues.append(
                f"{month}: scheduled={scheduled}, phase2={baseline_monthly.get(month)}"
            )
    findings.append(check(
        "source_to_fact_monthly_counts", not count_issues,
        "; ".join(count_issues[:8]) if count_issues else "All monthly row counts reconcile",
    ))
    findings.append(check(
        "bronze_silver_audit_and_hashes", not lineage_issues,
        "; ".join(lineage_issues[:8]) if lineage_issues else
        "Load audit counts and source SHA-256 values match",
    ))

    segments: dict[tuple[str, str], tuple] = {}
    segment_issues: list[str] = []
    for role, month, *counters in segment_rows:
        identifier = (role, month)
        if identifier in segments:
            segment_issues.append(f"Duplicate segment/month: {role}/{month}")
        segments[identifier] = tuple(counters)
    for role in ("airline", "route", "origin", "destination"):
        for month in sorted(expected_months):
            if segments.get((role, month)) != network.get(month):
                segment_issues.append(f"{role}/{month} differs from network")
    findings.append(check(
        "segment_kpi_reconciliation", not segment_issues,
        "; ".join(segment_issues[:8]) if segment_issues else
        "Airline, route, origin and destination reconcile independently",
    ))

    denominator_issues: list[str] = []
    for month, values in network.items():
        scheduled, completed, cancelled, diverted, eligible, late, on_time = values
        if (scheduled <= 0 or completed + cancelled + diverted > scheduled
                or eligible > completed or late + on_time != eligible):
            denominator_issues.append(month)
    findings.append(check(
        "arrival_kpi_denominators", not denominator_issues,
        "Invalid months: " + ", ".join(denominator_issues)
        if denominator_issues else "Valid completed/eligible arrival counters",
    ))

    totals = {metric: sum(int(values[index]) for values in network.values())
              for index, metric in enumerate(METRICS)}
    if profile is not None:
        expected = profile["overall"]
        profile_issues = [
            f"{field}: gold={totals[field]}, phase1={expected[source_field]}"
            for field, source_field in PROFILE_FIELDS.items()
            if totals[field] != expected[source_field]
        ]
        findings.append(check(
            "phase1_population_baseline", not profile_issues,
            "; ".join(profile_issues) if profile_issues else
            "All seven additive metrics match the verified Phase 1 population",
        ))
        for warning in profile.get("checks", {}).get("warnings", []):
            findings.append({
                "name": "documented_source_exception",
                "status": "REVIEW",
                "detail": warning,
            })
    else:
        findings.append(check(
            "fixture_population", totals["scheduled_flights"] == 10,
            f"Expected 10 synthetic flights; got {totals['scheduled_flights']}",
        ))

    statuses = Counter(item["status"] for item in findings)
    return {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FAIL" if statuses["FAIL"] else
                  "REVIEW" if statuses["REVIEW"] else "PASS",
        "summary": {name: statuses[name] for name in ("PASS", "REVIEW", "FAIL")},
        "monthly_count": len(network),
        "totals": totals,
        "checks": findings,
    }


def fetch_report(conn: psycopg.Connection, *, fixture: bool) -> dict:
    metric_sql = ", ".join(METRICS)
    network = as_monthly(conn.execute(
        f"select to_char(source_month,'YYYY-MM'), {metric_sql} "
        "from gold.mart_network_monthly order by source_month"
    ).fetchall())
    fact = dict(conn.execute(
        "select to_char(source_month,'YYYY-MM'), count(*) "
        "from gold.fct_flights group by source_month"
    ).fetchall())
    silver = dict(conn.execute(
        "select to_char(source_month,'YYYY-MM'), count(*) "
        "from silver.flights group by source_month"
    ).fetchall())
    audit = as_monthly(conn.execute(
        "select to_char(source_month,'YYYY-MM'), source_sha256, "
        "bronze_row_count, silver_row_count from audit.silver_loads"
    ).fetchall())
    segments = conn.execute(
        "select 'airline'::text, to_char(source_month,'YYYY-MM'), "
        f"{', '.join('sum(' + key + ')' for key in METRICS)} "
        "from gold.mart_airline_monthly group by source_month "
        "union all select 'route', to_char(source_month,'YYYY-MM'), "
        f"{', '.join('sum(' + key + ')' for key in METRICS)} "
        "from gold.mart_route_monthly group by source_month "
        "union all select airport_role, to_char(date_trunc('month',flight_date),'YYYY-MM'), "
        f"{', '.join('sum(' + key + ')' for key in METRICS)} "
        "from gold.mart_airport_daily "
        "group by airport_role, date_trunc('month',flight_date)"
    ).fetchall()

    profile = manifest = baseline = None
    if fixture:
        expected_months = set(EXPECTED_MONTHLY_ROWS)
    else:
        base = PROJECT_ROOT / "docs"
        profile = json.loads((base / "phase1/2024_2025/aggregate_profile.json").read_text(
            encoding="utf-8"
        ))
        acquisition = json.loads((base / "phase1/2024_2025/acquisition_manifest.json").read_text(
            encoding="utf-8"
        ))
        manifest = {entry["month"]: entry["sha256"] for entry in acquisition["files"]}
        reconciliation = json.loads((base / "phase3/m32_reconciliation.json").read_text(
            encoding="utf-8"
        ))
        baseline = {entry["month"]: entry["bronze_rows"]
                    for entry in reconciliation["monthly"]}
        expected_months = set(manifest)
    return evaluate(
        network, fact, silver, audit, segments,
        expected_months=expected_months, profile=profile,
        manifest=manifest, baseline_monthly=baseline,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("full", "fixture"), default="full")
    parser.add_argument("--report", type=Path, help="Optional JSON output path")
    args = parser.parse_args()
    if args.mode == "fixture":
        connection = require_fixture_environment()
    else:
        configuration = read_env(PROJECT_ROOT / ".env")
        connection = {
            "host": "127.0.0.1", "port": int(configuration["POSTGRES_PORT"]),
            "dbname": configuration["POSTGRES_DB"],
            "user": configuration["POSTGRES_USER"],
            "password": configuration["POSTGRES_PASSWORD"],
        }
    with psycopg.connect(**connection) as conn:
        report = fetch_report(conn, fixture=args.mode == "fixture")
    result = json.dumps(report, indent=2, ensure_ascii=False)
    print(result)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(result + "\n", encoding="utf-8")
    if report["summary"]["FAIL"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
