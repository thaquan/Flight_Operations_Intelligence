"""Acceptance contracts for Flight Deck editorial Power BI report redesign."""
from __future__ import annotations

import json

from src.phase5.build_atlas_report import NAV_TABS, PAGES, REPORT, TEAL, uid
from src.phase5.final_quality_pass import ALT, LABELS
from src.phase5.final_quality_pass import plan as plan_quality
from src.phase5.polish_executive import plan as plan_executive
from src.phase5.redesign_dashboard import plan_redesign
from src.phase5.rework_overview_seasonal import plan as plan_year_comparison


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
    assert overview["visualType"] == "cardVisual"
    assert overview["query"]["queryState"]["Data"]["projections"][0]["queryRef"] == (
        "mart_network_monthly.Executive Arrival Risk YoY"
    )
    for role, expected in [
        ("risk-cancellation", "Executive Cancellation Risk YoY"),
        ("risk-diversion", "Executive Diversion Risk YoY"),
    ]:
        extra = get_visual(ids[0], role)["visual"]
        assert extra["visualType"] == "cardVisual"
        assert extra["query"]["queryState"]["Data"]["projections"][0]["queryRef"] == (
            "mart_network_monthly." + expected
        )
    assert seasonal["visualType"] == "clusteredBarChart"
    assert seasonal["query"]["queryState"]["Category"]["projections"][0]["queryRef"] == (
        "dim_month.calendar_month"
    )
    assert seasonal["query"]["queryState"]["Y"]["projections"][0]["queryRef"] == (
        "mart_network_monthly.Delay Rate YoY pp"
    )
    assert causes["visualType"] == "donutChart"
    assert causes["query"]["queryState"]["Y"]["projections"][0]["queryRef"] == "mart_delay_causes.Reported Cause Minutes"

    airports = get_visual(ids[2], "left-chart")["visual"]
    query = airports["query"]
    # The state-to-airport hierarchy shares a directed-route grain with
    # the adjacent route table; a selected origin can filter its routes.
    levels = query["queryState"]["Category"]["projections"]
    assert [item["queryRef"] for item in levels] == [
        "dim_origin_airport.state_code", "dim_origin_airport.airport_code",
    ]
    assert [item["active"] for item in levels] == [True, False]
    assert airports["drillFilterOtherVisuals"] is True
    assert query["queryState"]["Y"]["projections"][0]["queryRef"] == "mart_route_monthly.Route Scheduled Flights"
    assert query["queryState"]["Tooltips"]["projections"][0]["queryRef"] == "mart_route_monthly.Route Delay 15+ Rate"
    assert query["sortDefinition"]["sort"][0]["direction"] == "Descending"
    cards = get_visual(ids[2], "metrics")["visual"]["query"]["queryState"]["Data"]["projections"]
    assert [v["queryRef"] for v in cards] == [
        "mart_route_monthly.Route Scheduled Flights",
        "mart_route_monthly.Route Delay 15+ Rate",
        "mart_route_monthly.Route Cancelled Flights",
        "mart_route_monthly.Route Diverted Flights",
    ]


def test_chart_variety_has_semantically_matched_fields_and_clean_titles():
    ids = read(PAGES / "pages.json")["pageOrder"]
    names = {
        (1, "left-chart"): ("scatterChart", "Carrier risk by traffic and delay"),
        (1, "right-chart"): ("treemap", "Carrier share of flight volume"),
        (2, "left-chart"): ("clusteredBarChart", "Origin traffic by state"),
        (3, "left-chart"): ("stackedAreaChart", "Attributed delay minutes over time"),
        (3, "right-chart"): ("donutChart", "Delay minutes by cause"),
    }
    for (page_number, role), (kind, title) in names.items():
        visual = get_visual(ids[page_number], role)["visual"]
        assert visual["visualType"] == kind
        objects = visual["visualContainerObjects"]
        assert objects["title"][0]["properties"]["text"]["expr"]["Literal"]["Value"] == f"'{title}'"
        assert objects["subTitle"][0]["properties"]["show"]["expr"]["Literal"]["Value"] == "false"

    bubble = get_visual(ids[1], "left-chart")["visual"]["query"]["queryState"]
    assert bubble["Category"]["projections"][0]["queryRef"] == "dim_airline.airline_code"
    assert bubble["X"]["projections"][0]["queryRef"] == "mart_airline_monthly.Airline Scheduled Flights"
    assert bubble["Y"]["projections"][0]["queryRef"] == "mart_airline_monthly.Airline Delay 15+ Rate"
    assert bubble["Size"]["projections"][0]["queryRef"] == "mart_airline_monthly.Airline Cancelled Flights"
    tree = get_visual(ids[1], "right-chart")["visual"]["query"]["queryState"]
    assert tree["Group"]["projections"][0]["queryRef"] == "dim_airline.airline_code"
    assert tree["Values"]["projections"][0]["queryRef"] == "mart_airline_monthly.Airline Scheduled Flights"
    area = get_visual(ids[3], "left-chart")["visual"]["query"]["queryState"]
    assert area["Category"]["projections"][0]["queryRef"] == "dim_month.source_month"
    assert area["Series"]["projections"][0]["queryRef"] == "mart_delay_causes.cause_type"
    assert area["Y"]["projections"][0]["queryRef"] == "mart_delay_causes.Reported Cause Minutes"


def test_airport_role_dimensions_match_the_fact_marts():
    relationships = (REPORT.parent / "FlightOperations.SemanticModel" / "definition"
                     / "relationships.tmdl").read_text(encoding="utf-8-sig")
    assert ("fromColumn: mart_airport_daily.airport_sk\n"
            "\ttoColumn: dim_airport.airport_sk") in relationships
    assert ("fromColumn: mart_route_monthly.origin_airport_sk\n"
            "\ttoColumn: dim_origin_airport.airport_sk") in relationships
    assert ("fromColumn: mart_route_monthly.dest_airport_sk\n"
            "\ttoColumn: dim_dest_airport.airport_sk") in relationships


def test_executive_trend_is_full_width_and_risk_delta_strip_is_compact():
    page = read(PAGES / "pages.json")["pageOrder"][0]
    trend = get_visual(page, "left-chart")
    assert trend["visual"]["visualType"] == "lineChart"
    assert trend["position"]["x"] == 28
    assert trend["position"]["width"] == 1224
    assert trend["position"]["y"] > 340
    assert trend["visual"]["query"]["queryState"]["Category"]["projections"][0][
        "queryRef"] == "dim_month.source_month"
    assert trend["visual"]["objects"]["categoryAxis"][0]["properties"][
        "axisType"]["expr"]["Literal"]["Value"] == "'Scalar'"
    line = trend["visual"]["objects"]["lineStyles"][0]["properties"]
    assert line["lineChartType"]["expr"]["Literal"]["Value"] == "'linear'"
    assert line["showMarker"]["expr"]["Literal"]["Value"] == "true"
    accent = trend["visual"]["objects"]["dataPoint"][0]["properties"][
        "defaultColor"]["solid"]["color"]["expr"]["Literal"]["Value"]
    assert accent == "'#1665ED'"

    risk = (
        ("right-chart", "Executive Arrival Risk YoY", 28, 510),
        ("risk-cancellation", "Executive Cancellation Risk YoY", 554, 331),
        ("risk-diversion", "Executive Diversion Risk YoY", 900, 352),
    )
    for role, measure, x, width in risk:
        card = get_visual(page, role)
        assert card["position"]["y"] == 253
        assert card["position"]["height"] == 82
        assert (card["position"]["x"], card["position"]["width"]) == (x, width)
        assert card["position"]["y"] + card["position"]["height"] < trend["position"]["y"]
        assert card["visual"]["query"]["queryState"]["Data"]["projections"][0][
            "queryRef"] == "mart_network_monthly." + measure
    kpis = get_visual(page, "metrics")["visual"]
    assert kpis["objects"]["value"][0]["properties"]["labelPrecision"][
        "expr"]["Literal"]["Value"] == "2L"


def test_executive_year_comparison_dax_is_short_and_maintenance_safe():
    source = (REPORT.parent / "FlightOperations.SemanticModel" / "definition"
              / "tables" / "mart_network_monthly.tmdl").read_text(
                  encoding="utf-8-sig"
              )
    for name in ("Executive Arrival Risk YoY", "Executive Cancellation Risk YoY",
                 "Executive Diversion Risk YoY"):
        block = source.split(f"measure '{name}' =", 1)[1].split(
            "displayFolder:", 1
        )[0]
        assert 'RETURN FORMAT(ChangePP, "+0.00;-0.00;0.00") & " pp"' in block
        assert "RETURN FORMAT(Rate2024," not in block
    assert plan_executive() == {}
    assert plan_year_comparison() == {}


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


def test_final_quality_pass_has_fixed_accessible_navigation_and_kpi_precision():
    pages = read(PAGES / "pages.json")["pageOrder"]
    keys = ("executive", "airline", "airports", "causes", "seasonal")
    for page, key in zip(pages, keys):
        v = get_visual(page, "nav-" + key)["visual"]
        color = v["objects"]["text"][1]["properties"]["fontColor"]
        assert color["solid"]["color"]["expr"]["Literal"]["Value"] == "'#073049'"
        metrics = get_visual(page, "metrics")["visual"]
        assert metrics["objects"]["value"][0]["properties"]["labelPrecision"][
            "expr"]["Literal"]["Value"] == "2L"
        for role, label in LABELS[key].items():
            visual = get_visual(page, role)["visual"]
            actual = visual["objects"]["general"][0]["properties"][
                "paragraphs"][0]["textRuns"][0]["value"]
            assert actual == label


def test_final_quality_visual_accessibility_and_formatted_comparison_scales():
    pages = read(PAGES / "pages.json")["pageOrder"]
    keys = ("executive", "airline", "airports", "causes", "seasonal")
    for key, page in zip(keys, pages):
        for (expected_key, role), description in ALT.items():
            if key != expected_key:
                continue
            obj = get_visual(page, role)["visual"]
            value = obj["visualContainerObjects"]["general"][0]["properties"][
                "altText"]["expr"]["Literal"]["Value"]
            assert value == "'" + description.replace("'", "''") + "'"
    airline = pages[1]
    bubble = get_visual(airline, "left-chart")["visual"]
    assert bubble["objects"]["categoryLabels"][0]["properties"]["show"][
        "expr"]["Literal"]["Value"] == "false"
    assert get_visual(airline, "right-chart")["visual"]["objects"]["legend"][
        0]["properties"]["show"]["expr"]["Literal"]["Value"] == "false"
    airport = get_visual(pages[2], "right-chart")["visual"]
    seasonal = get_visual(pages[4], "left-chart")["visual"]
    for visual, source, bounds in (
        (airport, ["mart_route_monthly.Route Delay 15+ Rate"], ("0.1D", "0.4D")),
        (seasonal, ["mart_network_monthly.Delay Rate 2024 Fixed",
                    "mart_network_monthly.Delay Rate 2025 Fixed"],
         ("0.1D", "0.35D")),
    ):
        rules = {x.get("selector", {}).get("metadata"): x for x in
                 visual["objects"]["values"]}
        for measure in source:
            val = rules[measure]["properties"]["backColor"]["solid"]["color"][
                "expr"]["FillRule"]["FillRule"]["linearGradient2"]
            assert val["min"]["value"]["Literal"]["Value"] == bounds[0]
            assert val["max"]["value"]["Literal"]["Value"] == bounds[1]
    cause = get_visual(pages[3], "left-chart")["visual"]
    assert cause["query"]["queryState"]["Category"]["projections"][0][
        "queryRef"] == "dim_month.source_month"
    assert cause["objects"]["categoryAxis"][0]["properties"]["axisType"][
        "expr"]["Literal"]["Value"] == "'Scalar'"
    assert plan_quality() == {}


def test_active_nav_tab_uses_wcag_aa_readable_text_against_teal():
    def luminance(value):
        parts = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
                  for v in parts]
        return sum(a * b for a, b in zip((0.2126, 0.7152, 0.0722), linear))

    foreground = luminance("#073049")
    background = luminance(TEAL)
    contrast = (max(foreground, background) + 0.05) / (
        min(foreground, background) + 0.05)
    assert contrast >= 4.5

def test_theme_resource_name_is_independent_of_checkout_line_endings(tmp_path):
    theme = REPORT.parent / "themes" / "FlightNetworkRiskIntel.json"
    lf = theme.read_bytes().replace(b"\r\n", b"\n")
    for name, data in (("lf.json", lf), ("crlf.json", lf.replace(b"\n", b"\r\n"))):
        path = tmp_path / name
        path.write_bytes(data)
        assert plan_redesign(theme_src=path) == {}
