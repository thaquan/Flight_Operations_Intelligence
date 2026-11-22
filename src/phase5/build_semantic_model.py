"""Generate the reviewable Power BI Import-mode semantic model for M5.2.

This is metadata only. It never connects to PostgreSQL and never embeds secrets.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "powerbi" / "FlightOperations.SemanticModel"
DEFINITION = MODEL_DIR / "definition"
MEASURE_SNIPPETS = ROOT / "src" / "phase5" / "measure_snippets"


@dataclass(frozen=True)
class Column:
    name: str
    kind: str
    hidden: bool = False
    key: bool = False
    sort_by: str | None = None


def column(name: str, kind: str, *, hidden: bool = False, key: bool = False,
           sort_by: str | None = None) -> Column:
    return Column(name, kind, hidden, key, sort_by)


COUNTERS = (
    "scheduled_flights",
    "completed_flights",
    "cancelled_flights",
    "diverted_flights",
    "eligible_arrivals",
    "late_arrivals_15",
    "on_time_arrivals",
)
COUNT_COLUMNS = tuple(column(name, "int64", hidden=True) for name in COUNTERS)
MONTH = column("source_month", "dateTime")
MONTH_FK = column("source_month", "dateTime", hidden=True)

# Only additive counters are imported. Rounded mart rates and unweighted
# averages are deliberately excluded; DAX will recompute rates in M5.3.
TABLES: dict[str, dict] = {
    "dim_month": {
        "source": "mart_network_monthly",
        "columns": (
            column("source_month", "dateTime", key=True),
            column("calendar_year", "int64"),
            column("calendar_month", "int64"),
            column("month_label", "string", sort_by="month_sort"),
            column("month_sort", "int64", hidden=True),
        ),
    },
    "dim_airline": {
        "source": "dim_airline",
        "columns": (
            column("airline_sk", "int64", hidden=True, key=True),
            column("airline_dot_id", "int64", hidden=True),
            column("airline_code", "string"),
            column("airline_iata_code", "string"),
            column("is_unknown", "boolean", hidden=True),
        ),
    },
    "dim_airport": {
        "source": "dim_airport",
        "columns": (
            column("airport_sk", "int64", hidden=True, key=True),
            column("airport_id", "int64", hidden=True),
            column("airport_code", "string"),
            column("city_name", "string"),
            column("state_code", "string"),
            column("is_unknown", "boolean", hidden=True),
        ),
    },
    "dim_origin_airport": {
        "source": "dim_airport",
        "columns": (
            column("airport_sk", "int64", hidden=True, key=True),
            column("airport_id", "int64", hidden=True),
            column("airport_code", "string"),
            column("city_name", "string"),
            column("state_code", "string"),
            column("is_unknown", "boolean", hidden=True),
        ),
    },
    "dim_dest_airport": {
        "source": "dim_airport",
        "columns": (
            column("airport_sk", "int64", hidden=True, key=True),
            column("airport_id", "int64", hidden=True),
            column("airport_code", "string"),
            column("city_name", "string"),
            column("state_code", "string"),
            column("is_unknown", "boolean", hidden=True),
        ),
    },
    "dim_date": {
        "source": "dim_date",
        "columns": (
            column("date_key", "int64", hidden=True, key=True),
            column("flight_date", "dateTime"),
            column("calendar_year", "int64"),
            column("calendar_quarter", "int64"),
            column("calendar_month", "int64"),
            column("iso_day_of_week", "int64"),
            column("is_weekend", "boolean"),
        ),
    },
    "mart_network_monthly": {
        "source": "mart_network_monthly",
        "columns": (MONTH_FK, *COUNT_COLUMNS),
    },
    "mart_airline_monthly": {
        "source": "mart_airline_monthly",
        "columns": (
            column("airline_sk", "int64", hidden=True),
            MONTH_FK,
            *COUNT_COLUMNS,
        ),
    },
    "mart_airport_daily": {
        "source": "mart_airport_daily",
        "columns": (
            column("airport_sk", "int64", hidden=True),
            column("airport_role", "string"),
            column("flight_date_key", "int64", hidden=True),
            column("flight_date", "dateTime"),
            MONTH_FK,
            *COUNT_COLUMNS,
        ),
    },
    "mart_route_monthly": {
        "source": "mart_route_monthly",
        "columns": (
            column("origin_airport_sk", "int64", hidden=True),
            column("dest_airport_sk", "int64", hidden=True),
            MONTH_FK,
            *COUNT_COLUMNS,
        ),
    },
    "mart_delay_causes": {
        "source": "mart_delay_causes",
        "columns": (
            column("airline_sk", "int64", hidden=True),
            MONTH_FK,
            column("cause_type", "string"),
            column("reported_observations", "int64", hidden=True),
            column("positive_delay_observations", "int64", hidden=True),
            column("reported_delay_minutes", "decimal", hidden=True),
        ),
    },
}

# Many-side table/column, one-side table/column. Every relationship is
# active, one-to-many and single-direction, never a mart-to-mart join.
RELATIONSHIPS = (
    ("mart_network_monthly", "source_month", "dim_month", "source_month"),
    ("mart_airline_monthly", "source_month", "dim_month", "source_month"),
    ("mart_airport_daily", "source_month", "dim_month", "source_month"),
    ("mart_route_monthly", "source_month", "dim_month", "source_month"),
    ("mart_delay_causes", "source_month", "dim_month", "source_month"),
    ("mart_airline_monthly", "airline_sk", "dim_airline", "airline_sk"),
    ("mart_delay_causes", "airline_sk", "dim_airline", "airline_sk"),
    ("mart_airport_daily", "airport_sk", "dim_airport", "airport_sk"),
    ("mart_airport_daily", "flight_date_key", "dim_date", "date_key"),
    ("mart_route_monthly", "origin_airport_sk", "dim_origin_airport", "airport_sk"),
    ("mart_route_monthly", "dest_airport_sk", "dim_dest_airport", "airport_sk"),
)

M_TYPES = {
    "int64": "Int64.Type",
    "dateTime": "type date",
    "string": "type text",
    "boolean": "type logical",
    "decimal": "type number",
}


def _quote_tmdl(name: str) -> str:
    if any(ch in name for ch in " .:='"):
        return "'" + name.replace("'", "''") + "'"
    return name


def render_m(table_name: str, spec: dict) -> list[str]:
    """Build an M navigation query using Power BI's native PostgreSQL connector."""
    derived = {"month_label", "month_sort"} if table_name == "dim_month" else set()
    if table_name == "mart_airport_daily":
        derived.add("source_month")
    selected = [c for c in spec["columns"] if c.name not in derived]
    fields = ", ".join(f'"{c.name}"' for c in selected)
    conversions = ", ".join(
        f'{{"{c.name}", {M_TYPES[c.kind]}}}' for c in selected
    )
    lines = [
        "let",
        "    Source = PostgreSQL.Database(pPgServer, pPgDatabase, [CreateNavigationProperties=false]),",
        f'    Raw = Source{{[Schema="gold", Item="{spec["source"]}"]}}[Data],',
        f"    Selected = Table.SelectColumns(Raw, {{{fields}}}),",
        f"    Typed = Table.TransformColumnTypes(Selected, {{{conversions}}})",
    ]
    if table_name == "dim_month":
        lines[-1] += ","
        lines += [
            '    WithLabel = Table.AddColumn(Typed, "month_label", each Date.ToText([source_month], "MMM yyyy", "en-US"), type text),',
            '    WithSort = Table.AddColumn(WithLabel, "month_sort", each [calendar_year] * 100 + [calendar_month], Int64.Type)',
            "in",
            "    WithSort",
        ]
    elif table_name == "mart_airport_daily":
        lines[-1] += ","
        lines += [
            '    WithMonth = Table.AddColumn(Typed, "source_month", each Date.StartOfMonth([flight_date]), type date)',
            "in",
            "    WithMonth",
        ]
    else:
        lines += ["in", "    Typed"]
    return lines


def render_table(name: str, spec: dict) -> str:
    lines = [f"table {name}", ""]
    # Keep the curated DAX definitions separate from generated table metadata.
    snippet = MEASURE_SNIPPETS / f"{name}.tmdl"
    if snippet.is_file():
        lines.extend(snippet.read_text(encoding="utf-8").splitlines())
        lines.append("")
    for col in spec["columns"]:
        lines += [
            f"\tcolumn {_quote_tmdl(col.name)}",
            f"\t\tdataType: {col.kind}",
            f"\t\tsourceColumn: {col.name}",
            "\t\tsummarizeBy: none",
        ]
        if col.hidden:
            lines.append("\t\tisHidden")
        if col.key:
            lines.append("\t\tisKey")
        if col.sort_by:
            lines.append(f"\t\tsortByColumn: {col.sort_by}")
        if col.kind == "dateTime":
            lines.append("\t\tformatString: yyyy-MM-dd")
        lines.append("")
    lines += [
        f"\tpartition {name} = m",
        "\t\tmode: import",
        "\t\tsource =",
    ]
    lines += ["\t\t\t" + mline for mline in render_m(name, spec)]
    return "\n".join(lines) + "\n"


def render_relationships() -> str:
    lines = []
    for fact, fact_col, dim, dim_col in RELATIONSHIPS:
        key = "/".join((fact, fact_col, dim, dim_col))
        rid = uuid.uuid5(uuid.NAMESPACE_URL, f"flight-operations/{key}")
        lines += [
            f"relationship {rid}",
            f"\tfromColumn: {fact}.{fact_col}",
            f"\ttoColumn: {dim}.{dim_col}",
            "\tcrossFilteringBehavior: oneDirection",
            "",
        ]
    return "\n".join(lines)


def render_files() -> dict[Path, str]:
    refs = "\n".join(f"ref table {name}" for name in TABLES)
    return {
        Path("definition.pbism"): json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
                "version": "5.0",
                "settings": {"qnaEnabled": False},
            },
            indent=2,
        ) + "\n",
        Path("definition/database.tmdl"):
            "database FlightOperationsIntelligence\n"
            "\tcompatibilityLevel: 1702\n"
            "\tcompatibilityMode: powerBI\n"
            "\tlanguage: 1033\n",
        Path("definition/model.tmdl"):
            "model Model\n"
            "\tculture: en-US\n"
            "\tsourceQueryCulture: en-US\n"
            "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
            "\tdiscourageImplicitMeasures\n\n"
            f"{refs}\n",
        Path("definition/expressions.tmdl"):
            'expression pPgServer = "127.0.0.1:5433" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n\n'
            'expression pPgDatabase = "flight_warehouse" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n',
        Path("definition/relationships.tmdl"): render_relationships(),
        **{
            Path(f"definition/tables/{name}.tmdl"): render_table(name, spec)
            for name, spec in TABLES.items()
        },
    }


def build() -> None:
    # Keep Desktop lineage, relationships, and processed model caches intact.
    if (MODEL_DIR / ".pbi").exists() or (MODEL_DIR / ".platform").exists():
        raise FileExistsError("Desktop-saved semantic model; refuse regeneration")
    for path, content in render_files().items():
        dest = MODEL_DIR / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8", newline="\n")
    print(f"Generated {len(render_files())} TMDL/JSON model files in {MODEL_DIR}")


if __name__ == "__main__":
    build()
