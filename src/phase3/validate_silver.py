"""Reconcile all physical PostgreSQL Silver rows with the Bronze manifest."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from .config import PROJECT_ROOT, read_env
from .load_silver import MANIFEST_PATH, connect


def reconcile(connection, manifest: dict) -> dict:
    records = manifest["partitions"]
    observed = connection.execute(
        """
        SELECT source_month, COUNT(*), MIN(source_row_number), MAX(source_row_number),
               MIN(source_sha256), MAX(source_sha256),
               MIN(source_file), MAX(source_file)
        FROM silver.flights
        GROUP BY source_month
        ORDER BY source_month
        """
    ).fetchall()
    by_month = {row[0].strftime("%Y-%m"): row for row in observed}
    audit = {
        row[0].strftime("%Y-%m"): row
        for row in connection.execute(
            "SELECT source_month, source_sha256, parquet_sha256, "
            "bronze_row_count, silver_row_count "
            "FROM audit.silver_loads ORDER BY source_month"
        ).fetchall()
    }
    findings: list[dict] = []
    expected_total = 0
    actual_total = 0
    for month in sorted(records):
        item = records[month]
        expected = item["bronze_row_count"]
        expected_total += expected
        row = by_month.get(month)
        count = row[1] if row else 0
        actual_total += count
        issues: list[str] = []
        if item.get("status") != "completed":
            issues.append("bronze_not_completed")
        if count != expected:
            issues.append("row_count_mismatch")
        if row:
            if row[2] != 1 or row[3] != expected:
                issues.append("source_row_number_range_mismatch")
            if row[4] != item["source_sha256"] or row[5] != item["source_sha256"]:
                issues.append("source_sha256_mismatch")
            if row[6] != item["source_file"] or row[7] != item["source_file"]:
                issues.append("source_file_mismatch")
        audit_row = audit.get(month)
        if audit_row is None or audit_row[1:] != (
            item["source_sha256"],
            item["parquet_sha256"],
            expected,
            expected,
        ):
            issues.append("load_audit_mismatch")
        findings.append({
            "month": month,
            "bronze_rows": expected,
            "silver_rows": count,
            "status": "pass" if not issues else "fail",
            "issues": issues,
        })
    extra = sorted((set(by_month) | set(audit)) - set(records))
    all_passed = (
        len(records) == 24
        and set(records) == {
            f"{year}-{month:02d}" for year in (2024, 2025) for month in range(1, 13)
        }
        and not extra
        and expected_total == actual_total
        and all(item["status"] == "pass" for item in findings)
    )
    return {
        "status": "pass" if all_passed else "fail",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "period": "2024-01 to 2025-12",
        "expected_months": 24,
        "actual_months": len(by_month),
        "bronze_rows": expected_total,
        "silver_rows": actual_total,
        "unexpected_months": extra,
        "monthly": findings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Optional JSON report location")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    settings = read_env(PROJECT_ROOT / ".env")
    with connect(settings) as connection:
        report = reconcile(connection, manifest)
    if args.report:
        destination = args.report if args.report.is_absolute() else PROJECT_ROOT / args.report
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(
        {key: value for key, value in report.items() if key != "monthly"},
        indent=2,
    ))
    if report["status"] != "pass":
        raise SystemExit("Silver reconciliation failed; inspect the monthly report")


if __name__ == "__main__":
    main()
