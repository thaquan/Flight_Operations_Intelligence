"""Acceptance contracts for Flight Deck editorial Power BI report redesign."""
from __future__ import annotations

import json

from src.phase5.build_atlas_report import NAV_TABS, PAGES, REPORT, uid
from src.phase5.redesign_dashboard import plan_redesign


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def get_visual(page, role):
    return read(PAGES / page / "visuals" / uid(page, role) / "visual.json")


def test_five_home_actions_and_all_navigation_targets():
    ids = read(PAGES / "pages.json")["pageOrder"]
    assert len(ids) == 5
    for page in ids:
        home = get_visual(page, "nav-home")
        assert home["visual"]["visualType"] == "actionButton"
        assert home["position"]["width"] == 68
        assert home["position"]["x"] == 264
        target = home["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]
        assert target["type"]["expr"]["Literal"]["Value"] == "'PageNavigation'"
        assert target["navigationSection"]["expr"]["Literal"]["Value"] == f"'{ids[0]}'"
        glyph = home["visual"]["objects"]["text"][1]["properties"]["text"]
        assert glyph["expr"]["Literal"]["Value"] == f"'{chr(0xE80F)}'"
        for ix, (key, _) in enumerate(NAV_TABS):
            link = get_visual(page, "nav-" + key)
            action = link["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]
            assert action["navigationSection"]["expr"]["Literal"]["Value"] == f"'{ids[ix]}'"
            assert "Ctrl+click" in action["tooltip"]["expr"]["Literal"]["Value"]


def test_year_slicers_integrated_with_dark_header_and_correct_keys():
    ids = read(PAGES / "pages.json")["pageOrder"]
    for page in ids:
        year = get_visual(page, "year-slicer")
        v = year["visual"]
        assert v["query"]["queryState"]["Values"]["projections"][0]["queryRef"] == "dim_month.calendar_year"
        assert v["syncGroup"]["groupName"] == "FlightOperationsYear"
        bg = v["visualContainerObjects"]["background"][0]["properties"]["color"]
        assert bg["solid"]["color"]["expr"]["Literal"]["Value"] == "'#102B43'"
        assert v["objects"]["header"][0]["properties"]["text"]["expr"]["Literal"]["Value"] == "'YEAR / PERIOD'"
        header = get_visual(page, "navy-header")
        fill = header["visual"]["objects"]["fill"][0]["properties"]["fillColor"]
        assert fill["solid"]["color"]["expr"]["Literal"]["Value"] == "'#081B30'"


def test_chart_stories_differ_and_risk_is_grain_aware():
    ids = read(PAGES / "pages.json")["pageOrder"]
    overview = get_visual(ids[0], "right-chart")["visual"]
    seasonal = get_visual(ids[4], "right-chart")["visual"]
    causes = get_visual(ids[3], "right-chart")["visual"]
    assert overview["query"]["queryState"]["Category"]["projections"][0]["queryRef"] == "dim_month.calendar_year"
    assert {v["queryRef"] for v in overview["query"]["queryState"]["Y"]["projections"]} == {
        "mart_network_monthly.Cancellation Rate",
        "mart_network_monthly.Diversion Rate",
    }
    assert seasonal["query"]["queryState"]["Category"]["projections"][0]["queryRef"] == "dim_month.calendar_month"
    assert seasonal["query"]["queryState"]["Series"]["projections"][0]["queryRef"] == "dim_month.calendar_year"
    assert seasonal["query"]["queryState"]["Y"]["projections"][0]["queryRef"] == "mart_network_monthly.Scheduled Flights"
    assert causes["visualType"] == "donutChart"
    assert causes["query"]["queryState"]["Y"]["projections"][0]["queryRef"] == "mart_delay_causes.Reported Cause Minutes"

    airports = get_visual(ids[2], "left-chart")["visual"]
    query = airports["query"]
    assert query["queryState"]["Y"]["projections"][0]["queryRef"] == "mart_airport_daily.Origin Scheduled Flights"
    assert query["queryState"]["Tooltips"]["projections"][0]["queryRef"] == "mart_airport_daily.Origin Delay 15+ Rate"
    assert query["sortDefinition"]["sort"][0]["direction"] == "Descending"
    cards = get_visual(ids[2], "metrics")["visual"]["query"]["queryState"]["Data"]["projections"]
    assert [v["queryRef"] for v in cards] == [
        "mart_route_monthly.Route Scheduled Flights",
        "mart_route_monthly.Route Delay 15+ Rate",
        "mart_route_monthly.Route Cancelled Flights",
        "mart_route_monthly.Route Diverted Flights",
    ]


def test_palette_and_card_contrast_and_reapplication_are_safe():
    theme = read(REPORT.parent / "themes" / "FlightNetworkRiskIntel.json")
    report = read(REPORT / "definition" / "report.json")
    installed = report["themeCollection"]["customTheme"]["name"]
    resource = read(REPORT / "StaticResources" / "RegisteredResources" / installed)
    assert theme["dataColors"] == resource["dataColors"]
    assert theme["dataColors"][:2] == ["#1665ED", "#F26852"]
    for page in read(PAGES / "pages.json")["pageOrder"]:
        card = get_visual(page, "metrics")
        value_color = card["visual"]["objects"]["value"][0]["properties"]["fontColor"]
        assert value_color["solid"]["color"]["expr"]["Literal"]["Value"] == "'#102238'"
    assert plan_redesign() == {}
