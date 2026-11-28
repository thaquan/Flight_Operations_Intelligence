"""Repeatable, read-only query baseline for the accepted historical warehouse."""

import argparse
import json
import statistics
from datetime import datetime, timezone

from src.phase3.config import PROJECT_ROOT, read_env

EXPECTED_ROWS = 14080680
QUERIES = {
    "network_monthly": (
        """select source_month, sum(scheduled_flight_count)::bigint,
        sum(eligible_arrival_count)::bigint, sum(arrival_delayed_15_count)::bigint,
        sum(cancelled_flight_count)::bigint
        from gold.fct_flights group by 1 order by 1""",
        """select source_month, scheduled_flights, eligible_arrivals, late_arrivals_15,
        cancelled_flights from gold.mart_network_monthly order by 1""",
    ),
    "airline_2025": (
        """select airline_sk, sum(scheduled_flight_count)::bigint,
        sum(eligible_arrival_count)::bigint, sum(arrival_delayed_15_count)::bigint
        from gold.fct_flights where source_month >= date '2025-01-01'
        and source_month < date '2026-01-01' group by 1 order by 1""",
        """select airline_sk, sum(scheduled_flights)::bigint,
        sum(eligible_arrivals)::bigint, sum(late_arrivals_15)::bigint
        from gold.mart_airline_monthly where source_month >= date '2025-01-01'
        and source_month < date '2026-01-01' group by 1 order by 1""",
    ),
    "top_origin_20": (
        """select origin_airport_sk, sum(scheduled_flight_count)::bigint as flights
        from gold.fct_flights group by 1 order by flights desc, origin_airport_sk limit 20""",
        """select origin_airport_sk, sum(scheduled_flights)::bigint as flights
        from gold.mart_route_monthly group by 1 order by flights desc, origin_airport_sk limit 20""",
    ),
}
RELATIONS = (
    "silver.flights", "gold.fct_flights", "gold.dim_airline", "gold.dim_airport",
    "gold.dim_date", "gold.mart_network_monthly", "gold.mart_airline_monthly",
    "gold.mart_airport_daily", "gold.mart_route_monthly", "gold.mart_delay_causes",
)


def execution_order(repetitions):
    if type(repetitions) is not int or not 3 <= repetitions <= 9:
        raise ValueError("repetitions must be between 3 and 9")
    return [("fact", "mart") if i % 2 == 0 else ("mart", "fact")
            for i in range(repetitions)]


def summarize(samples):
    if not samples or any(s["execution_ms"] <= 0 for s in samples):
        raise ValueError("positive execution-time samples required")
    values = [s["execution_ms"] for s in samples]
    return {"samples": samples, "median_ms": round(statistics.median(values), 3),
            "min_ms": min(values), "max_ms": max(values)}


def plan_nodes(node):
    return [node["Node Type"], *[name for child in node.get("Plans", [])
                                 for name in plan_nodes(child)]]


def sample(plan):
    root = plan["Plan"]
    return {"execution_ms": plan["Execution Time"], "planning_ms": plan["Planning Time"],
            "shared_hit_blocks": root.get("Shared Hit Blocks", 0),
            "shared_read_blocks": root.get("Shared Read Blocks", 0),
            "temp_read_blocks": root.get("Temp Read Blocks", 0),
            "temp_written_blocks": root.get("Temp Written Blocks", 0),
            "nodes": sorted(set(plan_nodes(root)))}


def require_equal(fact, mart, name):
    if fact != mart:
        raise ValueError(f"{name}: fact/mart results differ")


def run(repetitions=3):
    import psycopg

    order = execution_order(repetitions)
    settings = read_env(PROJECT_ROOT / ".env")
    if (settings["POSTGRES_DB"], settings["POSTGRES_PORT"]) != ("flight_warehouse", "5433"):
        raise RuntimeError("Expected the accepted local warehouse on port 5433")
    result = {"measured_at_utc": datetime.now(timezone.utc).isoformat(),
              "repetitions": repetitions, "warmup_per_variant": 1,
              "method": "alternating EXPLAIN ANALYZE BUFFERS, no cache reset",
              "queries": {}, "storage": {}, "indexes": []}
    plans = {}
    with psycopg.connect(host="127.0.0.1", port=5433, dbname=settings["POSTGRES_DB"],
                         user=settings["POSTGRES_USER"], password=settings["POSTGRES_PASSWORD"],
                         connect_timeout=10) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '180s'")
        conn.execute("SET LOCAL lock_timeout = '5s'")
        if conn.execute("select current_database()").fetchone()[0] != "flight_warehouse":
            raise RuntimeError("Unexpected database")
        result["postgres_version"] = conn.execute("show server_version").fetchone()[0]
        result["settings"] = {key: conn.execute("select current_setting(%s)", (key,)).fetchone()[0]
                              for key in ("shared_buffers", "work_mem", "effective_cache_size",
                                          "max_parallel_workers_per_gather", "jit", "block_size")}
        result["database_bytes"] = conn.execute(
            "select pg_database_size(current_database())").fetchone()[0]
        audit = conn.execute("select count(*),sum(silver_row_count) from audit.silver_loads").fetchone()
        if audit != (24, EXPECTED_ROWS):
            raise RuntimeError("Unexpected audit scope")
        result["audit_months"], result["audit_rows"] = int(audit[0]), int(audit[1])
        for relation in RELATIONS:
            heap, indexes, total = conn.execute(
                "select pg_relation_size(%s),pg_indexes_size(%s),pg_total_relation_size(%s)",
                (relation, relation, relation)).fetchone()
            result["storage"][relation] = {"heap_bytes": heap, "index_bytes": indexes,
                                           "total_bytes": total}
        for row in conn.execute(
            """select schemaname,tablename,indexname,indexdef from pg_indexes
            where schemaname in ('silver','gold') order by 1,2,3"""
        ):
            result["indexes"].append(dict(zip(("schema", "table", "name", "definition"), row)))
        for name, (fact, mart) in QUERIES.items():
            variants = {"fact": fact, "mart": mart}
            rows = {key: conn.execute(sql).fetchall() for key, sql in variants.items()}
            require_equal(rows["fact"], rows["mart"], name)
            if name == "network_monthly" and (
                len(rows["fact"]) != 24 or sum(r[1] for r in rows["fact"]) != EXPECTED_ROWS
            ):
                raise RuntimeError("Unexpected network population")
            samples = {"fact": [], "mart": []}
            plans[name] = {"fact": [], "mart": []}
            # The result comparison above is also the unmeasured warm-up.
            for pair in order:
                for key in pair:
                    raw = conn.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " +
                                       variants[key]).fetchone()[0][0]
                    samples[key].append(sample(raw))
                    plans[name][key].append(raw)
            summaries = {key: summarize(value) for key, value in samples.items()}
            result["queries"][name] = {
                "matched_rows": len(rows["fact"]), "fact": summaries["fact"],
                "mart": summaries["mart"], "median_ratio": round(
                    summaries["fact"]["median_ms"] / summaries["mart"]["median_ms"], 2),
            }
            print(name, result["queries"][name]["fact"]["median_ms"],
                  result["queries"][name]["mart"]["median_ms"], flush=True)
    return result, plans


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    result, plans = run(args.repetitions)
    output = PROJECT_ROOT / "data/tmp/phase8"
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    for name, payload in (("baseline", result), ("plans", plans)):
        path = output / f"{name}-{stamp}.json"
        with path.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
