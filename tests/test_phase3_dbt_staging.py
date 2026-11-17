"""Static dbt model contracts; runnable without PostgreSQL or dbt installed."""

from __future__ import annotations

from pathlib import Path
import re

from src.phase3.silver_contract import SILVER_COLUMNS


DBT_ROOT = Path(__file__).resolve().parents[1] / "dbt"


def test_staging_selects_every_silver_column_without_dropping_rows() -> None:
    sql = (DBT_ROOT / "models/staging/stg_flights.sql").read_text(encoding="utf-8")
    assert "source('silver', 'flights')" in sql
    for column in (*SILVER_COLUMNS, "silver_loaded_at_utc"):
        assert re.search(rf"^    {re.escape(column)},?$", sql, re.MULTILINE), column
    assert not re.search(r"^\s*(where|join|distinct)\b", sql, re.IGNORECASE | re.MULTILINE)


def test_outcomes_use_arrival_eligibility_not_scheduled_denominator() -> None:
    sql = (DBT_ROOT / "models/staging/stg_flight_outcomes.sql").read_text(encoding="utf-8")
    assert "ref('stg_flights')" in sql
    assert "flight_status = 'completed' and arr_del15 in (0, 1)" in sql
    assert "flight_status = 'completed' and arr_del15 = 1" in sql
    assert "flight_status = 'completed' and arr_del15 = 0" in sql
    for column in (
        "scheduled_flight_count",
        "completed_flight_count",
        "cancelled_flight_count",
        "diverted_flight_count",
        "eligible_arrival_count",
        "arrival_delayed_15_count",
        "arrival_on_time_count",
    ):
        assert f"as {column}" in sql


def test_staging_has_monthly_reconciliation_and_semantic_data_tests() -> None:
    monthly = (DBT_ROOT / "tests/assert_staging_monthly_row_counts.sql").read_text(
        encoding="utf-8"
    )
    outcomes = (DBT_ROOT / "tests/assert_arrival_kpi_flags.sql").read_text(
        encoding="utf-8"
    )
    assert "source('silver', 'flights')" in monthly
    assert "ref('stg_flight_outcomes')" in monthly
    assert "full outer join" in monthly.lower()
    assert "arrival_delayed_15_count + arrival_on_time_count" in outcomes
