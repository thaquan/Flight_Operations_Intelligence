"""Read-only warehouse and Dagster health checks for the fixed historical scope."""

import argparse
import json
from datetime import datetime, timezone
from urllib.request import urlopen

from src.phase7.pipeline import MANIFEST, MONTHS, ROOT, verify_source

EXPECTED_ROWS = 14080680


def check(name, fn):
    try:
        status, detail = fn()
    except Exception as exc:
        # Never include raw exception messages, connection strings or credentials.
        status, detail = "FAIL", {"error_type": type(exc).__name__}
    return {"name": name, "status": status, "detail": detail}


def report(checks):
    status = "FAIL" if any(c["status"] == "FAIL" for c in checks) else (
        "REVIEW" if any(c["status"] == "REVIEW" for c in checks) else "PASS"
    )
    return {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": status, "checks": checks}


def source_check():
    entries = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))["files"]
    if sorted(e["month"] for e in entries) != sorted(MONTHS):
        return "FAIL", {"reason": "source_scope_mismatch"}
    for month in MONTHS:
        verify_source(month)
    return "PASS", {"verified_months": len(MONTHS)}


def bronze_check():
    from src.phase3.load_silver import MANIFEST_PATH, inspect_partition

    records = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["partitions"]
    if set(records) != set(MONTHS):
        return "FAIL", {"reason": "bronze_scope_mismatch"}
    rows = sum(inspect_partition(m, records[m]).row_count for m in MONTHS)
    return ("PASS" if rows == EXPECTED_ROWS else "FAIL",
            {"verified_months": len(records), "rows": rows})


def database_checks():
    import psycopg

    from src.phase3.config import read_env
    from src.phase3.load_silver import MANIFEST_PATH
    from src.phase3.validate_silver import reconcile
    from src.phase4.quality_gates import fetch_report

    settings = read_env(ROOT / ".env")
    with psycopg.connect(host="127.0.0.1", port=int(settings["POSTGRES_PORT"]),
                         dbname=settings["POSTGRES_DB"], user=settings["POSTGRES_USER"],
                         password=settings["POSTGRES_PASSWORD"], connect_timeout=10) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '300s'")
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        silver = reconcile(conn, manifest)
        counts = conn.execute(
            "select count(*), coalesce(sum(silver_row_count),0), max(loaded_at_utc) "
            "from audit.silver_loads"
        ).fetchone()
        gold = conn.execute("select count(*), coalesce(sum(scheduled_flights),0) "
                            "from gold.mart_network_monthly").fetchone()
        quality = fetch_report(conn, fixture=False)
        result = {
            "silver_reconciliation": silver["status"],
            "silver_months": silver["actual_months"], "silver_rows": silver["silver_rows"],
            "audit_months": counts[0], "audit_rows": int(counts[1]),
            "last_silver_load_utc": counts[2].isoformat() if counts[2] else None,
            "gold_months": gold[0], "gold_rows": int(gold[1]),
            "quality": quality["summary"], "quality_status": quality["status"],
        }
        passed = (silver["status"] == "pass" and silver["silver_rows"] == EXPECTED_ROWS
                  and counts[:2] == (24, EXPECTED_ROWS) and gold == (24, EXPECTED_ROWS)
                  and quality["summary"]["FAIL"] == 0)
        return (quality["status"] if passed else "FAIL"), result


def webserver_check():
    with urlopen("http://127.0.0.1:3000/", timeout=5) as response:
        return ("PASS" if response.status == 200 else "FAIL"), {"http": response.status}


def dagster_check():
    from dagster import DagsterInstance

    from src.phase7.definitions import weekly_audit
    from src.phase7.observability import summarize

    home = ROOT / "data/tmp/dagster-home"
    if not (home / "dagster.yaml").is_file():
        return "FAIL", {"reason": "instance_not_initialized"}
    with DagsterInstance.from_config(str(home)) as instance:
        daemons = {name: status.healthy for name, status in instance.get_daemon_statuses().items()
                   if status.required}
        states = [s.status.value for s in instance.all_instigator_state()
                  if s.name == weekly_audit.name]
        metrics = summarize(instance.get_run_records(), instance.all_logs)
        result = {"required_daemons": daemons,
                  "weekly_audit": states[0] if states else weekly_audit.default_status.value,
                  "partition_coverage": metrics["partition_coverage"],
                  "unexpected_failures": metrics["unexpected_failures"],
                  "last_success_utc": metrics["last_success_utc"]}
        passed = (bool(daemons) and all(v is True for v in daemons.values())
                  and metrics["partition_coverage"] == 24 and metrics["unexpected_failures"] == 0)
        return ("PASS" if passed else "FAIL"), result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", required=True, choices=["warehouse", "orchestration"])
    args = parser.parse_args()
    checks = ([check("source", source_check), check("bronze", bronze_check),
               check("warehouse", database_checks)] if args.component == "warehouse" else
              [check("webserver", webserver_check), check("dagster", dagster_check)])
    result = report(checks)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["status"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
