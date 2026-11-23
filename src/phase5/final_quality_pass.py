"""Apply scoped, replay-safe UX and accessibility refinements to five PBIR pages."""
from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
from pathlib import Path

from src.phase5.build_atlas_report import PAGES, color, expression_literal, field, uid

NAV_KEYS = ("executive", "airline", "airports", "causes", "seasonal")
LABELS = {
    "executive": {
        "left-label": "MONTHLY TREND / RESPONDS TO YEAR SELECTION",
        "footer": "Headline KPIs and trend follow YEAR. YoY deltas compare full 2024 vs 2025. Delay % uses eligible arrivals.",
    },
    "airline": {
        "left-label": "CARRIER RISK / HOVER BUBBLES FOR DETAILS",
        "right-label": "FLIGHT SHARE / COLORS IDENTIFY CARRIERS",
        "footer": "Bubbles: X = flights, Y = delay %, size = cancelled flights. Hover for airline; treemap colors do not represent risk.",
    },
    "airports": {
        "left-label": "ORIGIN TRAFFIC / DRILL STATE TO AIRPORT",
        "right-label": "ROUTES BY VOLUME / SHADED DELAY RISK",
        "footer": "Select a state to filter routes; use drill controls for airports. Route table sorts by flights; warmer cells = more delay.",
    },
    "causes": {
        "left-label": "ATTRIBUTED MINUTES / MONTHLY HISTORY",
        "right-label": "CAUSE SHARE / MINUTES, NOT FLIGHTS",
        "footer": "Causes can overlap; observations are not unique delayed flights. Raw minutes are not normalized for traffic.",
    },
    "seasonal": {
        "left-label": "MONTHLY DELAY HEATMAP / SAME 10-35% SCALE",
        "right-label": "2025 - 2024 (PP) / CORAL WORSE, CYAN BETTER",
        "footer": "Top KPIs follow YEAR; comparison charts always show both years. Shared heatmap scale 10-35%; warmer means worse.",
    },
}
ALT = {
    ("executive", "left-chart"): "Line chart showing the monthly arrival delay 15 plus minute rate across the selected year or years.",
    ("executive", "right-chart"): "Increase in arrival delay rate from full-year 2024 to full-year 2025, in percentage points.",
    ("executive", "risk-cancellation"): "Change in cancellation rate from 2024 to 2025 in percentage points.",
    ("executive", "risk-diversion"): "Change in diversion rate from 2024 to 2025 in percentage points.",
    ("airline", "left-chart"): "Carrier scatterplot: horizontal axis flights, vertical axis delayed-arrival rate, bubble size cancelled flights. Hover for carrier details.",
    ("airline", "right-chart"): "Treemap showing carrier share of flight volume. Colors identify carriers only, not operational risk.",
    ("airports", "left-chart"): "Origin traffic by state, with drill from state to airport and selection filtering the route table.",
    ("airports", "right-chart"): "Directed origin to destination routes sorted by flights, with delay rate cells shaded to indicate risk.",
    ("causes", "left-chart"): "Stacked area over time of reported delay minutes attributed to carrier, late aircraft, NAS, security and weather causes.",
    ("causes", "right-chart"): "Share of reported delay minutes by five cause categories. Minutes and observations are not unique flights.",
    ("seasonal", "left-chart"): "Heatmap comparing monthly delayed-arrival rates for 2024 and 2025 on a fixed color scale from 10 to 35 percent.",
    ("seasonal", "right-chart"): "Monthly 2025 minus 2024 arrival delay rate in percentage points. Coral is worse; cyan is better.",
}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def fixed_fill_rule(measure: str, low: float, high: float) -> dict:
    """Use fixed numeric stops so shading means the same in every column."""
    return {
        "properties": {"backColor": {"solid": {"color": {"expr": {
            "FillRule": {
                "Input": {"SelectRef": {"ExpressionName": measure}},
                "FillRule": {"linearGradient2": {
                    "min": {"color": {"Literal": {"Value": "'#DDF7F2'"}},
                            "value": {"Literal": {"Value": f"{low}D"}}},
                    "max": {"color": {"Literal": {"Value": "'#F46A55'"}},
                            "value": {"Literal": {"Value": f"{high}D"}}},
                    "nullColoringStrategy": {"strategy": {
                        "Literal": {"Value": "'noColor'"}}},
                }},
            },
        }}}}},
        "selector": {
            "data": [{"dataViewWildcard": {"matchingOption": 1}}],
            "metadata": measure,
        },
    }


def enhance(key: str, role: str, original: dict) -> dict:
    """Return a refined copy; preserve identities, queries and other pages."""
    obj = copy.deepcopy(original)
    vis = obj["visual"]
    if role == "nav-" + key:
        text = vis["objects"]["text"][1]["properties"]
        actual = text["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"]
        if actual not in ("'#FFFFFF'", "'#073049'"):
            raise ValueError(f"Unexpected selected tab color on {key}")
        text["fontColor"] = color("#073049")

    if role == "metrics":
        if vis["visualType"] != "cardVisual":
            raise ValueError(f"Expected KPI card on {key}")
        props = vis["objects"]["value"][0]["properties"]
        current = props.get("labelPrecision", expression_literal("0L"))
        if current["expr"]["Literal"]["Value"] not in ("0L", "2L"):
            raise ValueError(f"Existing KPI decimal precision customized on {key}")
        props["labelPrecision"] = expression_literal("2L")
        if key == "executive":
            # Reject arbitrary user moves; correct only the observed Desktop
            # accidental drag outside the 1280px report canvas.
            geometry = obj["position"]
            if (geometry["width"], geometry["height"]) != (1224, 82):
                raise ValueError("Executive KPI dimensions were customized")
            current_xy = (geometry["x"], geometry["y"])
            accidental = (56.7029417419727, 96.07998461834262)
            if current_xy != (28, 115) and not all(
                    abs(actual - drift) < 0.01
                    for actual, drift in zip(current_xy, accidental)):
                raise ValueError("Executive KPI placement was customized")
            geometry.update({"x": 28, "y": 115})

    if role in LABELS[key]:
        if vis["visualType"] != "textbox":
            raise ValueError(f"Expected text box for {key}/{role}")
        runs = vis["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"]
        if len(runs) != 1:
            raise ValueError(f"Customized multi-run label on {key}/{role}")
        runs[0]["value"] = LABELS[key][role]
        if role == "footer":
            runs[0]["textStyle"].update({"fontSize": "12px", "color": "#34516A"})

    if (key, role) == ("airline", "left-chart"):
        if vis["visualType"] != "scatterChart":
            raise ValueError("Carrier risk scatter was replaced")
        # Small dense airlines remain accessible via native bubble hover.
        vis["objects"]["categoryLabels"][0]["properties"]["show"] = (
            expression_literal("false")
        )
        # The native scatter tooltip role accepts measures, not raw columns.
        tooltip = vis["query"]["queryState"]["Tooltips"]["projections"]
        tooltip[:] = [p for p in tooltip if p["queryRef"] !=
                      "dim_airline.airline_iata_code"]

    if (key, role) == ("airline", "right-chart"):
        if vis["visualType"] != "treemap":
            raise ValueError("Carrier treemap was replaced")
        vis["objects"]["legend"] = [{"properties": {
            "show": expression_literal("false")}}]

    if (key, role) == ("airports", "right-chart"):
        if vis["visualType"] != "tableEx":
            raise ValueError("Directed route table was replaced")
        measure = "mart_route_monthly.Route Delay 15+ Rate"
        refs = [p["queryRef"] for p in vis["query"]["queryState"]["Values"]["projections"]]
        if measure not in refs:
            raise ValueError("Route delay rate not in table")
        entries = vis["objects"].setdefault("values", [])
        entries[:] = [x for x in entries if x.get("selector", {}).get("metadata") != measure]
        entries.append(fixed_fill_rule(measure, 0.10, 0.40))

    if (key, role) == ("causes", "left-chart"):
        if vis["visualType"] != "stackedAreaChart":
            raise ValueError("Cause history was replaced")
        q = vis["query"]["queryState"]
        old = [p["queryRef"] for p in q["Category"]["projections"]]
        if old not in (["dim_month.month_label"], ["dim_month.source_month"]):
            raise ValueError("Unexpected cause history category")
        date = field("dim_month", "source_month", "Column")
        date.update({"displayName": "Month"})
        if q["Category"]["projections"][0].get("active") is True:
            date["active"] = True  # Desktop materializes the active level on Save.
        q["Category"]["projections"] = [date]
        vis["query"]["sortDefinition"] = {
            "sort": [{"field": date["field"], "direction": "Ascending"}],
        }
        props = vis["objects"]["categoryAxis"][0]["properties"]
        props["axisType"] = expression_literal("'Scalar'")
        props["fontSize"] = expression_literal("10D")

    if (key, role) == ("seasonal", "left-chart"):
        if vis["visualType"] != "pivotTable":
            raise ValueError("Seasonal heatmap was replaced")
        entries = vis["objects"]["values"]
        measure_names = [
            "mart_network_monthly.Delay Rate 2024 Fixed",
            "mart_network_monthly.Delay Rate 2025 Fixed",
        ]
        entries[:] = [item for item in entries if item.get("selector", {}).get("metadata") not in measure_names]
        entries.extend(fixed_fill_rule(name, 0.10, 0.35) for name in measure_names)

    if (key, role) in ALT:
        # Alt text belongs to the visual container, not visual.objects.general.
        objects = vis.get("objects")
        if objects is not None:
            legacy = objects.get("general", [])
            if legacy and len(legacy) == 1:
                legacy[0].get("properties", {}).pop("altText", None)
                if not legacy[0].get("properties"):
                    objects.pop("general", None)
        container = vis.setdefault("visualContainerObjects", {})
        general = container.setdefault("general", [])
        if len(general) > 1:
            raise ValueError(f"Multiple container general objects: {key}/{role}")
        if not general:
            general.append({"properties": {}})
        general[0]["properties"]["altText"] = expression_literal(
            "'" + ALT[key, role].replace("'", "''") + "'"
        )
    return obj


def plan(pages: Path = PAGES) -> dict[Path, dict]:
    ids = read(pages / "pages.json")["pageOrder"]
    if len(ids) != len(NAV_KEYS):
        raise ValueError("Canonical five-page report required")
    changes = {}
    for key, page in zip(NAV_KEYS, ids):
        for role in ("nav-" + key, "metrics", "left-label", "right-label",
                     "footer", "left-chart", "right-chart",
                     "risk-cancellation", "risk-diversion"):
            path = pages / page / "visuals" / uid(page, role) / "visual.json"
            if not path.is_file():
                if role.startswith("risk-") and key != "executive":
                    continue
                raise ValueError(f"Missing expected report visual: {path}")
            source = read(path)
            if source["name"] != uid(page, role):
                raise ValueError(f"Unexpected visual ID: {path}")
            target = enhance(key, role, source)
            if target != source:
                changes[path] = target
    return changes


def apply(pages: Path = PAGES) -> list[Path]:
    changes = plan(pages)
    for path, contents in changes.items():
        fd, temporary = tempfile.mkstemp(prefix=".quality-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(contents, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return list(changes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(f"{'Applied' if args.apply else 'Dry run:'} "
          f"{len(apply() if args.apply else plan())} report visual refinements")
