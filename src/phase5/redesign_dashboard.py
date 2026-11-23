"""Scoped Flight Deck UI redesign for the existing Power BI Desktop project.

Preserve the imported model, page ids, filters and desktop-normalized visuals.
Only touch explicitly enumerated report design elements; use --apply after
verifying the live Desktop instance has no unsaved edits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from src.phase5.build_atlas_report import (
    NAV_TABS,
    NAVY,
    PAGES,
    PAGES_SPEC,
    PALE,
    PALETTE,
    REPORT,
    TEAL,
    chart,
    color,
    home_button,
    navigation_button,
    uid,
    year_slicer,
)

OLD_RIGHT_PREFIX = {
    "executive": "SCHEDULED FLIGHTS",
    "seasonal": "SCHEDULED VOLUME",
    "causes": "SHARE OF CAUSE MINUTES",
}
PALETTE_BY_ROLE = {
    ("executive", "left-chart"): "#F26852",
    ("airline", "left-chart"): "#F26852",
    ("airline", "right-chart"): "#1665ED",
    ("airports", "left-chart"): "#1665ED",
    ("causes", "left-chart"): "#1665ED",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _visual(root: Path, page: str, role: str) -> Path:
    return root / page / "visuals" / uid(page, role) / "visual.json"


def _save_if_changed(changes: dict[Path, dict], path: Path, value: dict) -> None:
    if not path.is_file() or _load(path) != value:
        changes[path] = value


def _preserve_desktop_active(current: dict, desired: dict) -> None:
    """Desktop persists active=true for visible category levels by default."""
    old_state = current.get("queryState", {})
    new_state = desired.get("queryState", {})
    for role, new_level in new_state.items():
        old = old_state.get(role, {}).get("projections", [])
        for projection in new_level.get("projections", []):
            match = next((p for p in old
                          if p.get("queryRef") == projection.get("queryRef")), None)
            if match is not None and match.get("active") is True:
                projection["active"] = True


def _style_chart(visual: dict, page_key: str, role: str) -> None:
    theme = PALETTE_BY_ROLE.get((page_key, role))
    if not theme or visual["visual"]["visualType"] not in (
            "clusteredBarChart", "clusteredColumnChart"):
        return
    obj = visual["visual"].setdefault("objects", {})
    obj["dataPoint"] = [{"properties": {"defaultColor": color(theme)}}]


def _check_role(file: Path, data: dict, visual_type: str) -> None:
    if data.get("name") != file.parent.name or data["visual"]["visualType"] != visual_type:
        raise ValueError(f"Visual customized or changed type: {file}")


def plan_redesign(pages: Path = PAGES, report: Path = REPORT,
                  theme_src: Path = PALETTE) -> dict[Path, dict]:
    page_ids = _load(pages / "pages.json")["pageOrder"]
    if len(page_ids) != 5:
        raise ValueError("Expected five approved report pages")
    changes: dict[Path, dict] = {}

    for page_index, (page_id, spec) in enumerate(zip(page_ids, PAGES_SPEC)):
        if _load(pages / page_id / "page.json")["displayName"] != spec["title"]:
            raise ValueError("Unexpected page definition")
        key = spec["key"]
        path = pages / page_id / "page.json"
        meta = _load(path)
        meta["objects"]["background"][0]["properties"]["color"] = color(PALE)
        _save_if_changed(changes, path, meta)

        for role, new_fill in (("navy-header", NAVY), ("teal-accent", TEAL)):
            path = _visual(pages, page_id, role)
            v = _load(path)
            _check_role(path, v, "shape")
            v["visual"]["objects"]["fill"][0]["properties"]["fillColor"] = color(new_fill)
            _save_if_changed(changes, path, v)

        path = _visual(pages, page_id, "metrics")
        v = _load(path)
        _check_role(path, v, "cardVisual")
        for section, fg in (("value", "#102238"), ("label", "#45617C")):
            v["visual"]["objects"][section][0]["properties"]["fontColor"] = color(fg)
        v["visual"]["objects"]["value"][0]["properties"]["bold"] = {
            "expr": {"Literal": {"Value": "true"}},
        }
        v["visual"].setdefault("visualContainerObjects", {})["background"] = [
            {"properties": {
                "show": {"expr": {"Literal": {"Value": "true"}}},
                "color": color("#122E48"),
                "transparency": {"expr": {"Literal": {"Value": "0D"}}},
            }},
        ]
        if key == "airports":
            from src.phase5.build_atlas_report import field
            v["visual"]["query"]["queryState"]["Data"]["projections"] = [
                field(table, metric, "Measure") for table, metric in spec["cards"]
            ]
        _save_if_changed(changes, path, v)

        # Preserve the year slicer's query and current filter context.
        path = _visual(pages, page_id, "year-slicer")
        v = _load(path)
        _check_role(path, v, "slicer")
        if v["visual"]["query"]["queryState"]["Values"]["projections"][0]["queryRef"] \
                != "dim_month.calendar_year":
            raise ValueError(f"Year slicer field modified: {path}")
        ideal = year_slicer(page_id)
        for part in ("header", "items", "dropdown"):
            v["visual"].setdefault("objects", {})[part] = ideal["visual"]["objects"][part]
        for part in ("background", "border"):
            v["visual"].setdefault("visualContainerObjects", {})[part] = (
                ideal["visual"]["visualContainerObjects"][part]
            )
        _save_if_changed(changes, path, v)

        path = _visual(pages, page_id, "nav-home")
        ideal = home_button(page_id, page_ids[0])
        if path.exists():
            existing = _load(path)
            _check_role(path, existing, "actionButton")
            actual_link = (existing["visual"]["visualContainerObjects"]
                           ["visualLink"][0]["properties"]["navigationSection"])
            expected_link = (ideal["visual"]["visualContainerObjects"]
                             ["visualLink"][0]["properties"]["navigationSection"])
            if actual_link != expected_link:
                raise ValueError(f"Home navigation target customized: {path}")
            position = existing["position"]
            if (position["x"], position["width"]) not in ((258, 68), (278, 44),
                                                            (264, 68)):
                raise ValueError(f"Home button moved by user: {path}")
            position.update({"x": 264, "width": 68})
            _save_if_changed(changes, path, existing)
        else:
            changes[path] = ideal

        for index, (nav_key, label) in enumerate(NAV_TABS):
            path = _visual(pages, page_id, "nav-" + nav_key)
            v = _load(path)
            _check_role(path, v, "actionButton")
            desired = navigation_button(page_id, nav_key, label, page_ids[index],
                                        index, nav_key == key)
            old_link = (v["visual"]["visualContainerObjects"]["visualLink"][0]
                        ["properties"]["navigationSection"])
            new_link = (desired["visual"]["visualContainerObjects"]["visualLink"][0]
                        ["properties"]["navigationSection"])
            if old_link != new_link:
                raise ValueError(f"Page nav target changed: {path}")
            v["visual"]["objects"]["fill"] = desired["visual"]["objects"]["fill"]
            v["visual"]["visualContainerObjects"]["visualLink"] = (
                desired["visual"]["visualContainerObjects"]["visualLink"]
            )
            _save_if_changed(changes, path, v)

        for role in ("left-chart", "right-chart"):
            path = _visual(pages, page_id, role)
            v = _load(path)
            if (key, role) in {
                    ("executive", "right-chart"),
                    ("seasonal", "left-chart"),
                    ("seasonal", "right-chart")}:
                expected = {
                    ("executive", "right-chart"): (
                        "cardVisual", "Data",
                        ["mart_network_monthly.Executive Arrival Risk YoY"]),
                    ("seasonal", "left-chart"): (
                        "pivotTable", "Values",
                        ["mart_network_monthly.Delay Rate 2024 Fixed",
                         "mart_network_monthly.Delay Rate 2025 Fixed"]),
                    ("seasonal", "right-chart"): (
                        "clusteredBarChart", "Y",
                        ["mart_network_monthly.Delay Rate YoY pp"]),
                }[(key, role)]
                kind, slot, expected_refs = expected
                if v["visual"]["visualType"] != kind:
                    raise ValueError(f"Unexpected new comparison chart: {path}")
                projections = v["visual"]["query"]["queryState"][slot]["projections"]
                if [item["queryRef"] for item in projections] != expected_refs:
                    raise ValueError(f"Unexpected comparison measures: {path}")
                continue
            if key == "causes" and role == "right-chart":
                if v["visual"]["visualType"] not in ("clusteredColumnChart", "donutChart"):
                    raise ValueError("Delay cause right chart customized")
                desired = chart(page_id, role, "donutChart", spec["right"][1],
                                spec["right"][2], 860, 392, 24)
                old_type = v["visual"]["visualType"]
                v["visual"]["visualType"] = "donutChart"
                _preserve_desktop_active(v["visual"]["query"],
                                         desired["visual"]["query"])
                v["visual"]["query"] = desired["visual"]["query"]
                if old_type != "donutChart":
                    v["visual"].pop("objects", None)
            elif ((key in ("executive", "seasonal")) and role == "right-chart"):
                if v["visual"]["visualType"] != "clusteredColumnChart":
                    raise ValueError(f"Comparison visual customized: {path}")
                desired = chart(page_id, role, "clusteredColumnChart",
                                spec["right"][1], spec["right"][2], 860, 392, 24)
                _preserve_desktop_active(v["visual"]["query"],
                                         desired["visual"]["query"])
                v["visual"]["query"] = desired["visual"]["query"]
                if key == "seasonal":
                    v["visual"].setdefault("objects", {})["categoryAxis"] = (
                        desired["visual"]["objects"]["categoryAxis"]
                    )
                    v["position"].update({"x": 700, "width": 552})
            else:
                if v["visual"]["visualType"] not in (
                        "clusteredColumnChart", "clusteredBarChart",
                        "lineChart", "tableEx", "scatterChart",
                        "treemap", "stackedAreaChart"):
                    raise ValueError(f"Unexpected chart type: {path}")
                if v["visual"]["visualType"] == "clusteredBarChart":
                    query = v["visual"]["query"]
                    y = query["queryState"]["Y"]["projections"][0]["field"]
                    query["sortDefinition"] = {
                        "sort": [{"field": y, "direction": "Descending"}],
                    }
                if (key == "airline" and role == "right-chart"
                        and v["visual"]["visualType"] == "clusteredColumnChart"):
                    query = v["visual"]["query"]
                    y = query["queryState"]["Y"]["projections"][0]["field"]
                    query["sortDefinition"] = {
                        "sort": [{"field": y, "direction": "Descending"}],
                    }
                if key == "airports" and role == "left-chart":
                    from src.phase5.build_atlas_report import field
                    state = v["visual"]["query"]["queryState"]
                    current = state["Y"]["projections"][0]["queryRef"]
                    if current == "mart_route_monthly.Route Scheduled Flights":
                        actual = [x["queryRef"] for x in
                                  state["Category"]["projections"]]
                        if actual != ["dim_origin_airport.state_code",
                                      "dim_origin_airport.airport_code"]:
                            raise ValueError(f"Unexpected origin drill path: {path}")
                        tooltip = state.get("Tooltips", {}).get("projections", [])
                        if [x["queryRef"] for x in tooltip] != [
                                "mart_route_monthly.Route Delay 15+ Rate"]:
                            raise ValueError(f"Unexpected route tooltip: {path}")
                    elif current in (
                            "mart_airport_daily.Origin Delay 15+ Rate",
                            "mart_airport_daily.Origin Scheduled Flights"):
                        state["Y"] = {"projections": [
                            field("mart_airport_daily", "Origin Scheduled Flights",
                                  "Measure")
                        ]}
                        state["Tooltips"] = {"projections": [
                            field("mart_airport_daily", "Origin Delay 15+ Rate",
                                  "Measure")
                        ]}
                    else:
                        raise ValueError(f"Unexpected origin chart metric: {path}")
                    metric = state["Y"]["projections"][0]["field"]
                    v["visual"]["query"]["sortDefinition"] = {
                        "sort": [{"field": metric, "direction": "Descending"}],
                    }
            if key == "seasonal" and role == "left-chart":
                v["position"].update({"width": 650})
            _style_chart(v, key, role)
            _save_if_changed(changes, path, v)

        path = _visual(pages, page_id, "brand")
        v = _load(path)
        run = (v["visual"]["objects"]["general"][0]["properties"]
               ["paragraphs"][0]["textRuns"][0])
        if "FLIGHT OPERATIONS" not in run["value"] and "FLIGHT OPS" not in run["value"]:
            raise ValueError(f"Unexpected brand line: {path}")
        run["value"] = "FLIGHT OPS  /  NETWORK INTELLIGENCE"
        v["position"]["width"] = 260
        _save_if_changed(changes, path, v)

        if key in OLD_RIGHT_PREFIX:
            path = _visual(pages, page_id, "right-label")
            v = _load(path)
            run = (v["visual"]["objects"]["general"][0]["properties"]
                   ["paragraphs"][0]["textRuns"][0])
            existing = run["value"]
            desired = spec["right_title"]
            if existing != desired:
                if (OLD_RIGHT_PREFIX[key] not in existing
                        and not (key == "causes"
                                 and existing == "DELAY MINUTES / CAUSE MIX")):
                    raise ValueError(f"Right label changed by user: {path}")
                run["value"] = desired
            if key == "seasonal":
                v["position"].update({"x": 700, "width": 552})
            _save_if_changed(changes, path, v)

        if key == "airports":
            path = _visual(pages, page_id, "left-label")
            v = _load(path)
            run = (v["visual"]["objects"]["general"][0]["properties"]
                   ["paragraphs"][0]["textRuns"][0])
            desired_label = (spec["left_title"]
                             if len(spec["left"][1]) > 1
                             else "BUSIEST ORIGIN AIRPORTS / FLIGHT VOLUME")
            if run["value"] != desired_label:
                if ("ORIGIN AIRPORT" not in run["value"]
                        and "AIRPORT ARRIVAL DELAY RATE" not in run["value"]
                        and "BUSIEST ORIGIN AIRPORTS" not in run["value"]):
                    raise ValueError(f"Airport chart title modified: {path}")
                run["value"] = desired_label
            _save_if_changed(changes, path, v)

    source_theme = _load(theme_src)
    digest = hashlib.sha256(theme_src.read_bytes()).hexdigest()[:10]
    theme_name = f"FlightDeck-{digest}.json"
    source_theme["name"] = theme_name
    theme_path = report / "StaticResources" / "RegisteredResources" / theme_name
    _save_if_changed(changes, theme_path, source_theme)
    report_file = report / "definition" / "report.json"
    report_data = _load(report_file)
    custom = report_data["themeCollection"]["customTheme"]
    custom["name"] = theme_name
    resources = [x for x in report_data["resourcePackages"]
                 if x["name"] == "RegisteredResources"]
    if len(resources) != 1:
        raise ValueError("Unexpected theme resource package count")
    resources[0]["items"] = [{
        "name": theme_name, "path": theme_name, "type": "CustomTheme",
    }]
    _save_if_changed(changes, report_file, report_data)
    return changes


def apply_redesign() -> list[Path]:
    planned = plan_redesign()
    for path, value in planned.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix=".flight-deck-",suffix=".tmp",dir=path.parent)
        try:
            with os.fdopen(fd,"w",encoding="utf-8",newline="\n") as f:
                f.write(json.dumps(value,ensure_ascii=False,indent=2)+"\n")
            os.replace(temp,path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
    return list(planned)


if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()
    if args.apply:
        print(f"Applied {len(apply_redesign())} scoped design edits")
    else:
        print(f"Dry run: {len(plan_redesign())} files would change")
