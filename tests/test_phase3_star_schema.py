"""Offline contracts for the M3.4 warehouse star schema."""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "dbt/models/marts"


def test_marts_use_explicit_gold_schema_and_materialized_tables() -> None:
    project = (ROOT / "dbt/dbt_project.yml").read_text(encoding="utf-8")
    schema_macro = (ROOT / "dbt/macros/generate_schema_name.sql").read_text(
        encoding="utf-8"
    )
    assert "+schema: gold" in project
    assert project.count("+materialized: table") == 2
    assert "custom_schema_name | trim" in schema_macro
    for path in (
        MARTS / "dimensions/dim_airline.sql",
        MARTS / "dimensions/dim_airport.sql",
        MARTS / "dimensions/dim_date.sql",
        MARTS / "facts/fct_flights.sql",
    ):
        assert path.is_file()


def test_fact_retains_physical_grain_and_role_playing_keys() -> None:
    sql = (MARTS / "facts/fct_flights.sql").read_text(encoding="utf-8")
    assert "source_row_number" in sql
    assert "10000000" in sql  # room for up to 9,999,999 source rows per month
    assert "ref('stg_flight_outcomes')" in sql
    for field in (
        "flight_sk",
        "airline_sk",
        "origin_airport_sk",
        "dest_airport_sk",
        "flight_date_key",
        "source_file",
        "source_sha256",
        "eligible_arrival_count",
        "arrival_delayed_15_count",
    ):
        assert re.search(rf"\b{field}\b", sql), field
    assert not re.search(r"^\s*(where|join|distinct)\b", sql, re.I | re.M)


def test_airport_dimension_unions_both_roles_and_unknown_member() -> None:
    airport = (MARTS / "dimensions/dim_airport.sql").read_text(encoding="utf-8")
    airline = (MARTS / "dimensions/dim_airline.sql").read_text(encoding="utf-8")
    assert "origin_airport_id" in airport
    assert "dest_airport_id" in airport
    assert "union all" in airport.lower()
    assert "rank_number = 1" in airport
    assert "-1::integer as airport_sk" in airport
    assert "-1::integer as airline_sk" in airline


def test_fact_reconciliation_tests_are_present() -> None:
    monthly = (ROOT / "dbt/tests/assert_fact_monthly_row_counts.sql").read_text(
        encoding="utf-8"
    )
    kpis = (ROOT / "dbt/tests/assert_fact_kpi_totals.sql").read_text(
        encoding="utf-8"
    )
    assert "full outer join" in monthly.lower()
    assert "source('silver', 'flights')" in monthly
    assert "arrival_delayed_15_count" in kpis
    assert "eligible_arrival_count" in kpis
