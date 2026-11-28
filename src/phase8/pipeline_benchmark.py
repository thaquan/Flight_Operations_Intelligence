"""Profile bounded Parquet reads and real Silver replacement on the isolated database."""

import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from src.phase3 import load_silver
from src.phase3.config import PROJECT_ROOT
from src.phase7.recovery_acceptance import ISOLATED, isolated_settings, snapshot

MONTH = "2024-01"
BATCHES = (25000, 50000, 100000)
EXPECTED = 547271
TOTAL = 1066492


def require_target(settings):
    if (settings.get("POSTGRES_DB"), settings.get("POSTGRES_PORT")) != ("flight_m73_test", "5543"):
        raise RuntimeError("Pipeline benchmark requires the isolated two-month database")


def peak_rss_bytes():
    """OS lifetime peak resident/working-set memory for this fresh Python process."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                    "PagefileUsage", "PeakPagefileUsage",
                )
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        handle = ctypes.windll.kernel32.GetCurrentProcess
        handle.restype = wintypes.HANDLE
        get_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        get_info.restype = wintypes.BOOL
        if not get_info(handle(), ctypes.byref(counters), counters.cb):
            raise OSError("GetProcessMemoryInfo failed")
        return int(counters.PeakWorkingSetSize)
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def partition():
    manifest = ISOLATED / "data/bronze/_metadata/ingestion_manifest.json"
    records = json.loads(manifest.read_text(encoding="utf-8"))["partitions"]
    result = load_silver.inspect_partition(MONTH, records[MONTH], ISOLATED / "data/bronze")
    if result.row_count != EXPECTED:
        raise RuntimeError("Unexpected January partition population")
    return result


def verify_lineage(rows, row_sum, expected):
    if rows != expected or row_sum != expected * (expected + 1) // 2:
        raise RuntimeError("Parquet scan row count or lineage sum differs")


def read_sample(part, batch_size, columns):
    start = time.perf_counter()
    rows = row_sum = batches = 0
    parquet = pq.ParquetFile(part.path)
    for batch in parquet.iter_batches(batch_size=batch_size, columns=columns):
        rows += batch.num_rows
        row_sum += pc.sum(batch.column(batch.schema.get_field_index("source_row_number"))).as_py()
        batches += 1
    elapsed = time.perf_counter() - start
    verify_lineage(rows, row_sum, part.row_count)
    return {"seconds": round(elapsed, 6), "rows": rows, "batches": batches,
            "rows_per_second": round(rows / elapsed, 1)}


def scan_worker(batch_size, projection):
    part = partition()
    columns = list(load_silver.BRONZE_COLUMNS) if projection == "silver" else None
    read_sample(part, batch_size, columns)  # unmeasured warm-up
    samples = [read_sample(part, batch_size, columns) for _ in range(3)]
    return {"batch_size": batch_size, "projection": projection,
            "columns": len(columns) if columns else len(pq.ParquetFile(part.path).schema_arrow.names),
            "samples": samples, "median_seconds": round(statistics.median(s["seconds"] for s in samples), 6),
            "peak_process_bytes": peak_rss_bytes(), "arrow_peak_bytes": pa.default_memory_pool().max_memory()}


def check_connection(conn):
    if conn.execute("select current_database()").fetchone()[0] != "flight_m73_test":
        raise RuntimeError("Unexpected database")
    if conn.execute("select count(*) from pg_stat_activity where datname=current_database() "
                    "and pid<>pg_backend_pid() and backend_type='client backend'").fetchone()[0]:
        raise RuntimeError("Isolated database must be idle")
    if conn.execute("select count(*),sum(silver_row_count) from audit.silver_loads").fetchone() != (2, TOTAL):
        raise RuntimeError("Unexpected isolated database population")


def load_worker(batch_size):
    settings = isolated_settings()
    require_target(settings)
    part = partition()
    with load_silver.connect(settings) as conn:
        check_connection(conn)
        conn.execute("SET statement_timeout='300s'")
        conn.execute("SET lock_timeout='5s'")
        if not conn.execute("select pg_try_advisory_lock(%s)", (load_silver.LOCK_ID,)).fetchone()[0]:
            raise RuntimeError("Another Silver load holds the lock")
        original = load_silver.current_load(conn, part)
        if original != (part.source_sha256, part.parquet_sha256, EXPECTED, EXPECTED):
            raise RuntimeError("Expected the accepted January audit")
        with conn.transaction(force_rollback=True):
            start = time.perf_counter()
            outcome = load_silver.load_month(conn, part, reprocess=True, batch_size=batch_size)
            elapsed = time.perf_counter() - start
            if outcome["status"] != "reprocessed" or outcome["rows"] != EXPECTED:
                raise RuntimeError("Unexpected replacement result")
            if load_silver.current_load(conn, part) != original:
                raise RuntimeError("Replacement audit differs")
            measured = {"batch_size": batch_size, "rows": outcome["rows"],
                        "seconds": round(elapsed, 3),
                        "rows_per_second": round(EXPECTED / elapsed, 1),
                        "loader_seconds": outcome["elapsed_seconds"],
                        "peak_process_bytes": peak_rss_bytes(),
                        "arrow_peak_bytes": pa.default_memory_pool().max_memory()}
            rollback_start = time.perf_counter()
        measured["rollback_seconds"] = round(time.perf_counter() - rollback_start, 3)
        if load_silver.current_load(conn, part) != original or load_silver.physical_count(conn, part) != EXPECTED:
            raise RuntimeError("Rollback did not restore January")
        return measured


def fingerprint():
    settings = isolated_settings()
    require_target(settings)
    with load_silver.connect(settings) as conn:
        check_connection(conn)
        with conn.transaction():
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            conn.execute("SET LOCAL statement_timeout='300s'")
            result = snapshot(conn)
            if sum(r[1] for r in result[0]) != TOTAL:
                raise RuntimeError("Unexpected Silver population")
            return result


def child(mode, batch, projection="silver"):
    completed = subprocess.run(
        [sys.executable, "-m", "src.phase8.pipeline_benchmark", "--worker", mode,
         "--batch-size", str(batch), "--projection", projection],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=True, timeout=360,
    )
    return json.loads(completed.stdout)


def historical_dbt():
    path = PROJECT_ROOT / "data/tmp/m75-gold/dbt/target/run_results.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    nodes = [{"id": item["unique_id"], "status": item["status"],
              "seconds": round(item["execution_time"], 3)} for item in payload["results"]]
    if len(nodes) != 76 or any(n["status"] not in {"success", "pass"} for n in nodes):
        raise RuntimeError("Expected successful full Gold dbt artifact")
    return {"elapsed_seconds": round(payload["elapsed_time"], 3),
            "nodes": sorted(nodes, key=lambda n: n["seconds"], reverse=True)}


def run(checkpoint):
    result = {"measured_at_utc": datetime.now(timezone.utc).isoformat(),
              "month": MONTH, "rows": EXPECTED, "pyarrow_version": pa.__version__,
              "parquet_reads": [], "silver_replacements": [], "historical_dbt": historical_dbt()}
    before = fingerprint()
    checkpoint(result)
    try:
        for batch, projection in [(n, "silver") for n in BATCHES] + [(50000, "all")]:
            measured = child("scan", batch, projection)
            result["parquet_reads"].append(measured)
            checkpoint(result)
            print("SCAN", batch, projection, measured["median_seconds"], flush=True)
        for batch in BATCHES:
            measured = child("load", batch)
            result["silver_replacements"].append(measured)
            checkpoint(result)
            print("LOAD", batch, measured, flush=True)
    finally:
        if fingerprint() != before:
            raise RuntimeError("Isolated data or audit differs after the benchmark")
    result["isolated_fingerprint_restored"] = True
    checkpoint(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=["scan", "load"])
    parser.add_argument("--batch-size", type=int, choices=BATCHES, default=50000)
    parser.add_argument("--projection", choices=["silver", "all"], default="silver")
    args = parser.parse_args()
    if args.worker:
        result = (scan_worker(args.batch_size, args.projection) if args.worker == "scan"
                  else load_worker(args.batch_size))
        print(json.dumps(result))
        return
    root = PROJECT_ROOT / "data/tmp/phase8"
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = root / f"pipeline-results-{stamp}.json"
    def checkpoint(result):
        temp = path.with_suffix(".partial")
        temp.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        temp.replace(path)

    run(checkpoint)
    print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
