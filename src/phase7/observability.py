"""Summarize persisted Dagster run history without exposing raw logs or credentials."""

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from statistics import median

from src.phase7.pipeline import MONTHS, ROOT

SCOPES = {
    "main": "dagster-home",
    "isolated": "m73-isolated/dagster-home",
    "recovery": "m74-recovery/dagster-home",
    "scheduler": "m74-schedule/dagster-home",
    "gold_acceptance": "m75-gold/dagster-home",
}
TERMINAL = {"SUCCESS", "FAILURE", "CANCELED"}


def summarize(records, logs):
    status = Counter()
    by_job = {}
    coverage = set()
    latest_success = None
    durations = []
    retries = 0
    failure_steps = Counter()
    expected_failures = 0
    rows = {"bronze_flights": Counter(), "silver_flights": Counter()}
    for record in records:
        run = record.dagster_run
        state = run.status.value
        status[state] += 1
        by_job.setdefault(run.job_name, Counter())[state] += 1
        month = run.tags.get("dagster/partition")
        if state == "SUCCESS":
            if record.end_time is not None:
                latest_success = max(latest_success or record.end_time, record.end_time)
            if run.job_name == "ingest_flight_month" and month in MONTHS:
                coverage.add(month)
        if state in TERMINAL and record.start_time is not None and record.end_time is not None:
            duration = record.end_time - record.start_time
            if duration >= 0:
                durations.append(duration)
        if state == "FAILURE" and run.tags.get("acceptance") == "M7.4" and run.tags.get("drill") in {
            "corrupt_source", "database_unavailable"
        }:
            expected_failures += 1
        events = list(logs(run.run_id))
        successful_steps = set()
        for event in events:
            kind = getattr(event.dagster_event_type, "value", None)
            if kind == "STEP_SUCCESS":
                successful_steps.add(event.step_key)
            elif kind == "STEP_UP_FOR_RETRY":
                retries += 1
            elif kind == "STEP_FAILURE":
                failure_steps[event.step_key or "unknown"] += 1
        # Count only the last valid row summary per successful step, not duplicate log lines.
        outcomes = {}
        for event in events:
            if event.step_key not in rows or event.step_key not in successful_steps:
                continue
            try:
                data = json.loads(event.message)
            except (TypeError, ValueError):
                continue
            if not isinstance(data, dict):
                continue
            count, outcome = data.get("rows"), data.get("status")
            if (month in MONTHS and data.get("month") == month
                    and type(count) is int and count >= 0
                    and outcome in {"ingested", "loaded", "reprocessed", "skipped"}):
                outcomes[event.step_key] = (outcome, count)
        for step, (outcome, count) in outcomes.items():
            rows[step][outcome] += count
    finished = sum(status[k] for k in TERMINAL)
    return {
        "total_runs": sum(status.values()), "statuses": dict(status),
        "terminal_runs": finished,
        "success_rate": round(status["SUCCESS"] / finished, 4) if finished else None,
        "expected_test_failures": expected_failures,
        "unexpected_failures": status["FAILURE"] - expected_failures,
        "retry_events": retries, "failure_steps": dict(failure_steps),
        "duration_seconds": {
            "samples": len(durations),
            "median": round(median(durations), 3) if durations else None,
            "max": round(max(durations), 3) if durations else None,
        },
        "last_success_utc": datetime.fromtimestamp(latest_success, timezone.utc).isoformat()
        if latest_success is not None else None,
        "successful_monthly_partitions": sorted(coverage),
        "partition_coverage": len(coverage),
        "row_events_by_layer": {step: dict(counts) for step, counts in rows.items()},
        "jobs": {name: dict(counts) for name, counts in sorted(by_job.items())},
    }


def collect(scope):
    from dagster import DagsterInstance

    home = ROOT / "data/tmp" / SCOPES[scope]
    if not (home / "dagster.yaml").is_file():
        return {"available": False}
    with DagsterInstance.from_config(str(home)) as instance:
        result = summarize(instance.get_run_records(), instance.all_logs)
        result["backfills"] = [{"id": b.backfill_id, "status": b.status.value}
                               for b in instance.get_backfills()]
    return {"available": True, **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=["all", *SCOPES], default="all")
    args = parser.parse_args()
    scopes = SCOPES if args.scope == "all" else [args.scope]
    print(json.dumps({scope: collect(scope) for scope in scopes}, indent=2))


if __name__ == "__main__":
    main()
