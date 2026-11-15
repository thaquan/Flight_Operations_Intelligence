"""Validate all Phase 1 monthly profiles and produce an evidence-based report."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, timedelta
import json
from pathlib import Path

from .download_bts import month_range


KPI_FIELDS = (
    "scheduled_flights",
    "completed_flights",
    "cancelled_flights",
    "diverted_not_cancelled_flights",
    "arrival_delay15_eligible_flights",
    "on_time_arrivals",
    "arrival_delayed_15min",
)

FIELD_NOTES = {
    "FlightDate": ("DATE", "Scheduled flight service date", "Required for partitions and time-series analysis"),
    "Reporting_Airline": ("TEXT", "Reporting carrier code", "Carrier dimension label"),
    "DOT_ID_Reporting_Airline": ("INTEGER", "DOT reporting carrier identifier", "Carrier natural key candidate"),
    "Flight_Number_Reporting_Airline": ("TEXT", "Flight number for reporting carrier", "Part of candidate flight identity"),
    "Tail_Number": ("TEXT", "Aircraft registration", "Optional rotation analysis; can be missing"),
    "OriginAirportID": ("INTEGER", "BTS origin airport identifier", "Origin airport dimension key"),
    "DestAirportID": ("INTEGER", "BTS destination airport identifier", "Destination airport dimension key"),
    "Origin": ("TEXT", "Origin airport code", "Display and routing"),
    "Dest": ("TEXT", "Destination airport code", "Display and routing"),
    "CRSDepTime": ("HHMM TEXT", "Scheduled local departure time", "Local wall time, not UTC"),
    "CRSArrTime": ("HHMM TEXT", "Scheduled local arrival time", "Local wall time, not UTC"),
    "DepTime": ("HHMM TEXT", "Actual local departure time", "May be missing for cancellations"),
    "ArrTime": ("HHMM TEXT", "Actual local arrival time", "May be missing for cancellation/diversion"),
    "DepDelay": ("DECIMAL", "Signed departure delay in minutes", "Early departures can be negative"),
    "ArrDelay": ("DECIMAL", "Signed arrival delay in minutes", "Do not turn missing into zero"),
    "DepDel15": ("BOOLEAN", "Departure at least 15 minutes late", "Optional delay segmentation"),
    "ArrDel15": ("BOOLEAN", "Arrival at least 15 minutes late", "Core on-time KPI numerator"),
    "Cancelled": ("BOOLEAN", "Flight cancelled indicator", "Retain cancelled flight records"),
    "Diverted": ("BOOLEAN", "Flight diverted indicator", "Separate from cancellation"),
    "CancellationCode": ("TEXT", "Reported cancellation cause", "Conditional; sparse by design"),
    "Distance": ("DECIMAL", "Reported route distance in miles", "Not kilometres"),
    "CarrierDelay": ("DECIMAL", "Airline-attributable delay minutes", "Delay cause breakdown"),
    "WeatherDelay": ("DECIMAL", "BTS-classified weather delay minutes", "Different from NOAA observation"),
    "NASDelay": ("DECIMAL", "National Aviation System delay minutes", "Delay cause breakdown"),
    "SecurityDelay": ("DECIMAL", "Security-related delay minutes", "Delay cause breakdown"),
    "LateAircraftDelay": ("DECIMAL", "Late-arriving aircraft delay minutes", "Delay cause breakdown"),
    "Flights": ("DECIMAL", "Flight observation weight", "Expected to equal 1 in flight-level file"),
}


def rates(counts: Counter) -> dict:
    scheduled = counts["scheduled_flights"]
    eligible = counts["arrival_delay15_eligible_flights"]
    return {
        **{field: counts[field] for field in KPI_FIELDS},
        "arrival_on_time_pct": round(100 * counts["on_time_arrivals"] / eligible, 4) if eligible else None,
        "arrival_delay15_pct": round(100 * counts["arrival_delayed_15min"] / eligible, 4) if eligible else None,
        "cancellation_pct_of_scheduled": round(100 * counts["cancelled_flights"] / scheduled, 4) if scheduled else None,
        "diversion_pct_of_scheduled": round(100 * counts["diverted_not_cancelled_flights"] / scheduled, 4) if scheduled else None,
    }


def summarize(manifest: dict, profiles: dict[str, dict], start: str = "2024-01", end: str = "2025-12") -> dict:
    months = month_range(start, end)
    manifest_files = {entry["month"]: entry for entry in manifest.get("files", [])}
    errors: list[str] = []
    warnings: list[str] = []
    year_counts: dict[str, Counter] = {}
    overall_counts: Counter = Counter()
    origin_counts: Counter = Counter()
    destination_counts: Counter = Counter()
    airline_counts: Counter = Counter()
    route_counts: Counter = Counter()
    anomalies: Counter = Counter()
    null_counts: Counter = Counter()
    schema: list[str] | None = None
    monthly: list[dict] = []
    for month in months:
        file = manifest_files.get(month)
        profile = profiles.get(month)
        if file is None or profile is None:
            errors.append(f"{month}: missing {'manifest entry' if file is None else 'profile'}")
            continue
        if file.get("sha256") != profile["source"].get("zip_sha256"):
            errors.append(f"{month}: source ZIP SHA-256 does not match the profiling input")
        if file.get("zip_bytes") != profile["source"].get("zip_bytes"):
            errors.append(f"{month}: source ZIP byte count mismatch")
        rows = profile["dataset"]["rows"]
        if rows <= 0:
            errors.append(f"{month}: empty data file")
        year, month_number = (int(part) for part in month.split("-"))
        first = date(year, month_number, 1)
        next_month = date(year + (month_number == 12), month_number % 12 + 1, 1)
        last = next_month - timedelta(days=1)
        observed_days = len(profile.get("daily_counts", {}))
        if profile["dataset"].get("date_min") != first.isoformat() or profile["dataset"].get("date_max") != last.isoformat():
            errors.append(f"{month}: observed min/max flight dates do not cover calendar month")
        if observed_days != last.day:
            errors.append(f"{month}: observed {observed_days}/{last.day} flight dates")
        if profile["dataset"].get("invalid_flight_date_count", 0):
            errors.append(f"{month}: invalid FlightDate values")
        if profile["dataset"].get("missing_required_columns"):
            errors.append(f"{month}: missing required fields")
        if profile.get("anomalies", {}).get("outside_expected_month", 0):
            errors.append(f"{month}: records outside expected month")
        statuses = profile["dataset"]["status_counts"]
        status_total = sum(statuses.get(key, 0) for key in ("completed", "cancelled", "diverted_not_cancelled"))
        if status_total != rows:
            errors.append(f"{month}: {rows - status_total} records lack a valid flight status")
        month_schema = [column["name"] for column in profile["columns"]]
        if schema is None:
            schema = month_schema
        elif month_schema != schema:
            errors.append(f"{month}: schema differs from {months[0]}")
        for field in KPI_FIELDS:
            value = profile["kpis"][field]
            overall_counts[field] += value
            year_counts.setdefault(str(year), Counter())[field] += value
        for key, counter in (
            ("origin_counts", origin_counts),
            ("destination_counts", destination_counts),
            ("reporting_airline_counts", airline_counts),
            ("route_counts", route_counts),
        ):
            if key not in profile:
                errors.append(f"{month}: full {key} absent; cannot aggregate exact rankings")
            else:
                counter.update(profile[key])
        for column in profile["columns"]:
            null_counts[column["name"]] += column["null_count"]
        anomalies.update(profile.get("anomalies", {}))
        if profile.get("anomalies", {}).get("exact_duplicate_row", 0):
            warnings.append(f"{month}: exact duplicate source rows found; do not auto-drop")
        if profile.get("anomalies", {}).get("duplicate_candidate_business_key", 0):
            warnings.append(f"{month}: candidate business key collisions found; investigate before warehouse PK")
        if profile.get("anomalies", {}).get("missing_business_key_component", 0):
            warnings.append(f"{month}: flight record missing a candidate business-key component; preserve source-row lineage")
        if profile.get("anomalies", {}).get("completed_missing_arrdel15", 0):
            warnings.append(f"{month}: completed flight missing ArrDel15; excluded from arrival punctuality denominator")
        monthly.append({
            "month": month,
            "rows": rows,
            "date_min": profile["dataset"]["date_min"],
            "date_max": profile["dataset"]["date_max"],
            "distinct_flight_dates": profile["dataset"]["distinct_flight_dates"],
            **rates(Counter({field: profile["kpis"][field] for field in KPI_FIELDS})),
        })
    if manifest.get("failures"):
        errors.append(f"Acquisition manifest reports {len(manifest['failures'])} download failures")
    if len(manifest_files) != len(months):
        errors.append(f"Manifest has {len(manifest_files)} month entries; expected {len(months)}")
    if len(profiles) != len(months):
        errors.append(f"Found {len(profiles)} monthly profiles; expected {len(months)}")
    total_rows = overall_counts["scheduled_flights"]
    verified_zip_bytes = sum(item["zip_bytes"] for item in manifest_files.values())
    verified_csv_bytes = sum(item["csv_uncompressed_bytes"] for item in manifest_files.values() if "csv_uncompressed_bytes" in item)
    yearly = {year: rates(counts) for year, counts in sorted(year_counts.items())}
    yoy = None
    if "2024" in yearly and "2025" in yearly:
        prev, current = yearly["2024"], yearly["2025"]
        yoy = {
            "scheduled_flights_pct_change": round(100 * (current["scheduled_flights"] / prev["scheduled_flights"] - 1), 4) if prev["scheduled_flights"] else None,
            "arrival_delay15_percentage_point_change": round(current["arrival_delay15_pct"] - prev["arrival_delay15_pct"], 4) if current["arrival_delay15_pct"] is not None and prev["arrival_delay15_pct"] is not None else None,
            "cancellation_percentage_point_change": round(current["cancellation_pct_of_scheduled"] - prev["cancellation_pct_of_scheduled"], 4) if current["cancellation_pct_of_scheduled"] is not None and prev["cancellation_pct_of_scheduled"] is not None else None,
        }

    def ranking(counter: Counter, label: str, limit: int = 20) -> list[dict]:
        return [{label: name, "flights": count} for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]]

    return {
        "source_manifest_generated_at_utc": manifest.get("generated_at_utc"),
        "period": {"start": start, "end": end, "expected_months": len(months), "verified_months": len(monthly)},
        "phase1_complete": len(monthly) == len(months) and not errors,
        "checks": {"errors": errors, "warnings": warnings},
        "overall": rates(overall_counts),
        "source_storage": {
            "verified_zip_bytes": verified_zip_bytes,
            "verified_uncompressed_csv_bytes": verified_csv_bytes,
        },
        "distinct_entities": {
            "origin_airports": len(origin_counts),
            "destination_airports": len(destination_counts),
            "reporting_airlines": len(airline_counts),
            "directed_routes": len(route_counts),
        },
        "by_year": yearly,
        "year_over_year_2025_vs_2024": yoy,
        "monthly": monthly,
        "schema": {"named_columns": len(schema or []), "fields": schema or []},
        "data_quality": {
            "anomalies": dict(sorted(anomalies.items())),
            "column_missingness": [
                {"name": field, "null_count": count, "null_pct": round(100 * count / total_rows, 6) if total_rows else None}
                for field, count in sorted(null_counts.items())
            ],
        },
        "top_20_origin_airports": ranking(origin_counts, "airport"),
        "top_20_destination_airports": ranking(destination_counts, "airport"),
        "top_20_reporting_airlines": ranking(airline_counts, "airline"),
        "top_20_directed_routes": ranking(route_counts, "route"),
    }


def markdown_report(summary: dict) -> str:
    status = "PASS" if summary["phase1_complete"] else "INCOMPLETE"
    lines = [
        "# BTS 2024-2025: Full-Scope Data Quality Assessment",
        "",
        f"**Validation status:** {status}. Source manifest timestamp: {summary['source_manifest_generated_at_utc']}.",
        "",
        f"**Coverage:** {summary['period']['verified_months']}/{summary['period']['expected_months']} months.",
        f"**Flight records:** {summary['overall']['scheduled_flights']:,} (all reporting airlines and airports).",
        f"**Source columns:** {summary['schema']['named_columns']}.",
        f"**Compressed ZIP storage:** {summary['source_storage']['verified_zip_bytes']:,} bytes.",
        f"**Uncompressed CSV storage:** {summary['source_storage']['verified_uncompressed_csv_bytes']:,} bytes.",
        f"**Distinct origin airports / reporting airlines / directed routes:** {summary['distinct_entities']['origin_airports']:,} / {summary['distinct_entities']['reporting_airlines']:,} / {summary['distinct_entities']['directed_routes']:,}.",
        "",
        "## Year-by-year measured KPIs",
        "",
        "| Year | Scheduled flights | Eligible arrivals | Arrival >=15 min late | Cancellation rate |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for year, data in summary["by_year"].items():
        lines.append(f"| {year} | {data['scheduled_flights']:,} | {data['arrival_delay15_eligible_flights']:,} | {data['arrival_delay15_pct']:.2f}% | {data['cancellation_pct_of_scheduled']:.2f}% |")
    lines.extend(["", "Rates are recomputed from total counts, not averaged from monthly percentages.", ""])
    if summary["year_over_year_2025_vs_2024"]:
        yoy = summary["year_over_year_2025_vs_2024"]
        lines.extend([
            "## 2025 versus 2024",
            "",
            f"- Scheduled flight volume: {yoy['scheduled_flights_pct_change']:+.2f}%.",
            f"- Arrival delay >=15 minutes: {yoy['arrival_delay15_percentage_point_change']:+.2f} percentage points.",
            f"- Cancellation: {yoy['cancellation_percentage_point_change']:+.2f} percentage points.",
            "",
        ])
    lines.extend([
        "## Monthly source coverage",
        "",
        "| Month | Rows | First flight date | Last flight date | Delay >=15 min |",
        "| --- | ---: | --- | --- | ---: |",
    ])
    for item in summary["monthly"]:
        lines.append(f"| {item['month']} | {item['rows']:,} | {item['date_min']} | {item['date_max']} | {item['arrival_delay15_pct']:.2f}% |")
    lines.extend(["", "## Top 20 origin airports by reported flight count", "", "| Rank | Airport | Flights |", "| ---: | --- | ---: |"])
    for rank, item in enumerate(summary["top_20_origin_airports"], 1):
        lines.append(f"| {rank} | {item['airport']} | {item['flights']:,} |")
    lines.extend(["", "## Source anomalies", "", "| Anomaly | Records |", "| --- | ---: |"])
    for name, count in summary["data_quality"]["anomalies"].items():
        lines.append(f"| {name} | {count:,} |")
    if not summary["data_quality"]["anomalies"]:
        lines.append("| None detected by implemented rules | 0 |")
    lines.extend(["", "## Validation errors", ""])
    lines.extend([f"- {error}" for error in summary["checks"]["errors"]] or ["- None."])
    lines.extend(["", "## Review warnings", ""])
    lines.extend([f"- {warning}" for warning in summary["checks"]["warnings"]] or ["- None."])
    lines.extend([
        "",
        "## Methodology and interpretation",
        "",
        "- Every record comes from a verified monthly ZIP published by BTS; the manifest stores SHA-256 hashes and ZIP CRC checks.",
        "- Missing numeric delay values are preserved, not imputed. Cancelled and diverted flights are excluded from the arrival-delay denominator.",
        "- Arrival delay >=15 minutes is computed from BTS `ArrDel15` for non-cancelled, non-diverted flights with a populated indicator.",
        "- Year-over-year comparisons describe reported flights, not every U.S. flight or all global aviation activity.",
        "- Candidate-key collisions and other anomalies are retained for investigation; this assessment does not silently deduplicate.",
        "- See `aggregate_profile.json` and all 24 month-level JSON profiles for exact machine-readable measures.",
        "",
    ])
    return "\n".join(lines)


def field_catalog(summary: dict) -> str:
    missingness = {item["name"]: item for item in summary["data_quality"]["column_missingness"]}
    lines = [
        "# BTS Source Field Catalog (2024-2025)",
        "",
        "All named fields observed in the monthly CSV header. Raw values are text; type names are proposed for Phase 2-3, not transformations performed in Phase 1.",
        "NULL percentages are weighted by actual flight rows across all 24 months.",
        "Consult the [official BTS field definitions](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ) for the complete authoritative semantics.",
        "",
        "| Field | Proposed type | NULL % | Role / interpretation |",
        "| --- | --- | ---: | --- |",
    ]
    for field in summary["schema"]["fields"]:
        proposed, description, _ = FIELD_NOTES.get(field, ("REVIEW", "Additional BTS source attribute; preserve raw value", ""))
        percentage = missingness[field]["null_pct"]
        lines.append(f"| `{field}` | {proposed} | {percentage:.6f}% | {description} |")
    lines.extend([
        "",
        "## Modeling conventions",
        "",
        "- Do not assume a source flight-number or airline-code field is globally unique.",
        "- Treat sparse cancellation, diversion and delay-cause fields as conditional attributes.",
        "- Preserve source values until transformations, numeric casts and timestamp rules have been tested.",
        "- Phase 2 should explicitly type the remaining `REVIEW` fields that will enter the curated schema; not every raw column belongs in the star schema.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("docs/phase1/2024_2025/acquisition_manifest.json"))
    parser.add_argument("--profiles", type=Path, default=Path("docs/phase1/2024_2025/profiles"))
    parser.add_argument("--output", type=Path, default=Path("docs/phase1/2024_2025/aggregate_profile.json"))
    parser.add_argument("--report", type=Path, default=Path("docs/phase1/2024_2025/data_quality_assessment.md"))
    parser.add_argument("--catalog", type=Path, default=Path("docs/phase1/2024_2025/field_catalog.md"))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    profiles = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in args.profiles.glob("????-??.json")}
    summary = summarize(manifest, profiles)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(markdown_report(summary), encoding="utf-8")
    args.catalog.write_text(field_catalog(summary), encoding="utf-8")
    print(f"{summary['period']['verified_months']}/24 months; {summary['overall']['scheduled_flights']:,} records; complete={summary['phase1_complete']}")
    if not summary["phase1_complete"]:
        for error in summary["checks"]["errors"]:
            print(f"ERROR: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
