"""Streaming quality profile of an official BTS monthly ZIP (Python stdlib only).

Output is a reproducible assessment, not a curated/cleaned dataset.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

SOURCE_URL_TEMPLATE = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)

REQUIRED_COLUMNS = (
    "FlightDate", "Reporting_Airline", "DOT_ID_Reporting_Airline",
    "Flight_Number_Reporting_Airline", "Origin", "Dest", "OriginAirportID",
    "DestAirportID", "CRSDepTime", "CRSArrTime", "DepDelay", "ArrDelay",
    "ArrDel15", "Cancelled", "Diverted",
)

BUSINESS_KEY_COLUMNS = (
    "FlightDate", "DOT_ID_Reporting_Airline",
    "Flight_Number_Reporting_Airline", "OriginAirportID", "DestAirportID",
    "CRSDepTime",
)
EXTENDED_KEY_COLUMNS = (*BUSINESS_KEY_COLUMNS, "CRSArrTime")
STATUS_FIELDS = ("Cancelled", "Diverted", "ArrDel15")


def missing(value: str | None) -> bool:
    return value is None or not value.strip()


def parse_flag(value: str | None) -> int | None:
    if missing(value):
        return None
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return int(result) if result in (0.0, 1.0) else None


def parse_flight_date(value: str | None) -> date | None:
    if missing(value):
        return None
    try:
        return date.fromisoformat(value) if "-" in value else datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def is_valid_hhmm(value: str | None) -> bool:
    """Validate local HHMM clock text, retaining `2400` as a boundary case."""
    if missing(value) or not value.isascii() or not value.isdigit() or len(value) > 4:
        return False
    number = int(value)
    if number == 2400:
        return True
    return number < 2400 and number % 100 < 60


def make_key(row: dict[str, str], fields: tuple[str, ...]) -> bytes | None:
    values = [row.get(field, "") for field in fields]
    if any(missing(value) for value in values):
        return None
    payload = json.dumps(values, ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).digest()


def profile(source_zip: Path, expected_month: str | None = None) -> dict:
    if not source_zip.is_file():
        raise FileNotFoundError(f"BTS ZIP not found: {source_zip}")
    if expected_month is not None and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", expected_month):
        raise ValueError("Expected month must have YYYY-MM format")

    zip_hash = hashlib.sha256()
    with source_zip.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            zip_hash.update(block)

    source_size = source_zip.stat().st_size
    with zipfile.ZipFile(source_zip) as archive:
        candidates = [item for item in archive.infolist() if item.filename.lower().endswith(".csv")]
        if len(candidates) != 1:
            raise ValueError(f"Expected one monthly CSV in ZIP, found {len(candidates)}")
        csv_member = candidates[0]
        with archive.open(csv_member) as binary:
            reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig", newline=""))
            original_fields = list(reader.fieldnames or [])
            blank_header_fields = [idx for idx, name in enumerate(original_fields) if missing(name)]
            columns = [name for name in original_fields if not missing(name)]
            missing_required = [name for name in REQUIRED_COLUMNS if name not in columns]
            if missing_required:
                raise ValueError(f"Required BTS columns absent: {missing_required}")

            nulls: Counter[str] = Counter()
            origin_counter: Counter[str] = Counter()
            destination_counter: Counter[str] = Counter()
            airline_counter: Counter[str] = Counter()
            route_counter: Counter[str] = Counter()
            daily_counter: Counter[str] = Counter()
            statuses: Counter[str] = Counter()
            anomalies: Counter[str] = Counter()
            flight_dates: set[str] = set()
            unique_origins: set[str] = set()
            unique_destinations: set[str] = set()
            unique_airlines: set[str] = set()
            seen_key: set[bytes] = set()
            seen_extended_key: set[bytes] = set()
            seen_row: set[bytes] = set()
            duplicate_examples: list[dict] = []
            row_count = 0
            min_date: date | None = None
            max_date: date | None = None
            valid_arrival_denominator = 0
            arrival_on_time_count = 0
            arrival_delay15_count = 0
            valid_dep_delay_count = 0
            sum_positive_arrival_delay = 0.0
            invalid_date_count = 0

            for row in reader:
                row_count += 1
                if None in row:
                    anomalies["csv_extra_fields"] += 1

                for time_field in ("CRSDepTime", "CRSArrTime", "DepTime", "ArrTime"):
                    val = row.get(time_field)
                    if not missing(val):
                        if not is_valid_hhmm(val):
                            anomalies[f"invalid_{time_field}_hhmm"] += 1
                        elif int(val) == 2400:
                            anomalies[f"{time_field}_2400_boundary"] += 1

                flight_weight = row.get("Flights")
                if flight_weight is not None and not missing(flight_weight):
                    try:
                        if float(flight_weight) != 1.0:
                            anomalies["flight_weight_not_one"] += 1
                    except ValueError:
                        anomalies["invalid_flight_weight"] += 1

                # BTS ZIP carries a final unnamed, empty CSV header. Keep track
                # of its presence but exclude it from the intended schema.
                for column in columns:
                    if missing(row.get(column)):
                        nulls[column] += 1

                flight_date = parse_flight_date(row.get("FlightDate"))
                if flight_date is None:
                    invalid_date_count += 1
                else:
                    min_date = min(min_date, flight_date) if min_date else flight_date
                    max_date = max(max_date, flight_date) if max_date else flight_date
                    flight_dates.add(flight_date.isoformat())
                    daily_counter[flight_date.isoformat()] += 1
                    if expected_month and flight_date.strftime("%Y-%m") != expected_month:
                        anomalies["outside_expected_month"] += 1

                for name, counter, distinct in (
                    ("Origin", origin_counter, unique_origins),
                    ("Dest", destination_counter, unique_destinations),
                    ("Reporting_Airline", airline_counter, unique_airlines),
                ):
                    val = (row.get(name) or "").strip()
                    if val:
                        counter[val] += 1
                        distinct.add(val)
                origin = (row.get("Origin") or "").strip()
                destination = (row.get("Dest") or "").strip()
                if origin and destination:
                    route_counter[f"{origin}|{destination}"] += 1

                cancelled = parse_flag(row.get("Cancelled"))
                diverted = parse_flag(row.get("Diverted"))
                arrdel15 = parse_flag(row.get("ArrDel15"))
                arrdelay = row.get("ArrDelay")
                depdelay = row.get("DepDelay")
                for field, value in (("Cancelled", cancelled), ("Diverted", diverted), ("ArrDel15", arrdel15)):
                    if not missing(row.get(field)) and value is None:
                        anomalies[f"invalid_{field}_indicator"] += 1

                if cancelled == 1:
                    statuses["cancelled"] += 1
                    if not missing(arrdelay):
                        anomalies["cancelled_with_arrival_delay"] += 1
                elif diverted == 1:
                    statuses["diverted_not_cancelled"] += 1
                    if not missing(arrdelay):
                        anomalies["diverted_with_arrival_delay"] += 1
                elif cancelled == 0 and diverted == 0:
                    statuses["completed"] += 1
                    if arrdel15 is None:
                        anomalies["completed_missing_arrdel15"] += 1
                    else:
                        valid_arrival_denominator += 1
                        if arrdel15 == 0:
                            arrival_on_time_count += 1
                        else:
                            arrival_delay15_count += 1

                if cancelled == 1 and diverted == 1:
                    anomalies["cancelled_and_diverted"] += 1
                if not missing(depdelay):
                    valid_dep_delay_count += 1

                if not missing(arrdelay):
                    try:
                        delay = float(arrdelay)
                        sum_positive_arrival_delay += max(0.0, delay)
                        if arrdel15 is not None and (delay >= 15) != (arrdel15 == 1):
                            anomalies["arrdel15_vs_arrdelay_mismatch"] += 1
                    except ValueError:
                        anomalies["invalid_arrdelay_numeric"] += 1

                natural_key = make_key(row, BUSINESS_KEY_COLUMNS)
                if natural_key is None:
                    anomalies["missing_business_key_component"] += 1
                elif natural_key in seen_key:
                    anomalies["duplicate_candidate_business_key"] += 1
                    if len(duplicate_examples) < 5:
                        duplicate_examples.append({field: row.get(field) for field in BUSINESS_KEY_COLUMNS})
                else:
                    seen_key.add(natural_key)

                extended_key = make_key(row, EXTENDED_KEY_COLUMNS)
                if extended_key is None:
                    anomalies["missing_extended_key_component"] += 1
                elif extended_key in seen_extended_key:
                    anomalies["duplicate_extended_key"] += 1
                else:
                    seen_extended_key.add(extended_key)

                # Exact observed fields only; avoid the trailing empty header.
                row_hash = make_key(row, tuple(columns))
                if row_hash is None:
                    # Most BTS rows contain legitimate NULLs; hash the full row
                    # anyway to detect identical records.
                    raw = json.dumps([row.get(field) for field in columns], separators=(",", ":")).encode()
                    row_hash = hashlib.sha256(raw).digest()
                if row_hash in seen_row:
                    anomalies["exact_duplicate_row"] += 1
                else:
                    seen_row.add(row_hash)

            if row_count == 0:
                raise ValueError("CSV contains no data records")

    denominator = valid_arrival_denominator
    output = {
        "profile_version": "1.0",
        "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "publisher": "US Department of Transportation, Bureau of Transportation Statistics",
            "dataset": "Reporting Carrier On-Time Performance (1987-present)",
            "source_url": SOURCE_URL_TEMPLATE.format(year=(expected_month or "2025-01")[:4], month=int((expected_month or "2025-01")[5:])),
            "zip_filename": source_zip.name,
            "zip_sha256": zip_hash.hexdigest(),
            "zip_bytes": source_size,
            "csv_member": csv_member.filename,
            "csv_uncompressed_bytes": csv_member.file_size,
        },
        "dataset": {
            "rows": row_count,
            "original_csv_headers": len(original_fields),
            "named_columns": len(columns),
            "empty_header_positions": blank_header_fields,
            "missing_required_columns": missing_required,
            "date_min": min_date.isoformat() if min_date else None,
            "date_max": max_date.isoformat() if max_date else None,
            "invalid_flight_date_count": invalid_date_count,
            "distinct_flight_dates": len(flight_dates),
            "distinct_origin_airports": len(unique_origins),
            "distinct_destination_airports": len(unique_destinations),
            "distinct_reporting_airlines": len(unique_airlines),
            "status_counts": dict(statuses),
        },
        "columns": [
            {"name": name, "null_count": nulls[name], "null_pct": round(100 * nulls[name] / row_count, 4)}
            for name in columns
        ],
        "business_key": {
            "candidate_columns": list(BUSINESS_KEY_COLUMNS),
            "extended_columns": list(EXTENDED_KEY_COLUMNS),
            "distinct_candidate_keys": len(seen_key),
            "distinct_extended_keys": len(seen_extended_key),
            "distinct_exact_rows": len(seen_row),
            "duplicate_candidate_examples": duplicate_examples,
            "note": "Candidate natural key is not assumed to be unique; recheck during Phase 2.",
        },
        "kpis": {
            "scheduled_flights": row_count,
            "completed_flights": statuses["completed"],
            "cancelled_flights": statuses["cancelled"],
            "diverted_not_cancelled_flights": statuses["diverted_not_cancelled"],
            "arrival_delay15_eligible_flights": denominator,
            "on_time_arrivals": arrival_on_time_count,
            "arrival_delayed_15min": arrival_delay15_count,
            "arrival_on_time_pct": round(100 * arrival_on_time_count / denominator, 4) if denominator else None,
            "arrival_delay15_pct": round(100 * arrival_delay15_count / denominator, 4) if denominator else None,
            "cancellation_pct_of_scheduled": round(100 * statuses["cancelled"] / row_count, 4),
            "diversion_pct_of_scheduled": round(100 * statuses["diverted_not_cancelled"] / row_count, 4),
            "populated_depdelay_rows": valid_dep_delay_count,
            "sum_positive_arrival_delay_minutes": round(sum_positive_arrival_delay, 2),
        },
        "anomalies": dict(sorted(anomalies.items())),
        "top_origin_airports": [
            {"airport": name, "flights": count}
            for name, count in origin_counter.most_common(30)
        ],
        "top_destination_airports": [
            {"airport": name, "flights": count}
            for name, count in destination_counter.most_common(20)
        ],
        "top_reporting_airlines": [
            {"airline": name, "flights": count}
            for name, count in airline_counter.most_common(30)
        ],
        "origin_counts": dict(sorted(origin_counter.items())),
        "destination_counts": dict(sorted(destination_counter.items())),
        "reporting_airline_counts": dict(sorted(airline_counter.items())),
        "route_counts": dict(sorted(route_counter.items())),
        "daily_counts": dict(sorted(daily_counter.items())),
    }
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True, help="BTS monthly pre-zipped file")
    parser.add_argument("--output", type=Path, required=True, help="Full-quality-report JSON")
    parser.add_argument("--expected-month", help="YYYY-MM, validates FlightDate coverage")
    args = parser.parse_args()

    result = profile(args.zip, args.expected_month)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Profiled {result['dataset']['rows']:,} records / {result['dataset']['named_columns']} named columns")
    print(f"Output: {args.output}")
    print(f"Anomalies: {result['anomalies']}")


if __name__ == "__main__":
    main()
