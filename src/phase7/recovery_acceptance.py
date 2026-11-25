"""Opt-in failure drills against the M7.3 isolated warehouse, never the main one."""

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.phase3.config import read_env
from src.phase7.pipeline import MANIFEST, ROOT, PipelineRunner, verify_source

ISOLATED = ROOT / "data/tmp/m73-isolated"
RECOVERY = ROOT / "data/tmp/m74-recovery"
MONTH = "2024-01"


def isolated_settings():
    settings = read_env(ISOLATED / ".env")
    if (settings["POSTGRES_DB"], settings["POSTGRES_PORT"]) != ("flight_m73_test", "5543"):
        raise RuntimeError("Refusing recovery drill outside isolated M7.3 database")
    return settings


def snapshot(conn):
    rows = conn.execute(
        "select source_month, count(*), sum(hashtextextended(row(f.*)::text,0)::numeric) "
        "from silver.flights f group by source_month order by source_month"
    ).fetchall()
    audit = conn.execute("select * from audit.silver_loads order by source_month").fetchall()
    return rows, audit


def rollback_probe():
    import psycopg

    from src.phase3 import load_silver

    settings = isolated_settings()
    manifest = ISOLATED / "data/bronze/_metadata/ingestion_manifest.json"
    record = json.loads(manifest.read_text(encoding="utf-8"))["partitions"][MONTH]
    part = load_silver.inspect_partition(MONTH, record, ISOLATED / "data/bronze")
    with load_silver.connect(settings) as conn:
        assert conn.execute("select current_database()").fetchone()[0] == "flight_m73_test"
        before = snapshot(conn)
        assert sum(r[1] for r in before[0]) == 1066492
        original = load_silver.batch_to_csv
        calls = 0

        def fail_second_batch(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("M7.4 injected failure after first COPY batch")
            return original(*args)

        with patch.object(load_silver, "batch_to_csv", fail_second_batch):
            try:
                load_silver.load_month(conn, part, reprocess=True, batch_size=50000)
            except RuntimeError as exc:
                if "M7.4 injected failure" not in str(exc):
                    raise
            else:
                raise AssertionError("Expected injected failure")
        assert calls == 2
        assert conn.info.transaction_status == psycopg.pq.TransactionStatus.IDLE
        assert snapshot(conn) == before, "Rollback failed to restore data and audit"
        result = load_silver.load_month(conn, part)
        assert result["status"] == "skipped" and result["rows"] == 547271
        print(json.dumps({"rollback": "PASS", "batches_attempted": calls,
                          "rows_preserved": 1066492, "rerun": result}), flush=True)


def run_month(runner, instance, expected, label):
    from dagster import DagsterEventType, ResourceDefinition

    from src.phase7.definitions import defs

    result = defs.resolve_job_def("ingest_flight_month").execute_in_process(
        partition_key=MONTH, instance=instance,
        resources={"pipeline": ResourceDefinition.hardcoded_resource(runner)},
        raise_on_error=False, tags={"acceptance": "M7.4", "drill": label},
    )
    events = instance.all_logs(result.run_id)
    steps = [e.step_key for e in events if e.dagster_event_type == DagsterEventType.STEP_SUCCESS]
    retries = [e.step_key for e in events if e.dagster_event_type == DagsterEventType.STEP_UP_FOR_RETRY]
    failures = [e.step_key for e in events if e.dagster_event_type == DagsterEventType.STEP_FAILURE]
    print(json.dumps({"label": label, "run_id": result.run_id, "success": result.success,
                      "steps": steps, "retries": retries, "failures": failures}), flush=True)
    assert result.success == expected
    return steps, retries, failures


def source_probe():
    from dagster import DagsterInstance

    isolated_settings()
    RECOVERY.mkdir(parents=True, exist_ok=True)
    home = RECOVERY / "dagster-home"
    home.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "orchestration/dagster.yaml", home / "dagster.yaml")
    python = ROOT / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
    records = json.loads((ISOLATED / MANIFEST).read_text(encoding="utf-8"))["files"]
    record = next(r for r in records if r["month"] == MONTH)
    source = ISOLATED / record["relative_path"]
    good_hash = verify_source(MONTH, ISOLATED)["source_sha256"]

    with tempfile.TemporaryDirectory(prefix="source-", dir=RECOVERY) as tmp:
        root = Path(tmp)
        (root / MANIFEST).parent.mkdir(parents=True)
        shutil.copyfile(ISOLATED / MANIFEST, root / MANIFEST)
        bad = root / record["relative_path"]
        bad.parent.mkdir(parents=True)
        shutil.copyfile(source, bad)
        with bad.open("r+b") as stream:
            first = stream.read(1)
            stream.seek(0)
            stream.write(bytes([first[0] ^ 1]))

        class FaultRunner(PipelineRunner):
            def verify(self, month):
                return verify_source(month, root)

        with DagsterInstance.from_config(str(home)) as instance:
            fault = FaultRunner(ISOLATED, python)
            steps, retries, failures = run_month(fault, instance, False, "corrupt_source")
            assert steps == [] and retries == ["bts_source"] and failures == ["bts_source"]
            shutil.copyfile(source, bad)
            steps, retries, failures = run_month(fault, instance, True, "restored_source")
            assert steps == ["bts_source", "bronze_flights", "silver_flights"]
            assert not retries and not failures

    with source.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == good_hash


def database_probe(expect_failure):
    from dagster import DagsterInstance

    isolated_settings()
    home = RECOVERY / "dagster-home"
    if not home.is_dir():
        raise RuntimeError("Run source drill first")
    python = ROOT / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
    runner = PipelineRunner(ISOLATED, python)
    label = "database_unavailable" if expect_failure else "database_restored"
    with DagsterInstance.from_config(str(home)) as instance:
        steps, retries, failures = run_month(runner, instance, not expect_failure, label)
        assert not retries
        if expect_failure:
            assert steps == ["bts_source", "bronze_flights"] and failures == ["silver_flights"]
        else:
            assert steps == ["bts_source", "bronze_flights", "silver_flights"] and not failures


if __name__ == "__main__":
    modes = {"source": source_probe, "rollback": rollback_probe,
             "database-offline": lambda: database_probe(True),
             "database-restored": lambda: database_probe(False)}
    if len(sys.argv) != 2 or sys.argv[1] not in modes:
        raise SystemExit("Choose source, rollback, database-offline or database-restored")
    modes[sys.argv[1]]()
