"""Offline checks for the M5.2 Power BI semantic-model contract."""

from __future__ import annotations

import json

from src.phase5 import build_semantic_model as model_builder
from src.phase5.build_semantic_model import (
    COUNTERS,
    DEFINITION,
    MODEL_DIR,
    RELATIONSHIPS,
    ROOT,
    TABLES,
    render_files,
)


def test_semantic_model_generator_is_deterministic(tmp_path, monkeypatch):
    # Desktop re-serializes TMDL and writes .pbi caches; do not overwrite its model.
    expected = render_files()
    monkeypatch.setattr(model_builder, "MODEL_DIR", tmp_path)
    model_builder.build()
    actual = {p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file()}
    assert actual == set(expected)
    for path, contents in expected.items():
        assert (tmp_path / path).read_text(encoding="utf-8") == contents
    config = json.loads((MODEL_DIR / "definition.pbism").read_text(encoding="utf-8"))
    assert float(config["version"]) >= 4.0
    assert all((MODEL_DIR / path).is_file() for path in expected)


def test_five_gold_marts_and_unique_dimensions():
    marts = {name for name in TABLES if name.startswith("mart_")}
    assert marts == {
        "mart_network_monthly",
        "mart_airline_monthly",
        "mart_airport_daily",
        "mart_route_monthly",
        "mart_delay_causes",
    }
    assert len(TABLES) == 11
    for name, spec in TABLES.items():
        names = [column.name for column in spec["columns"]]
        assert len(names) == len(set(names)), name
        assert all(column.kind in {"int64", "string", "boolean", "dateTime", "decimal"}
                   for column in spec["columns"])
    for name in marts - {"mart_delay_causes"}:
        columns = {column.name for column in TABLES[name]["columns"]}
        assert set(COUNTERS).issubset(columns)
        assert not any("rate_pct" in name or name.startswith("avg_") for name in columns)


def test_relationships_are_unambiguous_and_single_direction():
    assert len(RELATIONSHIPS) == 11
    assert len(RELATIONSHIPS) == len(set(RELATIONSHIPS))
    relation_text = (DEFINITION / "relationships.tmdl").read_text(encoding="utf-8")
    assert relation_text.count("relationship ") == 11
    # Desktop omits a property after Save when the value is the default.
    assert relation_text.count("crossFilteringBehavior: oneDirection") in (0, 11)
    for fact, foreign_key, dim, primary_key in RELATIONSHIPS:
        assert fact.startswith("mart_")
        assert dim.startswith("dim_")
        assert any(c.name == foreign_key for c in TABLES[fact]["columns"])
        assert any(c.name == primary_key and c.key for c in TABLES[dim]["columns"])
        assert f"fromColumn: {fact}.{foreign_key}" in relation_text
        assert f"toColumn: {dim}.{primary_key}" in relation_text
    assert "bothDirections" not in relation_text


def test_month_filter_and_airport_roles_are_explicit():
    assert {
        fact for fact, fk, dim, pk in RELATIONSHIPS
        if dim == "dim_month" and fk == "source_month" and pk == "source_month"
    } == {name for name in TABLES if name.startswith("mart_")}
    airport_daily = (DEFINITION / "tables/mart_airport_daily.tmdl").read_text(
        encoding="utf-8"
    )
    assert "Date.StartOfMonth([flight_date])" in airport_daily
    assert "column airport_role" in airport_daily
    route_rels = [relationship for relationship in RELATIONSHIPS
                  if relationship[0] == "mart_route_monthly"]
    assert ("mart_route_monthly", "origin_airport_sk",
            "dim_origin_airport", "airport_sk") in route_rels
    assert ("mart_route_monthly", "dest_airport_sk",
            "dim_dest_airport", "airport_sk") in route_rels


def test_no_secrets_embedded_or_claim_of_live_connection():
    expressions = (DEFINITION / "expressions.tmdl").read_text(encoding="utf-8")
    assert "pPgServer" in expressions and "pPgDatabase" in expressions
    all_tmdl = "\n".join(p.read_text(encoding="utf-8")
                         for p in DEFINITION.rglob("*.tmdl"))
    assert "PostgreSQL.Database(pPgServer, pPgDatabase" in all_tmdl
    assert "POSTGRES_PASSWORD" not in all_tmdl
    assert "password=" not in all_tmdl.lower()
    assert "fct_flights" not in all_tmdl


def test_columns_match_existing_gold_contract():
    macro = (ROOT / "dbt/macros/flight_kpi_metrics.sql").read_text(encoding="utf-8")
    for name in COUNTERS:
        assert f"as {name}" in macro
    for name in ("mart_network_monthly", "mart_airline_monthly",
                 "mart_airport_daily", "mart_route_monthly"):
        sql = ROOT / f"dbt/models/marts/analytics/{name}.sql"
        assert "flight_kpi_metrics()" in sql.read_text(encoding="utf-8")
    causes = (ROOT / "dbt/models/marts/analytics/mart_delay_causes.sql").read_text(
        encoding="utf-8"
    )
    for name in ("cause_type", "reported_observations",
                 "positive_delay_observations", "reported_delay_minutes"):
        assert name in causes


def test_dimension_and_fact_keys_use_the_same_type():
    for fact, foreign_key, dim, primary_key in RELATIONSHIPS:
        fact_type = next(c.kind for c in TABLES[fact]["columns"]
                         if c.name == foreign_key)
        dim_type = next(c.kind for c in TABLES[dim]["columns"]
                        if c.name == primary_key)
        assert fact_type == dim_type, (fact, foreign_key, dim, primary_key)
