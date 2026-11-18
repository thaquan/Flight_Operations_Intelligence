"""Fast, offline contracts for the M3.5 Gold aggregate layer.

These complement dbt's data tests, which require a populated PostgreSQL
warehouse and verify actual source-to-mart reconciliation.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYTICS = ROOT / "dbt/models/marts/analytics"
DBT_TESTS = ROOT / "dbt/tests"

MODEL_NAMES = (
    "mart_network_monthly",
    "mart_airline_monthly",
    "mart_airport_daily",
    "mart_route_monthly",
    "mart_delay_causes",
)


def model_sql(name: str) -> str:
    return (ANALYTICS / f"{name}.sql").read_text(encoding="utf-8").lower()


def test_all_five_marts_materialize_as_gold_tables() -> None:
    project = (ROOT / "dbt/dbt_project.yml").read_text(encoding="utf-8")
    assert "analytics:" in project
    assert project.count("+materialized: table") == 3
    for name in MODEL_NAMES:
        assert (ANALYTICS / f"{name}.sql").is_file()
        assert "ref('fct_flights')" in model_sql(name)


def test_rate_logic_is_shared_and_ratio_of_sums() -> None:
    macro = (ROOT / "dbt/macros/flight_kpi_metrics.sql").read_text(
        encoding="utf-8"
    ).lower()
    assert "sum(arrival_delayed_15_count)" in macro
    assert "sum(eligible_arrival_count)" in macro
    assert "nullif(sum(eligible_arrival_count), 0)" in macro
    assert "avg(arr_delay)" in macro
    for name in MODEL_NAMES[:4]:
        assert "{{ flight_kpi_metrics() }}" in model_sql(name)


def test_airport_roles_and_directed_routes_are_explicit() -> None:
    airports = model_sql("mart_airport_daily")
    routes = model_sql("mart_route_monthly")
    assert "union all" in airports
    assert "'origin'" in airports
    assert "'destination'" in airports
    assert "group by airport_sk, airport_role, flight_date" in airports
    assert "origin_airport_sk" in routes
    assert "dest_airport_sk" in routes
    assert "limit " not in routes


def test_delay_causes_preserve_source_null_semantics() -> None:
    sql = model_sql("mart_delay_causes")
    assert "cross join lateral" in sql
    for cause in ("carrier", "weather", "nas", "security", "late_aircraft"):
        assert f"'{cause}'" in sql
    assert "cause.cause_minutes is not null" in sql
    assert "positive_delay_observations" in sql
    assert "coalesce(" not in sql
    assert "sum(reported_delay_minutes) over" in sql


def test_mart_reconciliation_and_grain_tests_are_versioned() -> None:
    for name in (
        "assert_mart_unique_grains",
        "assert_mart_network_fact_totals",
        "assert_mart_kpi_reconciliation",
        "assert_mart_rate_boundaries",
        "assert_mart_cause_fact_totals",
    ):
        assert (DBT_TESTS / f"{name}.sql").is_file()
    metadata = (ANALYTICS / "_analytics.yml").read_text(encoding="utf-8")
    for name in MODEL_NAMES:
        assert f"name: {name}" in metadata
