"""Targeted, idempotent PBIR repair without regenerating saved Desktop pages.

Use --apply only after the Power BI Desktop window reports no unsaved changes.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from src.phase5.build_atlas_report import PAGES, PAGES_SPEC, chart, uid, year_slicer

OLD_SUBTITLE = (28, 82, 1200, 24)
MID_SUBTITLE = (520, 58, 730, 30)
NEW_SUBTITLE = (420, 58, 540, 30)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _route_definition(page_id: str) -> dict:
    spec = PAGES_SPEC[2]
    kind, categories, measures = spec["right"]
    assert kind == "tableEx"
    return chart(page_id, "right-chart", kind, categories, measures, 700, 552, 24)


def plan_repair(pages: Path = PAGES) -> dict[Path, dict]:
    metadata = _load(pages / "pages.json")
    page_ids = metadata["pageOrder"]
    if len(page_ids) != len(PAGES_SPEC):
        raise ValueError("Unexpected number of pages; refuse selective repair")

    changes: dict[Path, dict] = {}
    for page_id, spec in zip(page_ids, PAGES_SPEC):
        page = _load(pages / page_id / "page.json")
        if page["displayName"] != spec["title"]:
            raise ValueError("Page order changed; refuse repair")
        subtitle_path = pages / page_id / "visuals" / uid(page_id, "subtitle") / "visual.json"
        current = _load(subtitle_path)
        if current["name"] != uid(page_id, "subtitle"):
            raise ValueError("Subtitle identity changed")
        pos = current["position"]
        coordinates = tuple(pos[k] for k in ("x", "y", "width", "height"))
        if coordinates not in (OLD_SUBTITLE, MID_SUBTITLE, NEW_SUBTITLE):
            raise ValueError(f"Customized subtitle layout: {subtitle_path}")
        if current["visual"]["visualType"] != "textbox":
            raise ValueError(f"Unexpected subtitle type in {subtitle_path}")
        runs = current["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"]
        if runs[0]["value"] != spec["subtitle"]:
            raise ValueError(f"Subtitle text has user changes: {subtitle_path}")
        if runs[0]["textStyle"]["color"] not in ("#586D80", "#CFE8F0"):
            raise ValueError(f"Customized subtitle color: {subtitle_path}")
        if coordinates != NEW_SUBTITLE or runs[0]["textStyle"]["color"] != "#CFE8F0":
            pos.update(dict(zip(("x", "y", "width", "height"), NEW_SUBTITLE)))
            runs[0]["textStyle"]["color"] = "#CFE8F0"
            changes[subtitle_path] = current

        year = year_slicer(page_id)
        year_path = pages / page_id / "visuals" / year["name"] / "visual.json"
        if year_path.exists():
            existing = _load(year_path)
            actual_query = existing["visual"]["query"]["queryState"]
            desired_query = year["visual"]["query"]["queryState"]
            # Desktop saves the selected single-field slicer level with
            # active=true. This default is not a user customization.
            actual_projections = actual_query.get("Values", {}).get("projections", [])
            desired_projections = desired_query["Values"]["projections"]
            normalized = [
                {k: v for k, v in projection.items() if k != "active"}
                if projection.get("active", True) is True else projection
                for projection in actual_projections
            ]
            if (existing["name"] != year["name"]
                    or existing["visual"]["visualType"] != "slicer"
                    or set(actual_query) != {"Values"}
                    or normalized != desired_projections
                    or existing["visual"].get("syncGroup")
                    != year["visual"]["syncGroup"]):
                raise ValueError(f"Year slicer was customized: {year_path}")
        else:
            changes[year_path] = year

    routes_id = page_ids[2]
    route_path = pages / routes_id / "visuals" / uid(routes_id, "right-chart") / "visual.json"
    route = _load(route_path)
    if route["name"] != uid(routes_id, "right-chart"):
        raise ValueError("Route visual identity changed")
    kind = route["visual"]["visualType"]
    expected = _route_definition(routes_id)
    if kind == "pivotTable":
        rows = route["visual"]["query"]["queryState"]["Rows"]["projections"]
        refs = [r["queryRef"] for r in rows]
        if refs != ["dim_origin_airport.airport_code", "dim_dest_airport.airport_code"]:
            raise ValueError("Route matrix changed; refuse to replace it")
        route["visual"] = expected["visual"]
        changes[route_path] = route
    elif kind == "tableEx":
        # Desktop drops isDefaultSort=false during Save. Compare the material
        # field bindings and sort definition, not the omitted default flag.
        query = route["visual"]["query"]
        desired = expected["visual"]["query"]
        actual_sort = query.get("sortDefinition", {})
        desired_sort = desired["sortDefinition"]
        if (query.get("queryState") != desired["queryState"]
                or actual_sort.get("sort") != desired_sort["sort"]
                or actual_sort.get("isDefaultSort", False)):
            raise ValueError("The existing route table has user edits")
    else:
        raise ValueError(f"Unexpected route visual type: {kind}")

    # Give the four route columns enough width while retaining a readable
    # airport delay-rate bar chart. Scope these changes to the routes page.
    geometry = [
        ("left-chart", (28, 263, 808, 387), (28, 263, 650, 387)),
        ("right-chart", (860, 263, 392, 387), (700, 263, 552, 387)),
        ("right-label", (864, 226, 385, 28), (700, 226, 552, 28)),
    ]
    for role, old, new in geometry:
        path = pages / routes_id / "visuals" / uid(routes_id, role) / "visual.json"
        content = changes.get(path) or _load(path)
        position = content["position"]
        coordinates = tuple(position[k] for k in ("x", "y", "width", "height"))
        if coordinates not in (old, new):
            raise ValueError(f"Customized route layout: {path}")
        if coordinates != new:
            position.update(dict(zip(("x", "y", "width", "height"), new)))
            changes[path] = content
    return changes


def apply_repair(pages: Path = PAGES) -> list[Path]:
    changes = plan_repair(pages)
    changed = []
    for path, value in changes.items():
        serialized = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".pbir-repair-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(serialized)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        changed.append(path)
    return changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply targeted PBIR changes without regenerating pages")
    opts = parser.parse_args()
    if opts.apply:
        affected = apply_repair()
        print(f"Applied {len(affected)} targeted PBIR repairs")
    else:
        print(f"Dry run: {len(plan_repair())} visual files would change")
