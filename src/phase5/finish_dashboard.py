"""Finish the saved Power BI dashboard without re-scaffolding its pages.

Only adds native page navigation and improves known fields / seasonality.
Refuses to replace any unexpected Desktop edits.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from src.phase5.build_atlas_report import (
    NAV_TABS,
    PAGES,
    PAGES_SPEC,
    navigation_button,
    seasonal_overlay_chart,
    uid,
)

FRIENDLY = {
    "month_label": "Month",
    "calendar_year": "Year",
    "calendar_month": "Month",
    "airline_code": "Airline",
    "airport_code": "Origin airport",
    "cause_type": "Delay cause",
}
ROUTE_LABELS = ("Origin", "Destination", "Flights", "Delay 15+ %")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _visual(pages: Path, page: str, role: str) -> Path:
    return pages / page / "visuals" / uid(page, role) / "visual.json"


def _check_navigation(actual: dict, expected: dict, path: Path) -> None:
    a = actual["visual"]
    e = expected["visual"]
    if (a.get("visualType") != "actionButton"
            or a.get("visualContainerObjects", {}).get("visualLink")
            != e["visualContainerObjects"]["visualLink"]
            or a.get("objects", {}).get("text", [None, {}])[1].get("properties", {}).get("text")
            != e["objects"]["text"][1]["properties"]["text"]):
        raise ValueError(f"Existing navigation button customized: {path}")


def plan_finish(pages: Path = PAGES) -> dict[Path, dict]:
    ids = _load(pages / "pages.json")["pageOrder"]
    if len(ids) != len(PAGES_SPEC) or len(NAV_TABS) != len(ids):
        raise ValueError("Unexpected page count; refusing PBIR edit")

    changes: dict[Path, dict] = {}
    for page_index, (page_id, spec) in enumerate(zip(ids, PAGES_SPEC)):
        meta = _load(pages / page_id / "page.json")
        if meta["displayName"] != spec["title"]:
            raise ValueError("Page layout/order changed; refusing PBIR edit")

        for nav_index, ((key, label), dest) in enumerate(zip(NAV_TABS, ids)):
            expected = navigation_button(page_id, key, label, dest, nav_index,
                                         page_index == nav_index)
            nav_path = _visual(pages, page_id, "nav-" + key)
            if nav_path.exists():
                _check_navigation(_load(nav_path), expected, nav_path)
            else:
                changes[nav_path] = expected

        # Make chart grouping labels informative, without modifying measures.
        for role in ("left-chart", "right-chart"):
            path = _visual(pages, page_id, role)
            content = _load(path)
            kind = content["visual"]["visualType"]
            if spec["key"] == "executive" and role == "right-chart" and kind == "cardVisual":
                refs = [x["queryRef"] for x in
                        content["visual"]["query"]["queryState"]["Data"]["projections"]]
                if refs != ["mart_network_monthly.Executive Arrival Risk YoY"]:
                    raise ValueError(f"Executive comparison source changed: {path}")
                continue
            if spec["key"] == "seasonal" and role == "left-chart" and kind == "pivotTable":
                q = content["visual"]["query"]["queryState"]
                rows = [x["queryRef"] for x in q["Rows"]["projections"]]
                vals = [x["queryRef"] for x in q["Values"]["projections"]]
                if rows != ["dim_month.calendar_month"] or vals != [
                        "mart_network_monthly.Delay Rate 2024 Fixed",
                        "mart_network_monthly.Delay Rate 2025 Fixed"]:
                    raise ValueError(f"Seasonal year matrix source changed: {path}")
                continue
            if spec["key"] == "seasonal" and role == "right-chart" and kind == "clusteredBarChart":
                q = content["visual"]["query"]["queryState"]
                if ([x["queryRef"] for x in q["Category"]["projections"]] !=
                        ["dim_month.calendar_month"] or
                    [x["queryRef"] for x in q["Y"]["projections"]] !=
                        ["mart_network_monthly.Delay Rate YoY pp"]):
                    raise ValueError(f"Seasonal YoY bar source changed: {path}")
                continue
            if kind not in ("clusteredColumnChart", "clusteredBarChart",
                            "lineChart", "tableEx", "donutChart",
                            "scatterChart", "treemap", "stackedAreaChart"):
                raise ValueError(f"Unexpected chart type: {path}")
            projections = content["visual"]["query"]["queryState"]
            if (spec["key"] == "airline"
                    and ((role == "left-chart" and kind == "scatterChart")
                         or (role == "right-chart" and kind == "treemap"))):
                continue
            if (spec["key"] == "causes" and role == "left-chart"
                    and kind == "stackedAreaChart"):
                continue
            if (spec["key"] == "airports" and role == "left-chart"
                    and kind == "clusteredBarChart"
                    and len(projections["Category"]["projections"]) == 2):
                refs = [p["queryRef"] for p in
                        projections["Category"]["projections"]]
                if refs != ["dim_origin_airport.state_code",
                            "dim_origin_airport.airport_code"]:
                    raise ValueError(f"Unexpected airport drill levels: {path}")
                continue
            if kind == "tableEx":
                items = projections["Values"]["projections"]
                refs = [v["queryRef"] for v in items]
                expected_refs = [
                    "dim_origin_airport.airport_code",
                    "dim_dest_airport.airport_code",
                    "mart_route_monthly.Route Scheduled Flights",
                    "mart_route_monthly.Route Delay 15+ Rate",
                ]
                if refs != expected_refs:
                    raise ValueError(f"Route table fields changed: {path}")
                for item, label in zip(items, ROUTE_LABELS):
                    if item.get("displayName") not in (None, label):
                        raise ValueError(f"Route header changed: {path}")
                    if item.get("displayName") is None:
                        item["displayName"] = label
                        changes[path] = content
                continue

            if spec["key"] == "seasonal" and role == "left-chart":
                cat = projections["Category"]["projections"]
                original = [v["queryRef"] for v in cat]
                years = [v["queryRef"] for v in
                         projections.get("Series", {}).get("projections", [])]
                measure = [v["queryRef"] for v in projections["Y"]["projections"]]
                if measure != ["mart_network_monthly.Arrival Delay 15+ Rate"]:
                    raise ValueError(f"Seasonal measure changed: {path}")
                if original == ["dim_month.month_label"] and not years:
                    seasonal_overlay_chart(content)
                    changes[path] = content
                elif (original == ["dim_month.calendar_month"]
                      and years == ["dim_month.calendar_year"]):
                    objects = content["visual"].setdefault("objects", {})
                    desired_axis = [{"properties": {
                        "axisType": {"expr": {"Literal": {"Value": "'Categorical'"}}}
                    }}]
                    current_axis = objects.get("categoryAxis")
                    if current_axis is None:
                        objects["categoryAxis"] = desired_axis
                        changes[path] = content
                    elif current_axis != desired_axis:
                        raise ValueError(f"Seasonal axis customized: {path}")
                else:
                    raise ValueError(f"Custom seasonal visual: {path}")
                continue

            category = projections["Category"]["projections"]
            if len(category) != 1:
                raise ValueError(f"Category projection changed: {path}")
            item = category[0]
            prop = item["field"]["Column"]["Property"]
            expected_label = FRIENDLY.get(prop)
            if expected_label and item.get("displayName") is None:
                item["displayName"] = expected_label
                changes[path] = content
            elif expected_label and item.get("displayName") != expected_label:
                raise ValueError(f"Customized category caption: {path}")

        if spec["key"] == "seasonal":
            path = _visual(pages, page_id, "left-label")
            content = _load(path)
            label = (content["visual"]["objects"]["general"][0]["properties"]
                     ["paragraphs"][0]["textRuns"][0])
            previous = label["value"]
            if ("24-MONTH SEQUENCE" in previous
                    or "2024 vs 2025 ? SAME CALENDAR MONTH" in previous):
                label["value"] = spec["left_title"]
                changes[path] = content
            elif previous != spec["left_title"]:
                raise ValueError(f"Seasonal label was customized: {path}")

    return changes


def apply_finish(pages: Path = PAGES) -> list[Path]:
    changes = plan_finish(pages)
    for path, value in changes.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".dashboard-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as out:
                out.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return list(changes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply scoped dashboard finalization")
    args = parser.parse_args()
    if args.apply:
        modified = apply_finish()
        print(f"Applied {len(modified)} dashboard changes")
    else:
        print(f"Dry run: {len(plan_finish())} dashboard files would change")
