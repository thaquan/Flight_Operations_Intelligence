"""Isolated two-month Gold replacement experiment; never writes production Gold."""

import json
import time

import psycopg

from src.phase3.config import PROJECT_ROOT, read_env


def benchmark() -> dict:
    root = PROJECT_ROOT / "data/tmp/m73-isolated"
    settings = read_env(root / ".env")
    if (settings["POSTGRES_DB"], settings["POSTGRES_PORT"]) != ("flight_m73_test", "5543"):
        raise RuntimeError("Refusing to benchmark outside the isolated M7.3 database")
    compiled = root / "dbt/target/compiled/flight_operations_intelligence/models/marts"
    fact_query = (compiled / "facts/fct_flights.sql").read_text(encoding="utf-8").strip().rstrip(";")
    network_query = (compiled / "analytics/mart_network_monthly.sql").read_text(
        encoding="utf-8").strip().rstrip(";")
    gold_ref = '"flight_m73_test"."gold"."fct_flights"'
    if '"flight_m73_test"."staging"."stg_flight_outcomes"' not in fact_query or gold_ref not in network_query:
        raise RuntimeError("Compiled SQL does not reference isolated dbt relations")
    network_query = network_query.replace(gold_ref, "pg_temp.month_fact")
    result = {}

    with psycopg.connect(host="127.0.0.1", port=5543, dbname=settings["POSTGRES_DB"],
                         user=settings["POSTGRES_USER"], password=settings["POSTGRES_PASSWORD"],
                         connect_timeout=10) as conn:
        if conn.execute("select current_database()").fetchone()[0] != "flight_m73_test":
            raise RuntimeError("Unexpected database")
        counts = conn.execute(
            "select to_char(source_month,'YYYY-MM'),count(*) from gold.fct_flights "
            "group by 1 order by 1").fetchall()
        if counts != [("2024-01", 547271), ("2024-02", 519221)]:
            raise RuntimeError(f"Unexpected baseline: {counts}")
        conn.execute("create temp table full_fact (like gold.fct_flights including indexes)")
        conn.execute("create temp table month_fact (like gold.fct_flights including indexes)")
        for table in ("full_fact", "month_fact"):
            conn.execute(f"create index on {table}(source_month)")
        conn.execute("create temp table month_network (like gold.mart_network_monthly including indexes)")
        conn.commit()

        def timed(label, sql, params=()):
            start = time.perf_counter()
            with conn.transaction():
                rows = conn.execute(sql, params).rowcount
            result[label] = {"rows": rows, "seconds": round(time.perf_counter() - start, 3)}
            print(label, result[label], flush=True)

        timed("full_fact_insert", "insert into full_fact " + fact_query)
        timed("jan_fact_insert", "insert into month_fact select * from (" + fact_query
              + ") q where source_month=%s::date", ("2024-01-01",))
        timed("jan_network_insert", "insert into month_network select * from (" + network_query
              + ") q where source_month=%s::date", ("2024-01-01",))
        timed("feb_fact_insert", "insert into month_fact select * from (" + fact_query
              + ") q where source_month=%s::date", ("2024-02-01",))
        timed("feb_network_insert", "insert into month_network select * from (" + network_query
              + ") q where source_month=%s::date", ("2024-02-01",))

        # Simulate a stale target key (one missing legitimate row and one obsolete key).
        with conn.transaction():
            conn.execute("update month_fact set flight_sk=-1 where flight_sk=(select min(flight_sk) "
                         "from month_fact where source_month='2024-02-01')")
            conn.execute("update month_network set scheduled_flights=-1 where source_month='2024-02-01'")
        start = time.perf_counter()
        with conn.transaction():
            deleted = conn.execute("delete from month_fact where source_month='2024-02-01'").rowcount
            inserted = conn.execute("insert into month_fact select * from (" + fact_query
                                    + ") q where source_month='2024-02-01'").rowcount
            conn.execute("delete from month_network where source_month='2024-02-01'")
            conn.execute("insert into month_network select * from (" + network_query
                         + ") q where source_month='2024-02-01'")
        result["feb_replacement"] = {"deleted": deleted, "inserted": inserted,
                                     "seconds": round(time.perf_counter() - start, 3)}
        print("feb_replacement", result["feb_replacement"], flush=True)
        for name, table, baseline, key in (
            ("full_fact_diff", "full_fact", "gold.fct_flights", "flight_sk"),
            ("incremental_fact_diff", "month_fact", "gold.fct_flights", "flight_sk"),
            ("incremental_network_diff", "month_network", "gold.mart_network_monthly", "source_month"),
        ):
            mismatch = conn.execute(
                f"select count(*) from {table} a full join {baseline} b using ({key}) "
                f"where a.{key} is null or b.{key} is null or row(a.*) is distinct from row(b.*)"
            ).fetchone()[0]
            result[name] = mismatch
            print(name, mismatch, flush=True)
            if mismatch:
                raise RuntimeError(f"{name}: {mismatch} mismatches")
        result["obsolete_key_count"] = conn.execute(
            "select count(*) from month_fact where flight_sk=-1").fetchone()[0]
        assert result["obsolete_key_count"] == 0
        result["row_counts"] = counts
    return result


if __name__ == "__main__":
    print(json.dumps(benchmark(), indent=2))
