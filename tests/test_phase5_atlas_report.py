"""Source-controlled acceptance checks for the Flight Network Atlas report."""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.phase5.build_atlas_report import PAGES, PAGES_SPEC, REPORT, uid
from src.phase5.build_semantic_model import DEFINITION


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_atlas_has_five_approved_pages_and_ninety_five_visuals():
    pages = _json(PAGES / "pages.json")
    assert len(PAGES_SPEC) == len(pages["pageOrder"]) == 5
    all_ids = set()
    for idx, page_id in enumerate(pages["pageOrder"]):
        page = _json(PAGES / page_id / "page.json")
        assert page["displayName"] == PAGES_SPEC[idx]["title"]
        assert (page["width"], page["height"]) == (1280, 720)
        visual_files = list((PAGES / page_id / "visuals").rglob("visual.json"))
        assert len(visual_files) == 19
        for file in visual_files:
            visual = _json(file)
            visual_id = visual["name"]
            assert re.fullmatch(r"[a-f0-9]{20}", visual_id)
            assert visual_id not in all_ids
            all_ids.add(visual_id)
            position = visual["position"]
            assert 0 <= position["x"]
            assert 0 <= position["y"]
            assert position["x"] + position["width"] <= 1280
            assert position["y"] + position["height"] <= 720
    assert len(all_ids) == 95


def test_atlas_theme_registered_from_approved_palette():
    report = _json(REPORT / "definition" / "report.json")
    custom = report["themeCollection"]["customTheme"]
    assert custom["type"] == "RegisteredResources"
    filename = custom["name"]
    theme = _json(REPORT / "StaticResources" / "RegisteredResources" / filename)
    source = _json(REPORT.parent / "themes" / "FlightNetworkRiskIntel.json")
    assert filename == theme["name"]
    assert theme["dataColors"] == source["dataColors"]
    package = next(p for p in report["resourcePackages"]
                   if p["name"] == "RegisteredResources")
    assert any(item["name"] == filename and item["path"] == filename
               for item in package["items"])


def test_all_chart_measures_exist_in_m53_tmdl_source():
    table_text = {
        file.stem: file.read_text(encoding="utf-8")
        for file in (DEFINITION / "tables").glob("*.tmdl")
    }
    references = []
    for page_id in _json(PAGES / "pages.json")["pageOrder"]:
        for visual_path in (PAGES / page_id / "visuals").rglob("visual.json"):
            config = _json(visual_path)["visual"]
            for q in config.get("query", {}).get("queryState", {}).values():
                for projection in q.get("projections", []):
                    expr = projection["field"]
                    if "Measure" not in expr:
                        continue
                    table = expr["Measure"]["Expression"]["SourceRef"]["Entity"]
                    name = expr["Measure"]["Property"]
                    references.append((table, name))
                    assert table in table_text
                    assert f"measure '{name}' =" in table_text[table], (table, name)
    assert len(references) == 32


def test_43_measures_from_the_live_mcp_export_are_retained():
    counts = {
        "mart_network_monthly": 11,
        "mart_airline_monthly": 8,
        "mart_airport_daily": 14,
        "mart_route_monthly": 7,
        "mart_delay_causes": 3,
    }
    assert sum(counts.values()) == 43
    for name, n in counts.items():
        path = DEFINITION / "tables" / f"{name}.tmdl"
        assert path.read_text(encoding="utf-8-sig").count("\tmeasure ") == n


def test_role_aware_airport_measures_and_no_unverified_geo():
    airport = (DEFINITION / "tables" / "mart_airport_daily.tmdl").read_text(
        encoding="utf-8"
    )
    assert 'airport_role] = "origin"' in airport
    assert 'airport_role] = "destination"' in airport
    pages = _json(PAGES / "pages.json")["pageOrder"]
    for page_id in pages:
        for path in (PAGES / page_id / "visuals").rglob("visual.json"):
            visual_type = _json(path)["visual"]["visualType"]
            assert visual_type not in {"map", "filledMap", "azureMap"}
    assert uid("page", "airports") in pages
