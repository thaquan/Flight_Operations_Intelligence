"""Bootstrap and verify a tiny, isolated PostgreSQL fixture for dbt CI.

Safety: runs only with FLIGHT_CI_FIXTURE=1 and POSTGRES_DB=flight_ci.
The production-like flight_warehouse database is never a valid target.
"""

from __future__ import annotations

import argparse
import os

import psycopg
from psycopg import errors

from src.phase3.config import PROJECT_ROOT

EXPECTED_MONTHLY_ROWS = {"2024-01": 6, "2024-02": 2, "2025-01": 2}


def require_fixture_environment() -> dict[str, str | int]:
    if os.environ.get("FLIGHT_CI_FIXTURE") != "1":
        raise RuntimeError("Set FLIGHT_CI_FIXTURE=1 for the isolated CI database")
    if os.environ.get("POSTGRES_DB") != "flight_ci":
        raise RuntimeError("Fixture operation refused: POSTGRES_DB must be flight_ci")
    required = ("POSTGRES_USER", "POSTGRES_PASSWORD")
    if any(not os.environ.get(key) for key in required):
        raise RuntimeError("CI PostgreSQL connection environment is incomplete")
    return {
        "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": "flight_ci",
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
    }


def setup(conn: psycopg.Connection) -> None:
    """Apply the actual versioned warehouse DDL, then insert synthetic rows."""
    paths = (
        "docker/postgres/init/001_create_schemas.sql",
        "sql/phase3/002_create_silver.sql",
        "sql/phase4/ci_seed.sql",
    )
    for relative in paths:
        conn.execute((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
    assert_source_counts(conn)
    print("Synthetic Silver fixture ready: 10 rows in 3 source months")


def assert_source_counts(conn: psycopg.Connection) -> None:
    actual = {
        month: count
        for month, count in conn.execute(
            "select to_char(source_month, 'YYYY-MM'), count(*) "
            "from silver.flights group by source_month"
        ).fetchall()
    }
    if actual != EXPECTED_MONTHLY_ROWS:
        raise AssertionError(f"Unexpected fixture months/rows: {actual}")


def verify(conn: psycopg.Connection) -> None:
    """Check semantic output and transactional recovery after dbt build."""
    assert_source_counts(conn)
    network = conn.execute(
        "select sum(scheduled_flights), sum(completed_flights), "
        "sum(cancelled_flights), sum(diverted_flights), "
        "sum(eligible_arrivals), sum(late_arrivals_15), "
        "sum(on_time_arrivals) from gold.mart_network_monthly"
    ).fetchone()
    expected = (10, 7, 2, 1, 6, 3, 3)
    if tuple(network) != expected:
        raise AssertionError(f"Expected KPI counters {expected}, got {network}")
    unknown = conn.execute(
        "select count(*) from gold.fct_flights "
        "where airline_sk = -1 and origin_airport_sk = -1"
    ).fetchone()[0]
    if unknown != 1:
        raise AssertionError(f"Expected one unknown-airline/airport flight, got {unknown}")
    attribution = conn.execute(
        "select sum(reported_observations), sum(positive_delay_observations) "
        "from gold.mart_delay_causes"
    ).fetchone()
    if tuple(attribution) != (15, 6):
        raise AssertionError(f"Expected (15 non-NULL, 6 positive) cause readings, got {attribution}")
    recovery_checks(conn)
    print("Synthetic Gold KPIs, unknown members, cause NULLs and recovery: PASS")


def recovery_checks(conn: psycopg.Connection) -> None:
    """Failures roll back only their own transaction/savepoint."""
    base_insert = (
        "insert into silver.flights "
        "(source_month,source_row_number,flight_year,flight_date,"
        "source_file,source_sha256,bronze_ingested_at_utc,cancelled,diverted) "
        "values (%s,%s,2024,%s,'ci_fixture.zip',repeat('a',64),now(),%s,0)"
    )
    cases = (
        (("2024-01-01", 1, "2024-01-03", 0), errors.UniqueViolation),
        (("2024-01-01", 90, "2024-02-01", 0), errors.CheckViolation),
        (("2024-01-01", 91, "2024-01-03", 2), errors.CheckViolation),
    )
    with conn.transaction():
        for values, error in cases:
            try:
                with conn.transaction():
                    conn.execute(base_insert, values)
            except error:
                pass
            else:
                raise AssertionError(f"Invalid write unexpectedly succeeded: row={values[1]}")
        # A valid preceding write must also roll back when a later write fails.
        try:
            with conn.transaction():
                conn.execute(base_insert, ("2024-01-01", 99, "2024-01-03", 0))
                conn.execute(base_insert, ("2024-01-01", 1, "2024-01-03", 0))
        except errors.UniqueViolation:
            pass
        else:
            raise AssertionError("A failed multi-statement transaction was committed")
        assert_source_counts(conn)
    assert_source_counts(conn)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("setup", "verify"))
    args = parser.parse_args()
    connection = require_fixture_environment()
    with psycopg.connect(**connection, autocommit=True) as conn:
        if args.command == "setup":
            setup(conn)
        else:
            verify(conn)


if __name__ == "__main__":
    main()
