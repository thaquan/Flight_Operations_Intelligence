"""Refine the Executive page layout while preserving report identity and filters.

The wide monthly trend is the primary visual. Three compact 2025-vs-2024
delta cards provide the executive takeaway without repeating KPI values.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
from pathlib import Path

from src.phase5.build_atlas_report import (
    PAGES,
    color,
    expression_literal,
    field,
    uid,
)

MONTHLY_CATEGORY = "dim_month.source_month"
DELTA_METRICS = (
    ("right-chart", "Executive Arrival Risk YoY", "ARRIVAL DELAY RISK",
     28, 510, 25),
    ("risk-cancellation", "Executive Cancellation Risk YoY",
     "CANCELLATION RISK", 554, 331, 22),
    ("risk-diversion", "Executive Diversion Risk YoY",
     "DIVERSION RISK", 900, 352, 22),
)
LABEL_TEXT = {
    "right-label": "2025 VS 2024  /  CHANGE IN RISK (PERCENTAGE POINTS)",
    "left-label": "MONTHLY TREND / RESPONDS TO YEAR SELECTION",
    "footer": ("Headline KPIs and trend follow YEAR. YoY deltas compare "
               "full 2024 vs 2025. Delay % uses eligible arrivals."),
}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def path_for(root: Path, page: str, role: str) -> Path:
    return root / page / "visuals" / uid(page, role) / "visual.json"


def color_rule(value: str) -> dict:
    return color(value)


def style_trend(item: dict) -> dict:
    out = copy.deepcopy(item)
    visual = out["visual"]
    if visual["visualType"] != "lineChart":
        raise ValueError("Expected the existing Executive line chart")
    q = visual["query"]["queryState"]
    cats = q["Category"]["projections"]
    ys = q["Y"]["projections"]
    old = [f"dim_month.{col}" for col in ("month_label", "source_month")]
    if [p["queryRef"] for p in cats] not in ([old[0]], [old[1]]):
        raise ValueError("Executive trend category was customized")
    if [p["queryRef"] for p in ys] != [
            "mart_network_monthly.Arrival Delay 15+ Rate"]:
        raise ValueError("Executive trend measure was customized")
    if out["position"]["width"] not in (808, 1224):
        raise ValueError("Executive trend geometry was customized")
    out["position"].update({"x": 28, "y": 375, "width": 1224, "height": 279})
    q["Category"]["projections"] = [{
        **field("dim_month", "source_month", "Column"),
        "displayName": "Month", "active": True,
    }]
    visual["query"]["sortDefinition"] = {
        "sort": [{"field": field("dim_month", "source_month", "Column")["field"],
                  "direction": "Ascending"}],
    }
    objects = visual.setdefault("objects", {})
    objects["dataPoint"] = [{"properties": {
        "defaultColor": color_rule("#1665ED"),
    }}]
    objects["lineStyles"] = [{"properties": {
        "lineChartType": expression_literal("'linear'"),
        "strokeWidth": expression_literal("2.5D"),
        "showMarker": expression_literal("true"),
        "markerShape": expression_literal("'circle'"),
        "markerSize": expression_literal("5D"),
    }}]
    objects["categoryAxis"] = [{"properties": {
        "axisType": expression_literal("'Scalar'"),
        "fontSize": expression_literal("10D"),
        "showAxisTitle": expression_literal("false"),
        "gridlineShow": expression_literal("false"),
    }}]
    objects["valueAxis"] = [{"properties": {
        "fontSize": expression_literal("10D"),
        "showAxisTitle": expression_literal("false"),
        "gridlineShow": expression_literal("true"),
        "gridlineColor": color_rule("#E7EDF4"),
    }}]
    container = visual.setdefault("visualContainerObjects", {})
    container["title"] = [{"properties": {
        "show": expression_literal("true"),
        "text": expression_literal("'Monthly delayed-arrival rate'"),
        "fontSize": expression_literal("16D"),
        "fontColor": color_rule("#142C43"),
        "bold": expression_literal("true"),
    }}]
    container["subTitle"] = [{"properties": {
        "show": expression_literal("false"),
    }}]
    return out


def style_delta_card(item: dict, name: str, label: str, x: int,
                     width: int, font_size: int) -> dict:
    out = copy.deepcopy(item)
    v = out["visual"]
    if v["visualType"] != "cardVisual":
        raise ValueError("Expected a native Power BI scorecard")
    refs = [p["queryRef"] for p in
            v["query"]["queryState"]["Data"]["projections"]]
    if refs != [f"mart_network_monthly.{name}"]:
        raise ValueError("Executive delta card measure was customized")
    if out["position"]["width"] not in (392, width):
        raise ValueError("Executive delta card position was customized")
    out["position"].update({"x": x, "y": 253, "width": width, "height": 82})
    projection = v["query"]["queryState"]["Data"]["projections"][0]
    projection["displayName"] = label
    v["objects"]["value"][0]["properties"].update({
        "fontSize": expression_literal(f"{font_size}D"),
        "fontColor": color_rule("#D55445"),
        "bold": expression_literal("true"),
        "textWrap": expression_literal("false"),
    })
    v["objects"]["label"][0]["properties"].update({
        "show": expression_literal("true"),
        "fontSize": expression_literal("12D"),
        "fontColor": color_rule("#25435F"),
        "bold": expression_literal("true"),
        "position": expression_literal("'aboveValue'"),
    })
    container = v["visualContainerObjects"]
    bg = "#FFF9F6" if name == "Executive Arrival Risk YoY" else "#FFFFFF"
    outline = ("#EFC3B8" if name == "Executive Arrival Risk YoY"
               else "#D6E1EA")
    container["background"][0]["properties"]["color"] = color_rule(bg)
    container["border"][0]["properties"]["color"] = color_rule(outline)
    for direction in ("top", "bottom", "left", "right"):
        container["padding"][0]["properties"][direction] = (
            expression_literal("7D" if direction in ("top", "bottom") else "12D")
        )
    return out


def style_network_kpis(item: dict) -> dict:
    """Show the network flight volume at two-decimal million precision."""
    out = copy.deepcopy(item)
    v = out["visual"]
    if v["visualType"] != "cardVisual":
        raise ValueError("Executive KPI row is not a card visual")
    refs = [p["queryRef"] for p in
            v["query"]["queryState"]["Data"]["projections"]]
    if not refs or refs[0] != "mart_network_monthly.Scheduled Flights":
        raise ValueError("Network KPI source has changed")
    v["objects"]["value"][0]["properties"]["labelPrecision"] = (
        expression_literal("2L")
    )
    return out


def style_label(item: dict, role: str) -> dict:
    out = copy.deepcopy(item)
    value = (out["visual"]["objects"]["general"][0]["properties"]
             ["paragraphs"][0]["textRuns"][0])
    old = value["value"]
    if old == LABEL_TEXT[role]:
        return out
    permitted = {
        "right-label": ("NETWORK RISK /", "2025 VS 2024  /"),
        "left-label": ("NETWORK RELIABILITY /", "24-MONTH TREND  /"),
        "footer": ("Risk scorecard compares", "YoY deltas compare"),
    }[role]
    if not old.startswith(permitted):
        raise ValueError(f"Executive label was customized: {role}")
    value["value"] = LABEL_TEXT[role]
    if role == "right-label":
        out["position"].update({"x": 28, "y": 220, "width": 1218})
        value["textStyle"].update({"fontSize": "13px", "color": "#173E59"})
    elif role == "left-label":
        out["position"].update({"x": 28, "y": 345, "width": 1218})
        value["textStyle"].update({"fontSize": "13px", "color": "#173E59"})
    else:
        out["position"].update({"x": 29, "y": 674, "width": 1210})
    return out


def plan(root: Path = PAGES) -> dict[Path, dict]:
    ids = read(root / "pages.json")["pageOrder"]
    if len(ids) != 5:
        raise ValueError("Expected five report pages")
    page = ids[0]
    if read(root / page / "page.json")["displayName"] != "Executive Overview":
        raise ValueError("Executive page identity changed")
    edits: dict[Path, dict] = {}
    for role in ("metrics", "left-chart",
                 *[r for r, *_ in DELTA_METRICS], *LABEL_TEXT):
        path = path_for(root, page, role)
        before = read(path)
        if before["name"] != uid(page, role):
            raise ValueError(f"Visual ID changed: {path}")
        if role == "metrics":
            after = style_network_kpis(before)
        elif role == "left-chart":
            after = style_trend(before)
        elif role in LABEL_TEXT:
            after = style_label(before, role)
        else:
            spec = next(m for m in DELTA_METRICS if m[0] == role)
            after = style_delta_card(before, *spec[1:])
        if before != after:
            edits[path] = after
    return edits


def apply(root: Path = PAGES) -> list[Path]:
    edits = plan(root)
    for path, obj in edits.items():
        fd, tmp = tempfile.mkstemp(
            prefix=".exec-polish-", suffix=".tmp", dir=path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(obj, indent=2, ensure_ascii=False)
                             + "\n")
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return list(edits)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(f"{'Applied' if args.apply else 'Dry run:'} "
          f"{len(apply() if args.apply else plan())} scoped edits")


if __name__ == "__main__":
    main()
