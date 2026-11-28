"""Compare source-month indexes only in the full isolated acceptance database."""

import argparse
import json
import time
from datetime import datetime, timezone

from src.phase3.config import PROJECT_ROOT
from src.phase7.gold_acceptance import acceptance_settings
from src.phase8.benchmark import (
    EXPECTED_ROWS,
    execution_order,
    require_equal,
    sample,
    summarize,
)

CANDIDATES = {
    "brin": ("m82_probe_month_brin",
             "CREATE INDEX m82_probe_month_brin ON gold.fct_flights USING brin (source_month)"),
    "btree": ("m82_probe_month_btree",
              "CREATE INDEX m82_probe_month_btree ON gold.fct_flights USING btree (source_month)"),
}
ORIGIN = 1013930
QUERIES = {
    "single_month": (
        """select sum(scheduled_flight_count)::bigint, sum(eligible_arrival_count)::bigint,
        sum(arrival_delayed_15_count)::bigint from gold.fct_flights
        where source_month=date '2025-12-01'""",
        """select scheduled_flights, eligible_arrivals, late_arrivals_15
        from gold.mart_network_monthly where source_month=date '2025-12-01'""",
    ),
    "origin_month": (
        """select sum(scheduled_flight_count)::bigint, sum(eligible_arrival_count)::bigint,
        sum(arrival_delayed_15_count)::bigint from gold.fct_flights
        where source_month=date '2025-12-01' and origin_airport_sk=1013930""",
        """select sum(scheduled_flights)::bigint, sum(eligible_arrivals)::bigint,
        sum(late_arrivals_15)::bigint from gold.mart_route_monthly
        where source_month=date '2025-12-01' and origin_airport_sk=1013930""",
    ),
    "full_year": (
        """select sum(scheduled_flight_count)::bigint, sum(eligible_arrival_count)::bigint,
        sum(arrival_delayed_15_count)::bigint from gold.fct_flights
        where source_month>=date '2025-01-01' and source_month<date '2026-01-01'""",
        """select sum(scheduled_flights)::bigint, sum(eligible_arrivals)::bigint,
        sum(late_arrivals_15)::bigint from gold.mart_network_monthly
        where source_month>=date '2025-01-01' and source_month<date '2026-01-01'""",
    ),
}


def require_target(settings):
    if (settings.get("POSTGRES_DB"), settings.get("POSTGRES_PORT")) != (
        "flight_m75_acceptance", "5543"
    ):
        raise RuntimeError("Only the isolated full acceptance database is allowed")


def index_inventory(conn):
    return conn.execute(
        """select indexname,indexdef from pg_indexes
        where schemaname='gold' and tablename='fct_flights' order by 1"""
    ).fetchall()


def index_names(node):
    names = [node["Index Name"]] if "Index Name" in node else []
    return names + [name for child in node.get("Plans", []) for name in index_names(child)]


def measure(conn, expected, repetitions):
    samples = {name: [] for name in QUERIES}
    plans = {name: [] for name in QUERIES}
    for name, (query, _) in QUERIES.items():
        require_equal(conn.execute(query).fetchall(), expected[name], name)
    # Reverse query order on alternating rounds to reduce ordering bias.
    names = list(QUERIES)
    for i in range(repetitions):
        for name in names if i % 2 == 0 else reversed(names):
            plan = conn.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " +
                                QUERIES[name][0]).fetchone()[0][0]
            observed = sample(plan)
            observed["indexes_used"] = sorted(set(index_names(plan["Plan"])))
            samples[name].append(observed)
            plans[name].append(plan)
    return {name: summarize(values) for name, values in samples.items()}, plans


def run(repetitions=3):
    import psycopg

    execution_order(repetitions)
    settings = acceptance_settings()
    require_target(settings)
    result = {"measured_at_utc": datetime.now(timezone.utc).isoformat(),
              "repetitions": repetitions, "warmup_per_query": 1, "origin_airport_sk": ORIGIN,
              "database": "flight_m75_acceptance", "stages": {}}
    plans = {}
    with psycopg.connect(host="127.0.0.1", port=5543, dbname=settings["POSTGRES_DB"],
                         user=settings["POSTGRES_USER"], password=settings["POSTGRES_PASSWORD"],
                         connect_timeout=10) as conn:
        try:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            conn.execute("SET LOCAL statement_timeout='300s'")
            conn.execute("SET LOCAL lock_timeout='5s'")
            if conn.execute("select current_database()").fetchone()[0] != "flight_m75_acceptance":
                raise RuntimeError("Wrong database")
            if conn.execute("""select count(*) from pg_stat_activity where datname=current_database()
                               and pid<>pg_backend_pid()""").fetchone()[0]:
                raise RuntimeError("Isolated database must be idle")
            audit = conn.execute("select count(*),sum(silver_row_count) from audit.silver_loads").fetchone()
            network = conn.execute("select count(*),sum(scheduled_flights) from gold.mart_network_monthly").fetchone()
            if audit != (24, EXPECTED_ROWS) or network != audit:
                raise RuntimeError("Unexpected data scope")
            original = index_inventory(conn)
            if len(original) != 3 or any("source_month" in definition for _, definition in original):
                raise RuntimeError("Expected original three fact indexes only")
            result["original_indexes"] = original
            result["postgres_version"] = conn.execute("show server_version").fetchone()[0]
            result["settings"] = {key: conn.execute("select current_setting(%s)", (key,)).fetchone()[0]
                                  for key in ("shared_buffers", "work_mem", "effective_cache_size",
                                              "max_parallel_workers_per_gather", "jit", "block_size")}
            result["source_month_correlation"] = conn.execute(
                """select correlation from pg_stats where schemaname='gold'
                and tablename='fct_flights' and attname='source_month'"""
            ).fetchone()[0]
            expected = {name: conn.execute(pair[1]).fetchall() for name, pair in QUERIES.items()}
            if any(len(rows) != 1 or not rows[0][0] for rows in expected.values()):
                raise RuntimeError("Empty expected results")
            result["matched_counts"] = {name: rows[0] for name, rows in expected.items()}

            def capture(stage, extra):
                measures, raw = measure(conn, expected, repetitions)
                result["stages"][stage] = {**extra, "queries": measures}
                plans[stage] = raw
                print(stage, {k: v["median_ms"] for k, v in measures.items()}, flush=True)

            capture("baseline", {})
            for stage, (name, ddl) in CANDIDATES.items():
                conn.execute("SAVEPOINT m82_candidate")
                try:
                    start = time.perf_counter()
                    conn.execute(ddl)
                    build_s = round(time.perf_counter() - start, 3)
                    size = conn.execute("select pg_relation_size(%s)", ("gold." + name,)).fetchone()[0]
                    print(stage, "build_s", build_s, "bytes", size, flush=True)
                    capture(stage, {"index_name": name, "build_seconds": build_s, "index_bytes": size})
                finally:
                    conn.execute("ROLLBACK TO SAVEPOINT m82_candidate")
                    conn.execute("RELEASE SAVEPOINT m82_candidate")
                if index_inventory(conn) != original:
                    raise RuntimeError("Candidate rollback did not restore index inventory")
            capture("baseline_after", {})
        finally:
            # Never commit any DDL, even if a candidate or measurement fails.
            conn.rollback()
        conn.execute("SET TRANSACTION READ ONLY")
        if index_inventory(conn) != original:
            raise RuntimeError("Final index inventory differs")
        result["original_indexes_restored"] = True
    return result, plans


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    result, plans = run(args.repetitions)
    output = PROJECT_ROOT / "data/tmp/phase8"
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    for name, data in (("index-results", result), ("index-plans", plans)):
        path = output / f"{name}-{stamp}.json"
        with path.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
