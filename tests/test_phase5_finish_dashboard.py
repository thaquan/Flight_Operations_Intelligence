"""Functional PBIR contract for the finished Flight Operations dashboard."""
import json
import shutil

from src.phase5.build_atlas_report import NAV_TABS, PAGES, uid
from src.phase5.finish_dashboard import apply_finish, plan_finish


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_all_pages_have_five_valid_page_navigation_targets():
    ids = read(PAGES / "pages.json")["pageOrder"]
    assert len(ids) == len(NAV_TABS) == 5
    for index, page in enumerate(ids):
        for tab_index, (key, label) in enumerate(NAV_TABS):
            entry = read(PAGES / page / "visuals" / uid(page, "nav-" + key) / "visual.json")
            assert entry["visual"]["visualType"] == "actionButton"
            pos = entry["position"]
            assert pos["height"] == 44 and pos["width"] == 112
            assert pos["x"] >= 336 and pos["x"] + pos["width"] <= 928
            action = entry["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]
            assert action["type"]["expr"]["Literal"]["Value"] == "'PageNavigation'"
            assert action["navigationSection"]["expr"]["Literal"]["Value"] == "'" + ids[tab_index] + "'"
            caption = entry["visual"]["objects"]["text"][1]["properties"]["text"]
            assert caption["expr"]["Literal"]["Value"] == "'" + label + "'"
            fill = entry["visual"]["objects"]["fill"][1]["properties"]["fillColor"]
            selected = fill["solid"]["color"]["expr"]["Literal"]["Value"] == "'#00BCD4'"
            assert selected == (index == tab_index)


def test_seasonal_trend_has_month_of_year_x_and_year_series():
    page = read(PAGES / "pages.json")["pageOrder"][4]
    visual = read(PAGES / page / "visuals" / uid(page, "left-chart") / "visual.json")
    q = visual["visual"]["query"]["queryState"]
    assert q["Category"]["projections"][0]["queryRef"] == "dim_month.calendar_month"
    assert q["Series"]["projections"][0]["queryRef"] == "dim_month.calendar_year"
    assert q["Y"]["projections"][0]["queryRef"] == "mart_network_monthly.Arrival Delay 15+ Rate"
    assert visual["visual"]["query"]["sortDefinition"]["sort"][0]["direction"] == "Ascending"
    axis = visual["visual"]["objects"]["categoryAxis"][0]["properties"]["axisType"]
    assert axis["expr"]["Literal"]["Value"] == "'Categorical'"
    label_path = PAGES / page / "visuals" / uid(page, "left-label") / "visual.json"
    label = read(label_path)["visual"]["objects"]["general"][0]["properties"]
    text = label["paragraphs"][0]["textRuns"][0]["value"]
    assert "SAME CALENDAR MONTH" in text and "?" not in text


def test_route_table_columns_have_clear_headers_without_changing_sources():
    page = read(PAGES / "pages.json")["pageOrder"][2]
    visual = read(PAGES / page / "visuals" / uid(page, "right-chart") / "visual.json")
    q = visual["visual"]["query"]["queryState"]["Values"]["projections"]
    assert [p["displayName"] for p in q] == [
        "Origin", "Destination", "Flights", "Delay 15+ %"
    ]
    assert [p["nativeQueryRef"] for p in q][:2] == ["airport_code", "airport_code1"]


def test_finish_dashboard_is_scoped_and_idempotent(tmp_path):
    target = tmp_path / "pages"
    shutil.copytree(PAGES, target)
    before = {p.relative_to(target): p.read_bytes() for p in target.rglob("visual.json")}
    changes = plan_finish(target)
    assert changes == {}
    assert apply_finish(target) == []
    after = {p.relative_to(target): p.read_bytes() for p in target.rglob("visual.json")}
    assert before == after
