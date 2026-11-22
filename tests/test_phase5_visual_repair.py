"""Non-destructive checks for the canonical PBIR visual repair."""

import json
import shutil

from src.phase5.build_atlas_report import PAGES, PAGES_SPEC, chart, uid
from src.phase5.repair_visuals import apply_repair, plan_repair


def test_flat_route_table_uses_distinct_native_references():
    kind, categories, measures = PAGES_SPEC[2]["right"]
    visual = chart("sample", "right-chart", kind, categories, measures, 860, 392, 24)
    assert visual["visual"]["visualType"] == "tableEx"
    projections = visual["visual"]["query"]["queryState"]["Values"]["projections"]
    assert [p["nativeQueryRef"] for p in projections[:2]] == [
        "airport_code", "airport_code1"
    ]
    assert {p["queryRef"] for p in projections[:2]} == {
        "dim_origin_airport.airport_code", "dim_dest_airport.airport_code"
    }
    assert visual["visual"]["query"]["sortDefinition"]["sort"][0]["direction"] == "Descending"


def test_repair_is_scoped_and_idempotent(tmp_path):
    pages = tmp_path / "pages"
    shutil.copytree(PAGES, pages)
    prior = {
        p.relative_to(pages): p.read_bytes()
        for p in pages.rglob("visual.json")
    }
    plan = plan_repair(pages)
    assert len(plan) in (0, 10)
    changed = apply_repair(pages)
    assert len(changed) == len(plan)
    assert not plan_repair(pages)
    assert not apply_repair(pages)
    after = {
        p.relative_to(pages): p.read_bytes()
        for p in pages.rglob("visual.json")
    }
    assert {p for p in set(prior) | set(after) if prior.get(p) != after.get(p)} == {
        p.relative_to(pages) for p in changed
    }
    page_ids = json.loads((pages / "pages.json").read_text(encoding="utf-8"))["pageOrder"]
    route_file = pages / page_ids[2] / "visuals" / uid(page_ids[2], "right-chart") / "visual.json"
    route = json.loads(route_file.read_text(encoding="utf-8"))
    assert route["visual"]["visualType"] == "tableEx"
    assert (route["position"]["x"], route["position"]["width"]) == (700, 552)
    left = pages / page_ids[2] / "visuals" / uid(page_ids[2], "left-chart") / "visual.json"
    left_chart = json.loads(left.read_text(encoding="utf-8"))
    assert left_chart["position"]["width"] == 650
    for page in page_ids:
        subtitle = pages / page / "visuals" / uid(page, "subtitle") / "visual.json"
        body = json.loads(subtitle.read_text(encoding="utf-8"))
        assert (body["position"]["x"], body["position"]["y"]) == (420, 58)
        assert body["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["textStyle"]["color"] == "#CFE8F0"
        slicer = pages / page / "visuals" / uid(page, "year-slicer") / "visual.json"
        data = json.loads(slicer.read_text(encoding="utf-8"))
        assert data["visual"]["visualType"] == "slicer"
        assert data["position"]["height"] == 80
        assert data["visual"]["query"]["queryState"]["Values"]["projections"][0]["queryRef"] == "dim_month.calendar_year"
        assert data["visual"]["syncGroup"]["groupName"] == "FlightOperationsYear"
