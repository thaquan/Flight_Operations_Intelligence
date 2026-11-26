import hashlib
import json
import sys
from pathlib import Path

import pytest

from src.phase7.pipeline import (
    MANIFEST,
    MONTHS,
    PipelineRunner,
    step_args,
    verify_source,
)


def test_partition_scope_and_commands():
    assert len(MONTHS) == 24
    assert MONTHS[0] == "2024-01" and MONTHS[-1] == "2025-12"
    assert step_args("bronze", "2024-01") == ("-m", "src.phase2.ingest", "--month", "2024-01")
    assert step_args("silver", "2025-12")[-2:] == ("--month", "2025-12")
    assert step_args("dbt_build")[-3:] == ("build", "--threads", "2")
    for step in ("bronze", "silver"):
        for invalid in (None, "2026-01", "2024-13", "--reprocess"):
            with pytest.raises(ValueError):
                step_args(step, invalid)
    with pytest.raises(ValueError):
        step_args("quality", "2024-01")
    with pytest.raises(ValueError):
        step_args("arbitrary")


def source_fixture(root):
    path = root / "data/raw/bts/2024/test.zip"
    path.parent.mkdir(parents=True)
    data = b"test fixture bytes"
    path.write_bytes(data)
    manifest = root / MANIFEST
    manifest.parent.mkdir(parents=True)
    record = {"month": "2024-01", "relative_path": path.relative_to(root).as_posix(),
              "zip_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    manifest.write_text(json.dumps({"files": [record]}), encoding="utf-8")
    return path, manifest, record


def test_source_integrity(tmp_path):
    path, _, record = source_fixture(tmp_path)
    assert verify_source("2024-01", tmp_path)["source_sha256"] == record["sha256"]
    path.write_bytes(b"x" * record["zip_bytes"])
    with pytest.raises(ValueError, match="checksum"):
        verify_source("2024-01", tmp_path)


def test_source_rejects_missing_duplicate_and_escaped_paths(tmp_path):
    _, manifest, record = source_fixture(tmp_path)
    manifest.write_text(json.dumps({"files": [record, record]}), encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one"):
        verify_source("2024-01", tmp_path)
    with pytest.raises(ValueError, match="exactly one"):
        verify_source("2024-02", tmp_path)
    record["relative_path"] = "../outside.zip"
    manifest.write_text(json.dumps({"files": [record]}), encoding="utf-8")
    with pytest.raises(ValueError, match="escapes"):
        verify_source("2024-01", tmp_path)


def test_runner_propagates_subprocess_exit(tmp_path, monkeypatch):
    import logging

    monkeypatch.setattr("src.phase7.pipeline.step_args", lambda *_: ("-c", "raise SystemExit(7)"))
    runner = PipelineRunner(tmp_path, Path(sys.executable))
    with pytest.raises(RuntimeError, match="code 7"):
        runner.run("quality", logging.getLogger("test"))


def test_runner_captures_success(tmp_path, monkeypatch, caplog):
    import logging

    monkeypatch.setattr("src.phase7.pipeline.step_args", lambda *_: ("-c", "print('pipeline result')"))
    with caplog.at_level(logging.INFO):
        result = PipelineRunner(tmp_path, Path(sys.executable)).run("quality", logging.getLogger("test"))
    assert result["exit_code"] == 0
    assert "pipeline result" in caplog.text


@pytest.fixture
def dagster_defs():
    dagster = pytest.importorskip("dagster")
    from src.phase7 import definitions

    return dagster, definitions


class FakeRunner:
    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail

    def verify(self, month):
        self.calls.append(("verify", month))
        return {"month": month}

    def run(self, step, log, month=None):
        self.calls.append((step, month))
        if step == self.fail:
            raise RuntimeError("simulated failed step")
        return {"step": step, "exit_code": 0}


def execute(dagster_defs, name, fake, partition=None):
    dagster, definitions = dagster_defs
    return definitions.defs.resolve_job_def(name).execute_in_process(
        partition_key=partition, resources={"pipeline": dagster.ResourceDefinition.hardcoded_resource(fake)},
        raise_on_error=False,
    )


def test_definitions_and_schedule(dagster_defs):
    dagster, definitions = dagster_defs
    dagster.Definitions.validate_loadable(definitions.defs)
    assert definitions.months.get_partition_keys() == list(MONTHS)
    assert definitions.weekly_audit.default_status == dagster.DefaultScheduleStatus.STOPPED
    assert definitions.weekly_audit.cron_schedule == "0 2 * * 1"


def test_monthly_ingestion_order(dagster_defs):
    fake = FakeRunner()
    result = execute(dagster_defs, "ingest_flight_month", fake, "2024-01")
    assert result.success
    assert fake.calls == [("verify", "2024-01"), ("bronze", "2024-01"), ("silver", "2024-01")]


def test_bronze_only(dagster_defs):
    fake = FakeRunner()
    assert execute(dagster_defs, "source_bronze_month", fake, "2025-12").success
    assert fake.calls == [("verify", "2025-12"), ("bronze", "2025-12")]


def test_bronze_failure_blocks_silver(dagster_defs):
    fake = FakeRunner("bronze")
    assert not execute(dagster_defs, "ingest_flight_month", fake, "2024-01").success
    assert fake.calls == [("verify", "2024-01"), ("bronze", "2024-01")]


def test_gold_preflight_and_quality_order(dagster_defs):
    fake = FakeRunner()
    assert execute(dagster_defs, "rebuild_gold_and_validate", fake).success
    assert fake.calls == [("silver_reconcile", None), ("dbt_build", None), ("quality", None)]


@pytest.mark.parametrize("failed,expected", [
    ("silver_reconcile", ["silver_reconcile"]),
    ("dbt_build", ["silver_reconcile", "dbt_build"]),
])
def test_failed_gold_blocks_quality(dagster_defs, failed, expected):
    fake = FakeRunner(failed)
    assert not execute(dagster_defs, "rebuild_gold_and_validate", fake).success
    assert fake.calls == [(step, None) for step in expected]


def test_audit_is_read_only(dagster_defs):
    fake = FakeRunner()
    assert execute(dagster_defs, "audit_job", fake).success
    assert fake.calls == [("quality", None)]


def test_recovery_refuses_main_database(monkeypatch):
    from src.phase7 import recovery_acceptance

    monkeypatch.setattr(recovery_acceptance, "read_env", lambda _: {
        "POSTGRES_DB": "flight_warehouse", "POSTGRES_PORT": "5433",
    })
    with pytest.raises(RuntimeError, match="isolated"):
        recovery_acceptance.isolated_settings()


def test_schedule_probe_is_separate_and_stopped(dagster_defs, monkeypatch, tmp_path):
    dagster, definitions = dagster_defs
    from src.phase7 import schedule_probe

    dagster.Definitions.validate_loadable(schedule_probe.defs)
    assert schedule_probe.probe_schedule.default_status == dagster.DefaultScheduleStatus.STOPPED
    assert schedule_probe.probe_schedule.cron_schedule == "* * * * *"
    assert definitions.weekly_audit.default_status == dagster.DefaultScheduleStatus.STOPPED
    assert definitions.weekly_audit.cron_schedule == "0 2 * * 1"
    monkeypatch.setenv("DAGSTER_HOME", str(tmp_path))
    result = schedule_probe.scheduled_source_probe.execute_in_process(raise_on_error=False)
    assert not result.success


def test_observability_distinguishes_history_and_row_events():
    from types import SimpleNamespace as NS

    from src.phase7.observability import summarize

    def record(rid, status, tags):
        return NS(dagster_run=NS(run_id=rid, status=NS(value=status),
                                 job_name="ingest_flight_month", tags=tags),
                  start_time=100, end_time=110)

    def event(step, kind, message=""):
        return NS(step_key=step, dagster_event_type=NS(value=kind), message=message)

    month = {"dagster/partition": "2024-01"}
    good = record("good", "SUCCESS", month)
    failed = record("fault", "FAILURE", {**month, "acceptance": "M7.4", "drill": "corrupt_source"})
    log = event("bronze_flights", None, '{"month":"2024-01","rows":5,"status":"skipped"}')
    logs = {"good": [log, log, event("bronze_flights", "STEP_SUCCESS")],
            "fault": [event("bts_source", "STEP_UP_FOR_RETRY"),
                      event("bts_source", "STEP_FAILURE"), log]}
    result = summarize([good, failed], logs.__getitem__)
    assert result["success_rate"] == 0.5
    assert result["expected_test_failures"] == 1
    assert result["unexpected_failures"] == 0
    assert result["partition_coverage"] == 1
    assert result["row_events_by_layer"]["bronze_flights"] == {"skipped": 5}
    assert result["row_events_by_layer"]["silver_flights"] == {}
    assert result["retry_events"] == 1


def test_empty_observability_has_no_invented_rates():
    from src.phase7.observability import summarize

    result = summarize([], lambda _: [])
    assert result["total_runs"] == 0
    assert result["success_rate"] is None
    assert result["last_success_utc"] is None
    assert result["duration_seconds"]["median"] is None


def test_health_status_preserves_review_and_failure():
    from src.phase7.health_check import check, report

    good = check("good", lambda: ("PASS", {}))
    review = check("quality", lambda: ("REVIEW", {"FAIL": 0}))
    assert report([good, review])["status"] == "REVIEW"

    def broken():
        raise RuntimeError("private connection detail")

    failed = check("database", broken)
    assert failed == {"name": "database", "status": "FAIL",
                      "detail": {"error_type": "RuntimeError"}}
    assert report([good, failed])["status"] == "FAIL"


def test_health_source_rejects_incomplete_manifest(tmp_path, monkeypatch):
    from src.phase7 import health_check

    manifest = tmp_path / health_check.MANIFEST
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"files": [{"month": "2024-01"}]}', encoding="utf-8")
    monkeypatch.setattr(health_check, "ROOT", tmp_path)
    assert health_check.source_check()[0] == "FAIL"


def test_gold_acceptance_refuses_main_and_m73(monkeypatch):
    from src.phase7 import gold_acceptance

    for name, port in [("flight_warehouse", "5433"), ("flight_m73_test", "5543"),
                       ("flight_m75_acceptance", "5433")]:
        monkeypatch.setattr(gold_acceptance, "read_env", lambda _, n=name, p=port: {
            "POSTGRES_DB": n, "POSTGRES_PORT": p,
        })
        with pytest.raises(RuntimeError, match="dedicated snapshot"):
            gold_acceptance.acceptance_settings()
