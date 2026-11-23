"""Apply the Executive scorecard and Seasonal YoY heatmap to two PBIR pages.

The three approved analytical pages are intentionally excluded. Desktop
normalization is tolerated without rewriting unrelated metadata on reruns.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from src.phase5.build_atlas_report import (
    PAGES,
    PAGES_SPEC,
    color,
    expression_literal,
    field,
    uid,
    visual,
)

TABLE = "mart_network_monthly"
MONTH = "dim_month"
PREVIOUS = {
    ("executive", "right-chart"): (
        "clusteredColumnChart",
        ["dim_month.calendar_year"],
        ["mart_network_monthly.Cancellation Rate",
         "mart_network_monthly.Diversion Rate"],
    ),
    ("seasonal", "left-chart"): (
        "lineChart", ["dim_month.calendar_month"],
        ["mart_network_monthly.Arrival Delay 15+ Rate"],
    ),
    ("seasonal", "right-chart"): (
        "clusteredColumnChart", ["dim_month.calendar_month"],
        ["mart_network_monthly.Scheduled Flights"],
    ),
}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def vpath(root: Path, page: str, role: str) -> Path:
    return root / page / "visuals" / uid(page, role) / "visual.json"


def selected_roles(item: dict) -> tuple[list[str], list[str]]:
    qs = item["visual"]["query"]["queryState"]
    axes = ("Category", "Rows")
    amounts = ("Y", "Values", "Data")
    return (
        [p["queryRef"] for axis in axes
         for p in qs.get(axis, {}).get("projections", [])],
        [p["queryRef"] for axis in amounts
         for p in qs.get(axis, {}).get("projections", [])],
    )


def _literal_fill_rule(measure_name: str) -> dict:
    return {
        "properties": {
            "backColor": {
                "solid": {"color": {"expr": {"FillRule": {
                    "Input": {"SelectRef": {
                        "ExpressionName": f"{TABLE}.{measure_name}",
                    }},
                    "FillRule": {"linearGradient2": {
                        "min": {"color": {"Literal": {"Value": "'#E4F1FA'"}}},
                        "max": {"color": {"Literal": {"Value": "'#F26852'"}}},
                        "nullColoringStrategy": {
                            "strategy": {"Literal": {"Value": "'noColor'"}},
                        },
                    }},
                }}}},
            },
        },
        "selector": {
            "data": [{"dataViewWildcard": {"matchingOption": 1}}],
            "metadata": f"{TABLE}.{measure_name}",
        },
    }


def heatmap(page: str, prior: dict) -> dict:
    out = prior
    v = out["visual"]
    v["visualType"] = "pivotTable"
    rates = ["Delay Rate 2024 Fixed", "Delay Rate 2025 Fixed"]
    v["query"] = {"queryState": {
        "Rows": {"projections": [{
            **field(MONTH, "calendar_month", "Column"), "displayName": "Month",
        }]},
        "Values": {"projections": [{
            **field(TABLE, measure, "Measure"), "displayName": year,
        } for year, measure in zip(("2024", "2025"), rates)]},
    }}
    v["objects"] = {
        "columnHeaders": [{"properties": {
            "columnAdjustment": expression_literal("'growToFit'"),
            "autoSizeColumnWidth": expression_literal("true"),
            "fontSize": expression_literal("12D"),
            "bold": expression_literal("true"),
            "fontColor": color("#FFFFFF"),
            "backColor": color("#183D58"),
        }}],
        "rowHeaders": [{"properties": {
            "fontSize": expression_literal("12D"),
            "bold": expression_literal("true"),
            "fontColor": color("#183D58"),
            "backColor": color("#E6EFF6"),
        }}],
        "grid": [{"properties": {
            "rowPadding": expression_literal("0D"),
            "gridHorizontal": expression_literal("true"),
            "gridHorizontalColor": color("#DCE7F1"),
        }}],
        "values": [
            {"properties": {
                "fontSize": expression_literal("12D"),
                "fontColor": color("#11263E"),
            }},
            *[_literal_fill_rule(m) for m in rates],
        ],
    }
    v["visualContainerObjects"] = {
        **v.get("visualContainerObjects", {}),
        "stylePreset": [{"properties": {"name": expression_literal("'None'")}}],
        "title": [{"properties": {"show": expression_literal("false")}}],
        "subTitle": [{"properties": {"show": expression_literal("false")}}],
    }
    out["position"].update({"x": 28, "width": 650})
    return out


def _sign_rule() -> dict:
    measure = field(TABLE, "Delay Rate YoY pp", "Measure")["field"]["Measure"]
    def case(kind: int, shade: str) -> dict:
        return {
            "Condition": {"Comparison": {
                "ComparisonKind": kind,
                "Left": {"Measure": measure},
                "Right": {"Literal": {"Value": "0D"}},
            }},
            "Value": {"Literal": {"Value": f"'{shade}'"}},
        }
    return {
        "properties": {
            "fill": {"solid": {"color": {"expr": {
                "Conditional": {"Cases": [
                    case(2, "#E75E4E"),  # Increase in delayed-arrival rate
                    case(3, "#0098AE"),  # Improvement
                ]},
            }}}},
        },
        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]},
    }


def diverging_bar(page: str, prior: dict) -> dict:
    out = prior
    v = out["visual"]
    v["visualType"] = "clusteredBarChart"
    month = field(MONTH, "calendar_month", "Column")
    month["displayName"] = "Month"
    v["query"] = {
        "queryState": {
            "Category": {"projections": [month]},
            "Y": {"projections": [
                {**field(TABLE, "Delay Rate YoY pp", "Measure"),
                 "displayName": "2025 - 2024 (pp)"},
            ]},
            "Tooltips": {"projections": [
                field(TABLE, "Delay Rate 2024 Fixed", "Measure"),
                field(TABLE, "Delay Rate 2025 Fixed", "Measure"),
            ]},
        },
        "sortDefinition": {"sort": [{
            "field": month["field"], "direction": "Ascending",
        }]},
    }
    v["objects"] = {
        "dataPoint": [_sign_rule()],
        "categoryAxis": [{"properties": {
            "axisType": expression_literal("'Categorical'"),
        }}],
        "labels": [{"properties": {
            "show": expression_literal("true"),
            "fontSize": expression_literal("10D"),
            "color": color("#193954"),
        }}],
        "legend": [{"properties": {"show": expression_literal("false")}}],
    }
    v["visualContainerObjects"] = {
        **v.get("visualContainerObjects", {}),
        "title": [{"properties": {"show": expression_literal("false")}}],
        "subTitle": [{"properties": {"show": expression_literal("false")}}],
    }
    out["position"].update({"x": 700, "width": 552})
    return out


def scorecard_item(page: str, role: str, metric: str, caption: str,
                   index: int, previous: dict | None) -> dict:
    out = (previous if previous is not None
           else visual(page, role, 860, 263, 392, 116, "cardVisual", 24 + index))
    out["position"].update({
        "x": 860, "y": 263 + index * 129,
        "width": 392, "height": 116,
    })
    v = out["visual"]
    v["visualType"] = "cardVisual"
    v["query"] = {"queryState": {"Data": {"projections": [{
        **field(TABLE, metric, "Measure"), "displayName": caption,
    }]}}}
    v["objects"] = {
        "value": [{"properties": {
            "fontSize": expression_literal("18D"),
            "fontColor": color("#C94D44"),
            "bold": expression_literal("true"),
            "textWrap": expression_literal("false"),
        }, "selector": {"id": "default"}}],
        "label": [{"properties": {
            "show": expression_literal("true"),
            "fontSize": expression_literal("12D"),
            "fontColor": color("#173D5A"),
            "bold": expression_literal("true"),
            "position": expression_literal("'aboveValue'"),
        }, "selector": {"id": "default"}}],
    }
    v["visualContainerObjects"] = {
        "background": [{"properties": {
            "show": expression_literal("true"),
            "color": color("#F9FCFF"),
            "transparency": expression_literal("0D"),
        }}],
        "border": [{"properties": {
            "show": expression_literal("true"),
            "color": color("#D3E3EF"),
        }}],
        "padding": [{"properties": {
            side: expression_literal("8D")
            for side in ("top", "bottom", "left", "right")
        }}],
        "title": [{"properties": {"show": expression_literal("false")}}],
    }
    return out


def plan(root: Path = PAGES) -> dict[Path, dict]:
    ids = read(root / "pages.json")["pageOrder"]
    if len(ids) != 5:
        raise ValueError("Expected five-page canonical report")
    names = {s["key"]: s for s in PAGES_SPEC}
    changes: dict[Path, dict] = {}
    for key, ix in (("executive", 0), ("seasonal", 4)):
        page = ids[ix]
        meta = read(root / page / "page.json")
        if meta["displayName"] != names[key]["title"]:
            raise ValueError(f"Unexpected page {ix}")
        for role, title in (
            ("left-label", names[key]["left_title"]),
            ("right-label", names[key]["right_title"]),
            ("footer", names[key]["footer"]),
        ):
            path = vpath(root, page, role)
            item = read(path)
            text = (item["visual"]["objects"]["general"][0]["properties"]
                    ["paragraphs"][0]["textRuns"][0])
            current = text["value"]
            if current == title:
                continue
            if role == "left-label":
                allowed = ("ARRIVAL DELAY RATE", "DELAY RATE")
            elif role == "right-label":
                allowed = ("RELIABILITY / CANCELLATIONS", "MONTHLY DEMAND")
            else:
                allowed = ("Historical BTS records", "Ratios are recomputed")
            if not current.startswith(allowed):
                raise ValueError(f"Customized text; preserve: {path}")
            text["value"] = title
            if key == "seasonal" and role == "left-label":
                item["position"]["width"] = 650
            changes[path] = item

        if key == "executive":
            path = vpath(root, page, "right-chart")
            item = read(path)
            previous_type, cats, vals = PREVIOUS[(key, "right-chart")]
            kind = item["visual"]["visualType"]
            current_cat, current_val = selected_roles(item)
            if kind == previous_type:
                if (current_cat, current_val) != (cats, vals):
                    raise ValueError(f"Executive visual modified: {path}")
                edited = scorecard_item(
                    page, "right-chart", "Executive Arrival Risk YoY",
                    "ARRIVAL DELAY / 2024 -> 2025", 0, item)
                changes[path] = edited
            elif kind != "cardVisual" or current_val != [
                    f"{TABLE}.Executive Arrival Risk YoY"]:
                raise ValueError(f"Unexpected scorecard: {path}")
            for index, role, metric, label in [
                (1, "risk-cancellation", "Executive Cancellation Risk YoY",
                 "CANCELLATION / 2024 -> 2025"),
                (2, "risk-diversion", "Executive Diversion Risk YoY",
                 "DIVERSION / 2024 -> 2025"),
            ]:
                path = vpath(root, page, role)
                if not path.exists():
                    changes[path] = scorecard_item(
                        page, role, metric, label, index, None)
                else:
                    existing = read(path)
                    if existing["visual"]["visualType"] != "cardVisual":
                        raise ValueError(f"Unexpected scorecard: {path}")
                    _, current_measures = selected_roles(existing)
                    if current_measures != [f"{TABLE}.{metric}"]:
                        raise ValueError(f"Scorecard measure customized: {path}")
        else:
            for role, builder, desired, expected_roles in (
                ("left-chart", heatmap, "pivotTable",
                 ([f"{MONTH}.calendar_month"],
                  [f"{TABLE}.Delay Rate 2024 Fixed",
                   f"{TABLE}.Delay Rate 2025 Fixed"])),
                ("right-chart", diverging_bar, "clusteredBarChart",
                 ([f"{MONTH}.calendar_month"],
                  [f"{TABLE}.Delay Rate YoY pp"])),
            ):
                path = vpath(root, page, role)
                item = read(path)
                actual = selected_roles(item)
                original, oldcats, oldvals = PREVIOUS[(key, role)]
                if item["visual"]["visualType"] == original:
                    if actual != (oldcats, oldvals):
                        raise ValueError(f"Unexpected previous chart: {path}")
                    changes[path] = builder(page, item)
                elif item["visual"]["visualType"] != desired or actual != expected_roles:
                    raise ValueError(f"User-customized chart: {path}")
    return changes


def apply(root: Path = PAGES) -> list[Path]:
    changes = plan(root)
    for path, item in changes.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            prefix=".yo-y-", suffix=".tmp", dir=path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as out:
                out.write(json.dumps(item, indent=2, ensure_ascii=False) + "\n")
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return list(changes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.apply:
        print(f"Applied {len(apply())} PBIR file edits")
    else:
        print(f"Dry run: {len(plan())} PBIR file edits")
