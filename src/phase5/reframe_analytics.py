"""Apply an incremental analytical chart redesign to the existing PBIP.

The edit changes only the designated visuals and text on three pages.
Page identities, slicers, links, other pages and model metadata remain intact.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from src.phase5.build_atlas_report import PAGES, PAGES_SPEC, chart, uid

OLD = {
    ("airline", "left-chart"): (
        "clusteredBarChart",
        {"Category": ["dim_airline.airline_code"],
         "Y": ["mart_airline_monthly.Airline Delay 15+ Rate"]},
    ),
    ("airline", "right-chart"): (
        "clusteredColumnChart",
        {"Category": ["dim_airline.airline_code"],
         "Y": ["mart_airline_monthly.Airline Scheduled Flights"]},
    ),
    ("airports", "left-chart"): (
        "clusteredBarChart",
        {"Category": ["dim_airport.airport_code"],
         "Y": ["mart_airport_daily.Origin Scheduled Flights"],
         "Tooltips": ["mart_airport_daily.Origin Delay 15+ Rate"]},
    ),
    ("causes", "left-chart"): (
        "clusteredBarChart",
        {"Category": ["mart_delay_causes.cause_type"],
         "Y": ["mart_delay_causes.Reported Cause Minutes"]},
    ),
}
OLD_TEXT = {
    ("airline", "left-label"): "ARRIVAL DELAY RATE",
    ("airline", "right-label"): "SCHEDULED VOLUME",
    ("airports", "left-label"): "BUSIEST ORIGIN AIRPORTS",
    ("airports", "right-label"): "DIRECTED ROUTE",
    ("causes", "left-label"): "REPORTED CAUSE MINUTES",
    ("causes", "right-label"): "DELAY MINUTES / CAUSE MIX",
}
OLD_FOOTER = {
    "airline": "Compare rates together with volume; low-sample carriers require interpretation.",
    "airports": "Route map pending validated airport geocodes. Origin and destination counts are never added together.",
    "causes": "BTS cause observations may overlap; they are not counts of distinct delayed flights or observed weather.",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def chart_path(pages: Path, page: str, role: str) -> Path:
    return pages / page / "visuals" / uid(page, role) / "visual.json"


def roles(data: dict) -> dict[str, list[str]]:
    return {
        key: [p["queryRef"] for p in slot["projections"]]
        for key, slot in data["visual"]["query"]["queryState"].items()
    }


def check_or_update(working: dict, desired: dict,
                    old_kind: str, old_roles: dict, path: Path) -> bool:
    actual_kind = working["visual"]["visualType"]
    actual_roles = roles(working)
    target_kind = desired["visual"]["visualType"]
    target_roles = roles(desired)
    if actual_kind == target_kind and actual_roles == target_roles:
        # Desktop may normalize metadata; preserve that on subsequent runs.
        if target_kind == "clusteredBarChart":
            if working["visual"].get("drillFilterOtherVisuals") is not True:
                raise ValueError(f"Airport drill interaction disabled: {path}")
        return False
    if actual_kind != old_kind or actual_roles != old_roles:
        raise ValueError(f"Unexpected chart customization in {path}: "
                         f"{actual_kind} {actual_roles}")

    working["visual"]["visualType"] = target_kind
    working["visual"]["query"] = desired["visual"]["query"]
    if actual_kind != target_kind:
        if "objects" in desired["visual"]:
            working["visual"]["objects"] = desired["visual"]["objects"]
        else:
            working["visual"].pop("objects", None)
    if "drillFilterOtherVisuals" in desired["visual"]:
        working["visual"]["drillFilterOtherVisuals"] = (
            desired["visual"]["drillFilterOtherVisuals"]
        )
    return True


def plan_reframe(pages: Path = PAGES) -> dict[Path, dict]:
    page_ids = load(pages / "pages.json")["pageOrder"]
    if len(page_ids) != 5:
        raise ValueError("Five approved report pages are required")
    specs = {spec["key"]: spec for spec in PAGES_SPEC}
    changes: dict[Path, dict] = {}
    indexes = {"airline": 1, "airports": 2, "causes": 3}
    for key, index in indexes.items():
        page_id = page_ids[index]
        spec = specs[key]
        if load(pages / page_id / "page.json")["displayName"] != spec["title"]:
            raise ValueError(f"Unexpected page at index {index}")
        for role in ("left-chart", "right-chart"):
            marker = (key, role)
            if marker not in OLD and marker != ("causes", "right-chart"):
                continue  # Preserve the directed-route table.
            path = chart_path(pages, page_id, role)
            entry = load(path)
            if entry["name"] != uid(page_id, role):
                raise ValueError(f"Chart identity changed: {path}")
            pos = entry["position"]
            kind, categories, measures = (spec["left"] if role == "left-chart"
                                           else spec["right"])
            desired = chart(page_id, role, kind, categories, measures,
                            pos["x"], pos["width"], pos["z"])
            changed = False
            if marker in OLD:
                changed = check_or_update(entry, desired, *OLD[marker], path)
            elif (entry["visual"]["visualType"] != kind
                  or roles(entry) != roles(desired)):
                raise ValueError(f"Cause share donut modified unexpectedly: {path}")
            desired_container = desired["visual"].get("visualContainerObjects", {})
            container = entry["visual"].setdefault("visualContainerObjects", {})
            for setting in ("title", "subTitle"):
                expected = desired_container[setting]
                current = container.get(setting)
                if current is not None:
                    old_properties = current[0].get("properties", {})
                    new_properties = expected[0]["properties"]
                    for name in ("show", "text"):
                        if name in old_properties and name in new_properties:
                            if old_properties[name] != new_properties[name]:
                                raise ValueError(f"User-customized {setting}: {path}")
                if current is None:
                    container[setting] = expected
                    changed = True
            if changed:
                changes[path] = entry

        for role, title in (("left-label", spec["left_title"]),
                            ("right-label", spec["right_title"]),
                            ("footer", spec["footer"])):
            path = chart_path(pages, page_id, role)
            entry = load(path)
            token = entry["visual"]["objects"]["general"][0]["properties"]
            run = token["paragraphs"][0]["textRuns"][0]
            original = run["value"]
            if original == title:
                continue
            previous = (OLD_FOOTER[key] if role == "footer"
                        else OLD_TEXT[(key, role)])
            if (original != previous if role == "footer"
                    else not original.startswith(previous)):
                raise ValueError(f"Unexpected editor-written text: {path}")
            run["value"] = title
            changes[path] = entry

    return changes


def apply_reframe(pages: Path = PAGES) -> list[Path]:
    edits = plan_reframe(pages)
    for path, data in edits.items():
        fd, temporary = tempfile.mkstemp(
            prefix=".visual-edit-", suffix=".tmp", dir=path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(data, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return list(edits)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    options = parser.parse_args()
    if options.apply:
        print(f"Applied {len(apply_reframe())} scoped report edits")
    else:
        print(f"Dry run: {len(plan_reframe())} report edits")


if __name__ == "__main__":
    main()
