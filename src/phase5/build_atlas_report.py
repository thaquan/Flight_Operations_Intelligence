"""Build an original five-page Atlas x Risk Intel Power BI PBIR report.

Runs against a CLI-scaffolded Report folder. Only report metadata is written;
the approved PostgreSQL Gold Import semantic model is linked by path.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "powerbi" / "FlightOperations.Report"
DEFINITION = REPORT / "definition"
PAGES = DEFINITION / "pages"
PALETTE = ROOT / "powerbi" / "themes" / "FlightNetworkRiskIntel.json"
VISUAL_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/item/"
                 "report/definition/visualContainer/2.9.0/schema.json")
NAVY, TEAL, INK, PALE, MUTED = "#081B30", "#00BCD4", "#102238", "#E6EDF5", "#50667E"

PAGES_SPEC = [
    {
        "key": "executive", "title": "Executive Overview",
        "subtitle": "Network reliability · U.S. domestic flights · Jan 2024–Dec 2025",
        "cards": [
            ("mart_network_monthly", "Scheduled Flights"),
            ("mart_network_monthly", "Arrival Delay 15+ Rate"),
            ("mart_network_monthly", "Arrival On-Time Rate"),
            ("mart_network_monthly", "Cancellation Rate"),
            ("mart_network_monthly", "Diversion Rate"),
        ],
        "left_title": "MONTHLY TREND / RESPONDS TO YEAR SELECTION",
        "left": ("lineChart", [("dim_month", "source_month")],
                 [("mart_network_monthly", "Arrival Delay 15+ Rate")]),
        "right_title": "2025 VS 2024  /  CHANGE IN RISK (PERCENTAGE POINTS)",
        "right": ("cardVisual", [],
                  [("mart_network_monthly", "Executive Arrival Risk YoY"),
                   ("mart_network_monthly", "Executive Cancellation Risk YoY"),
                   ("mart_network_monthly", "Executive Diversion Risk YoY")]),
        "footer": "Headline KPIs and trend follow YEAR. YoY deltas compare full 2024 vs 2025. Delay % uses eligible arrivals.",
    },
    {
        "key": "airline", "title": "Airline Performance",
        "subtitle": "Rank carrier punctuality against actual flight volume",
        "cards": [
            ("mart_airline_monthly", "Airline Scheduled Flights"),
            ("mart_airline_monthly", "Airline Delay 15+ Rate"),
            ("mart_airline_monthly", "Airline Cancellation Rate"),
            ("mart_airline_monthly", "Airline Diversion Rate"),
        ],
        "left_title": "CARRIER RISK / HOVER BUBBLES FOR DETAILS",
        "left": ("scatterChart", [("dim_airline", "airline_code")],
                 [("mart_airline_monthly", "Airline Scheduled Flights"),
                  ("mart_airline_monthly", "Airline Delay 15+ Rate"),
                  ("mart_airline_monthly", "Airline Cancelled Flights")]),
        "right_title": "FLIGHT SHARE / COLORS IDENTIFY CARRIERS",
        "right": ("treemap", [("dim_airline", "airline_code")],
                  [("mart_airline_monthly", "Airline Scheduled Flights"),
                   ("mart_airline_monthly", "Airline Delay 15+ Rate")]),
        "footer": "Bubbles: X = flights, Y = delay %, size = cancelled flights. Hover for airline; treemap colors do not represent risk.",
    },
    {
        "key": "airports", "title": "Airports & Routes",
        "subtitle": "Origin airport risk and directed origin → destination network",
        "cards": [
            ("mart_route_monthly", "Route Scheduled Flights"),
            ("mart_route_monthly", "Route Delay 15+ Rate"),
            ("mart_route_monthly", "Route Cancelled Flights"),
            ("mart_route_monthly", "Route Diverted Flights"),
        ],
        "left_title": "ORIGIN TRAFFIC / DRILL STATE TO AIRPORT",
        "left": ("clusteredBarChart",
                 [("dim_origin_airport", "state_code"),
                  ("dim_origin_airport", "airport_code")],
                 [("mart_route_monthly", "Route Scheduled Flights")]),
        "right_title": "ROUTES BY VOLUME / SHADED DELAY RISK",
        "right": ("tableEx",
                  [("dim_origin_airport", "airport_code"),
                   ("dim_dest_airport", "airport_code")],
                  [("mart_route_monthly", "Route Scheduled Flights"),
                   ("mart_route_monthly", "Route Delay 15+ Rate")]),
        "footer": "Select a state to filter routes; use drill controls for airports. Route table sorts by flights; warmer cells = more delay.",
    },
    {
        "key": "causes", "title": "Delay Causes",
        "subtitle": "Reported minutes attributed to BTS delay categories",
        "cards": [
            ("mart_delay_causes", "Reported Cause Minutes"),
            ("mart_delay_causes", "Positive Cause Observations"),
        ],
        "left_title": "ATTRIBUTED MINUTES / MONTHLY HISTORY",
        "left": ("stackedAreaChart", [("dim_month", "source_month")],
                 [("mart_delay_causes", "Reported Cause Minutes")]),
        "right_title": "CAUSE SHARE / MINUTES, NOT FLIGHTS",
        "right": ("donutChart", [("mart_delay_causes", "cause_type")],
                  [("mart_delay_causes", "Reported Cause Minutes")]),
        "footer": "Causes can overlap; observations are not unique delayed flights. Raw minutes are not normalized for traffic.",
    },
    {
        "key": "seasonal", "title": "Seasonal Trends",
        "subtitle": "2024–2025 monthly seasonality and year-over-year context",
        "cards": [
            ("mart_network_monthly", "Scheduled Flights"),
            ("mart_network_monthly", "Eligible Arrivals"),
            ("mart_network_monthly", "Late Arrivals 15+"),
            ("mart_network_monthly", "Arrival Delay 15+ Rate"),
        ],
        "left_title": "MONTHLY DELAY HEATMAP / SAME 10-35% SCALE",
        "left": ("pivotTable", [("dim_month", "calendar_month")],
                 [("mart_network_monthly", "Delay Rate 2024 Fixed"),
                  ("mart_network_monthly", "Delay Rate 2025 Fixed")]),
        "right_title": "2025 - 2024 (PP) / CORAL WORSE, CYAN BETTER",
        "right": ("clusteredBarChart", [("dim_month", "calendar_month")],
                  [("mart_network_monthly", "Delay Rate YoY pp")]),
        "footer": "Top KPIs follow YEAR; comparison charts always show both years. Shared heatmap scale 10-35%; warmer means worse.",
    },
]


def dump(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def uid(*parts: str) -> str:
    return uuid.uuid5(uuid.NAMESPACE_URL, "flight-operations-atlas/" + "/".join(parts)).hex[:20]


def expression_literal(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def color(value: str) -> dict:
    return {"solid": {"color": expression_literal("'" + value + "'")}}


def field(table: str, name: str, kind: str) -> dict:
    return {
        "field": {kind: {
            "Expression": {"SourceRef": {"Entity": table}},
            "Property": name,
        }},
        "queryRef": table + "." + name,
        "nativeQueryRef": name,
    }


def visual(page: str, role: str, x: int, y: int, w: int, h: int,
           kind: str, z: int) -> dict:
    return {
        "$schema": VISUAL_SCHEMA,
        "name": uid(page, role),
        "position": {
            "x": x, "y": y, "z": z,
            "height": h, "width": w, "tabOrder": z,
        },
        "visual": {"visualType": kind},
    }


def text_box(page: str, role: str, value: str, x: int, y: int,
             w: int, h: int, size: int, fg: str, z: int) -> dict:
    out = visual(page, role, x, y, w, h, "textbox", z)
    out["visual"]["objects"] = {
        "general": [{"properties": {"paragraphs": [{
            "textRuns": [{"value": value, "textStyle": {
                "fontFamily": "Segoe UI Semibold" if size >= 17 else "Segoe UI",
                "fontSize": str(size) + "px",
                "color": fg,
            }}],
            "horizontalTextAlignment": "left",
        }]}}],
    }
    # Remove the implicit 8px VCO padding: title labels occupy tight lanes.
    out["visual"]["visualContainerObjects"] = {
        "background": [{"properties": {"show": expression_literal("false")}}],
        "border": [{"properties": {"show": expression_literal("false")}}],
        "padding": [{"properties": {
            k: expression_literal("0D")
            for k in ("top", "bottom", "left", "right")
        }}],
    }
    return out


def rectangle(page: str, role: str, x: int, y: int, w: int, h: int,
              fill: str, z: int) -> dict:
    out = visual(page, role, x, y, w, h, "shape", z)
    out["visual"]["objects"] = {
        "shape": [{"properties": {"tileShape": expression_literal("'rectangle'")}}],
        "fill": [{"properties": {
            "fillColor": color(fill),
            "transparency": expression_literal("0D"),
        }, "selector": {"id": "default"}}],
        "outline": [{"properties": {
            "show": expression_literal("false"),
        }, "selector": {"id": "default"}}],
    }
    return out


def card(page: str, specs: list[tuple[str, str]], z: int) -> dict:
    canvas_height = 720
    value_font = min(28, max(12, int(canvas_height * 0.028)))
    label_font = min(14, max(8, int(value_font * 0.55)))
    content_height = 2*8 + 2*8 + 2 + (value_font*3+1)//2 + (max(label_font,12)*3+1)//2
    assert content_height <= int(canvas_height * .15)
    out = visual(page, "metrics", 28, 115, 1224, content_height, "cardVisual", z)
    out["visual"]["query"] = {"queryState": {
        "Data": {"projections": [field(t, m, "Measure") for t, m in specs]}
    }}
    out["visual"]["objects"] = {
        "value": [{"properties": {
            "fontSize": expression_literal(str(value_font)+"D"),
            "fontColor": color("#102238"),
            "bold": expression_literal("true"),
        }, "selector": {"id": "default"}}],
        "label": [{"properties": {
            "fontSize": expression_literal(str(label_font)+"D"),
            "fontColor": color("#45617C"),
        }, "selector": {"id": "default"}}],
        "padding": [{"properties": {"paddingUniform": expression_literal("8D")},
                     "selector": {"id": "default"}}],
        "layout": [{"properties": {"paddingUniform": expression_literal("0D")},
                    "selector": {"id": "default"}}],
    }
    out["visual"]["visualContainerObjects"] = {
        "padding": [{"properties": {
            v: expression_literal("8D") for v in ("top", "bottom", "left", "right")
        }, "selector": {"id": "default"}}],
        "spacing": [{"properties": {
            "customizeSpacing": expression_literal("true"),
            "verticalSpacing": expression_literal("2D"),
        }, "selector": {"id": "default"}}],
        "background": [{"properties": {
            "show": expression_literal("true"),
            "color": color("#122E48"),
            "transparency": expression_literal("0D"),
        }}],
    }
    return out


def year_slicer(page: str) -> dict:
    """Synced two-year dropdown in the navy header (80px includes padding)."""
    out = visual(page, "year-slicer", 1000, 8, 252, 80, "slicer", 40)
    out["visual"]["query"] = {
        "queryState": {
            "Values": {"projections": [field("dim_month", "calendar_year", "Column")]}
        }
    }
    out["visual"]["syncGroup"] = {
        "groupName": "FlightOperationsYear",
        "fieldChanges": True,
        "filterChanges": True,
    }
    out["visual"]["objects"] = {
        "data": [{"properties": {"mode": expression_literal("'Dropdown'")}}],
        "header": [{"properties": {
            "show": expression_literal("true"),
            "text": expression_literal("'YEAR / PERIOD'"),
            "fontColor": color("#E6F7FF"),
            "background": color("#102B43"),
            "bold": expression_literal("true"),
        }}],
        "items": [{"properties": {
            "fontColor": color("#F2FBFF"),
            "background": color("#102B43"),
        }}],
        "dropdown": [{"properties": {
            "borderColor": color("#40627A"),
            "iconColor": color("#E6F7FF"),
            "borderRadius": expression_literal("4L"),
        }}],
    }
    out["visual"]["visualContainerObjects"] = {
        "padding": [{"properties": {
            k: expression_literal("8D") for k in ("top", "bottom", "left", "right")
        }}],
        "background": [{"properties": {
            "show": expression_literal("true"),
            "color": color("#102B43"),
            "transparency": expression_literal("0D"),
        }}],
        "border": [{"properties": {
            "show": expression_literal("true"),
            "color": color("#40627A"),
            "radius": expression_literal("4L"),
        }}],
    }
    return out


NAV_TABS = [
    ("executive", "OVERVIEW"),
    ("airline", "AIRLINES"),
    ("airports", "AIRPORTS"),
    ("causes", "CAUSES"),
    ("seasonal", "TRENDS"),
]


def navigation_button(page: str, key: str, label: str, target: str,
                      index: int, selected: bool) -> dict:
    """Native PageNavigation action with page-specific active styling."""
    out = visual(page, "nav-" + key, 336 + 120 * index, 9, 112, 44,
                 "actionButton", 50 + index)
    out["visual"]["objects"] = {
        "text": [
            {"properties": {"show": expression_literal("true")}},
            {"properties": {
                "text": expression_literal("'" + label + "'"),
                "fontSize": expression_literal("11D"),
                "fontColor": color("#073049" if selected else "#DCEBF4"),
                "horizontalAlignment": expression_literal("'center'"),
            }, "selector": {"id": "default"}},
        ],
        "icon": [
            {"properties": {"show": expression_literal("false")}},
            {"properties": {
                "shapeType": expression_literal("'blank'"),
                "placement": expression_literal("'left'"),
            }, "selector": {"id": "default"}},
        ],
        "fill": [
            {"properties": {"show": expression_literal("true")}},
            {"properties": {"fillColor": color(TEAL if selected else "#1D3A55")},
             "selector": {"id": "default"}},
            {"properties": {"fillColor": color("#246C82")},
             "selector": {"id": "hover"}},
        ],
        "outline": [{"properties": {"show": expression_literal("false")}}],
        "shape": [
            {"properties": {
                "tileShape": expression_literal("'rectangleRounded'"),
                "roundEdge": expression_literal("8L"),
            }},
            {"properties": {"tileShape": expression_literal("'rectangleRounded'")},
             "selector": {"id": "default"}},
        ],
    }
    out["visual"]["visualContainerObjects"] = {
        "background": [{"properties": {"show": expression_literal("false")}}],
        "border": [{"properties": {"show": expression_literal("false")}}],
        "padding": [{"properties": {
            edge: expression_literal("0D")
            for edge in ("top", "bottom", "left", "right")
        }}],
        "visualLink": [{"properties": {
            "show": expression_literal("true"),
            "type": expression_literal("'PageNavigation'"),
            "navigationSection": expression_literal("'" + target + "'"),
            "tooltip": expression_literal("'Go to " + label + " (Ctrl+click in Desktop edit mode)'"),
        }}],
    }
    out["visual"]["drillFilterOtherVisuals"] = True
    out["howCreated"] = "InsertVisualButton"
    return out


def home_button(page: str, target: str) -> dict:
    """Home icon backed by native Power BI PageNavigation (Segoe MDL2 glyph)."""
    out = navigation_button(page, "home", chr(0xE80F), target, 0, False)
    out["position"].update({"x": 264, "y": 9, "width": 68, "height": 44})
    text_style = out["visual"]["objects"]["text"][1]["properties"]
    text_style.update({
        "fontFamily": expression_literal("'Segoe MDL2 Assets'"),
        "fontSize": expression_literal("22D"),
        "fontColor": color("#F7FCFF"),
    })
    link = out["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]
    link["tooltip"] = expression_literal("'Home - Executive Overview (Ctrl+click in Desktop edit mode)'")
    return out


def seasonal_overlay_chart(existing: dict) -> dict:
    """Overlay the two years by month-of-year, not by 24 sequential months."""
    if existing["visual"]["visualType"] != "lineChart":
        raise ValueError("Seasonal overlay must be a line chart")
    query = existing["visual"]["query"]
    state = query["queryState"]
    state["Category"] = {"projections": [
        {**field("dim_month", "calendar_month", "Column"),
         "displayName": "Month"},
    ]}
    state["Series"] = {"projections": [
        {**field("dim_month", "calendar_year", "Column"),
         "displayName": "Year"},
    ]}
    query["sortDefinition"] = {
        "sort": [{"field": state["Category"]["projections"][0]["field"],
                  "direction": "Ascending"}],
        "isDefaultSort": False,
    }
    existing["visual"].setdefault("objects", {})["categoryAxis"] = [{
        "properties": {"axisType": expression_literal("'Categorical'")}
    }]
    return existing


def chart(page: str, role: str, chart_type: str, categories: list,
          measures: list, x: int, w: int, z: int) -> dict:
    out = visual(page, role, x, 263, w, 387, chart_type, z)
    if chart_type in ("pivotTable", "tableEx"):
        columns = [field(t, c, "Column") for t, c in categories]
        # PBIR nativeQueryRef must be unique inside one visual. Origin and
        # destination both expose airport_code; give destination a distinct alias.
        seen: set[str] = set()
        for projection in columns:
            base = projection["nativeQueryRef"]
            alias = base
            suffix = 1
            while alias in seen:
                alias = f"{base}{suffix}"
                suffix += 1
            projection["nativeQueryRef"] = alias
            seen.add(alias)
        values = [field(t, m, "Measure") for t, m in measures]
        if chart_type == "tableEx":
            if categories == [("dim_origin_airport", "airport_code"),
                              ("dim_dest_airport", "airport_code")]:
                for projection, label in zip(columns + values,
                                             ("Origin", "Destination",
                                              "Flights", "Delay 15+ %")):
                    projection["displayName"] = label
            query_state = {"Values": {"projections": columns + values}}
        else:
            query_state = {
                "Rows": {"projections": columns},
                "Values": {"projections": values},
            }
        out["visual"]["objects"] = {
            "columnHeaders": [{"properties": {
                "columnAdjustment": expression_literal("'growToFit'"),
                "autoSizeColumnWidth": expression_literal("true"),
            }}]
        }
    elif chart_type == "scatterChart":
        assert len(categories) == 1 and len(measures) == 3
        query_state = {
            "Category": {"projections": [
                {**field(*categories[0], "Column"), "displayName": "Carrier"},
            ]},
            "X": {"projections": [field(*measures[0], "Measure")]},
            "Y": {"projections": [field(*measures[1], "Measure")]},
            "Size": {"projections": [field(*measures[2], "Measure")]},
            "Tooltips": {"projections": [
                field("mart_airline_monthly", "Airline Cancellation Rate", "Measure"),
            ]},
        }
        out["visual"]["objects"] = {
            "categoryLabels": [{"properties": {
                "show": expression_literal("true"),
                "fontSize": expression_literal("10D"),
                "color": color("#102238"),
            }}],
            "bubbles": [{"properties": {
                "markerShape": expression_literal("'circle'"),
                "preventOverflow": expression_literal("true"),
            }}],
        }
    elif chart_type == "treemap":
        assert len(categories) == 1 and len(measures) == 2
        query_state = {
            "Group": {"projections": [
                {**field(*categories[0], "Column"), "displayName": "Carrier"},
            ]},
            "Values": {"projections": [field(*measures[0], "Measure")]},
            "Tooltips": {"projections": [field(*measures[1], "Measure")]},
        }
        out["visual"]["objects"] = {
            "categoryLabels": [{"properties": {
                "show": expression_literal("true"),
                "fontSize": expression_literal("12D"),
                "color": color("#102238"),
            }}],
        }
    else:
        assert len(categories) in (1, 2)
        category_projections = [field(t, c, "Column") for t, c in categories]
        if len(category_projections) == 2:
            assert chart_type == "clusteredBarChart"
            assert page == uid("page", "airports")
            category_projections[0].update({"displayName": "State", "active": True})
            category_projections[1].update({
                "displayName": "Origin airport", "active": False,
            })
            out["visual"]["drillFilterOtherVisuals"] = True
        query_state = {
            "Category": {"projections": category_projections},
            "Y": {"projections": [field(t, m, "Measure") for t, m in measures]},
        }
        friendly_labels = {
            "month_label": "Month",
            "calendar_year": "Year",
            "calendar_month": "Month",
            "airline_code": "Airline",
            "airport_code": "Origin airport",
            "cause_type": "Delay cause",
        }
        category = query_state["Category"]["projections"][0]
        if len(categories) == 1 and categories[0][1] in friendly_labels:
            category["displayName"] = friendly_labels[categories[0][1]]
        if chart_type == "stackedAreaChart":
            assert page == uid("page", "causes")
            query_state["Series"] = {"projections": [{
                **field("mart_delay_causes", "cause_type", "Column"),
                "displayName": "Cause",
            }]}
            out["visual"]["objects"] = {
                "legend": [{"properties": {
                    "show": expression_literal("true"),
                    "position": expression_literal("'Top'"),
                    "fontSize": expression_literal("10D"),
                }}],
                "categoryAxis": [{"properties": {
                    "axisType": expression_literal("'Categorical'"),
                }}],
            }
    if chart_type == "clusteredColumnChart" and page == uid("page", "seasonal") and role == "right-chart":
        query_state["Series"] = {
            "projections": [{**field("dim_month", "calendar_year", "Column"),
                             "displayName": "Year"}],
        }
    out["visual"]["query"] = {"queryState": query_state}
    if chart_type in ("clusteredBarChart", "clusteredColumnChart") and measures:
        if chart_type == "clusteredBarChart" or page == uid("page", "airline"):
            out["visual"]["query"]["sortDefinition"] = {
                "sort": [{"field": field(measures[0][0], measures[0][1], "Measure")["field"],
                          "direction": "Descending"}],
                "isDefaultSort": False,
            }
    if (page == uid("page", "seasonal") and role == "right-chart"):
        out["visual"].setdefault("objects", {})["categoryAxis"] = [{
            "properties": {"axisType": expression_literal("'Categorical'")}
        }]
    if chart_type == "tableEx":
        out["visual"]["query"]["sortDefinition"] = {
            "sort": [{
                "field": field(measures[0][0], measures[0][1], "Measure")["field"],
                "direction": "Descending",
            }],
            "isDefaultSort": False,
        }
    if (page == uid("page", "airports") and role == "left-chart"):
        query_state["Tooltips"] = {"projections": [
            field("mart_route_monthly", "Route Delay 15+ Rate", "Measure"),
        ]}
    if (page == uid("page", "causes") and role == "left-chart"):
        out["visual"]["query"]["sortDefinition"] = {
            "sort": [{"field": field("dim_month", "month_label", "Column")["field"],
                      "direction": "Ascending"}],
        }
    chart_titles = {
        (uid("page", "airline"), "left-chart"): "Carrier risk by traffic and delay",
        (uid("page", "airline"), "right-chart"): "Carrier share of flight volume",
        (uid("page", "airports"), "left-chart"): "Origin traffic by state",
        (uid("page", "causes"), "left-chart"): "Attributed delay minutes over time",
        (uid("page", "causes"), "right-chart"): "Delay minutes by cause",
    }
    label = chart_titles.get((page, role))
    if label:
        container = out["visual"].setdefault("visualContainerObjects", {})
        container["title"] = [{"properties": {
            "show": expression_literal("true"),
            "text": expression_literal("'" + label + "'"),
            "fontSize": expression_literal("15D"),
            "fontColor": color("#102238"),
            "bold": expression_literal("true"),
        }}]
        container["subTitle"] = [{"properties": {
            "show": expression_literal("false"),
        }}]
    return out


def save_theme() -> None:
    theme = json.loads(PALETTE.read_text(encoding="utf-8-sig"))
    digest = hashlib.sha256(PALETTE.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:10]
    filename = "FlightNetworkRiskIntel-" + digest + ".json"
    theme["name"] = filename
    dump(REPORT / "StaticResources" / "RegisteredResources" / filename, theme)

    report_path = DEFINITION / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    base = report["themeCollection"]["baseTheme"]["reportVersionAtImport"]
    report["themeCollection"]["customTheme"] = {
        "name": filename,
        "reportVersionAtImport": dict(base),
        "type": "RegisteredResources",
    }
    packages = [p for p in report["resourcePackages"]
                if p["name"] != "RegisteredResources"]
    packages.append({
        "name": "RegisteredResources", "type": "RegisteredResources",
        "items": [{"name": filename, "path": filename, "type": "CustomTheme"}],
    })
    report["resourcePackages"] = packages
    dump(report_path, report)


def page_chart_visuals(page_id: str, spec: dict) -> list[dict]:
    """Build the charts for a new report without overwriting an edited PBIP."""
    if spec["key"] == "executive":
        from src.phase5.polish_executive import (
            DELTA_METRICS,
            style_delta_card,
            style_trend,
        )
        from src.phase5.rework_overview_seasonal import scorecard_item

        line = chart(page_id, "left-chart", *spec["left"], 28, 808, 23)
        result = [style_trend(line)]
        for index, (role, measure, title, x, width, size) in enumerate(
                DELTA_METRICS):
            original = scorecard_item(page_id, role, measure, title, index, None)
            result.append(style_delta_card(original, measure, title,
                                           x, width, size))
        return result
    if spec["key"] == "seasonal":
        from src.phase5.rework_overview_seasonal import diverging_bar, heatmap

        return [
            heatmap(page_id, visual(page_id, "left-chart", 28, 263, 650, 387,
                                    "pivotTable", 23)),
            diverging_bar(page_id, visual(page_id, "right-chart", 700, 263,
                                          552, 387, "clusteredBarChart", 24)),
        ]

    is_routes = spec["key"] == "airports"
    left_width = 650 if is_routes else 808
    right_x, right_width = (700, 552) if is_routes else (860, 392)
    return [
        chart(page_id, "left-chart", *spec["left"], 28, left_width, 23),
        chart(page_id, "right-chart", *spec["right"], right_x, right_width, 24),
    ]


def make_pages() -> None:
    pages_meta_path = PAGES / "pages.json"
    meta = json.loads(pages_meta_path.read_text(encoding="utf-8"))
    initial = meta["activePageName"]
    page_ids = [initial] + [uid("page", spec["key"]) for spec in PAGES_SPEC[1:]]
    page_schema = json.loads((PAGES / initial / "page.json").read_text(encoding="utf-8"))["$schema"]
    meta["pageOrder"] = page_ids
    meta["activePageName"] = initial
    dump(pages_meta_path, meta)

    for i, (page_id, spec) in enumerate(zip(page_ids, PAGES_SPEC)):
        page_json = {
            "$schema": page_schema, "name": page_id,
            "displayName": spec["title"],
            "displayOption": "FitToPage", "height": 720, "width": 1280,
            "objects": {
                "background": [{"properties": {
                    "color": color(PALE),
                    "transparency": expression_literal("0D"),
                }}],
            },
        }
        dump(PAGES / page_id / "page.json", page_json)
        is_wide_right = spec["key"] in ("airports", "seasonal")
        right_chart_x = 700 if is_wide_right else 860
        right_chart_width = 552 if is_wide_right else 392
        visuals = [
            rectangle(page_id, "navy-header", 0, 0, 1280, 96, NAVY, 0),
            rectangle(page_id, "teal-accent", 0, 93, 1280, 3, TEAL, 1),
            text_box(page_id, "brand", "FLIGHT OPS  /  NETWORK INTELLIGENCE",
                     27, 10, 260, 24, 12, "#A4DDEC", 11),
            text_box(page_id, "title", spec["title"], 27, 33, 1000, 48,
                     27, "#FFFFFF", 12),
            text_box(page_id, "subtitle", spec["subtitle"], 420, 58, 540, 30,
                     11, "#CFE8F0", 13),
            year_slicer(page_id),
            home_button(page_id, page_ids[0]),
            *[navigation_button(page_id, key, label, target, j,
                                spec["key"] == key)
              for j, ((key, label), target) in enumerate(zip(NAV_TABS, page_ids))],
            card(page_id, spec["cards"], 20),
            text_box(page_id, "left-label", spec["left_title"],
                     28, 226, 790, 28, 13, INK, 21),
            text_box(page_id, "right-label", spec["right_title"],
                     right_chart_x, 226, right_chart_width, 28, 13, INK, 22),
            *page_chart_visuals(page_id, spec),
            rectangle(page_id, "footer-rule", 28, 665, 1224, 1, "#DAE5EF", 25),
            text_box(page_id, "footer", spec["footer"], 29, 674,
                     1210, 28, 11, MUTED, 26),
        ]
        if spec["key"] == "executive":
            from src.phase5.polish_executive import (
                LABEL_TEXT,
                style_label,
                style_network_kpis,
            )
            for index, content in enumerate(visuals):
                if content["name"] == uid(page_id, "metrics"):
                    visuals[index] = style_network_kpis(content)
                else:
                    role = next((key for key in LABEL_TEXT
                                 if content["name"] == uid(page_id, key)), None)
                    if role:
                        visuals[index] = style_label(content, role)
        from src.phase5.final_quality_pass import enhance
        named_roles = ("metrics", "left-label", "right-label", "footer",
                       "left-chart", "right-chart", "risk-cancellation",
                       "risk-diversion", *("nav-" + tab for tab, _ in NAV_TABS))
        role_lookup = {uid(page_id, role): role for role in named_roles}
        for content in visuals:
            role = content["name"]
            refined = enhance(spec["key"], role_lookup.get(role, ""), content)
            dump(PAGES / page_id / "visuals" / role / "visual.json", refined)
        print(spec["title"], "->", len(visuals), "visuals")


def build() -> None:
    assert (REPORT / "definition.pbir").exists(), "CLI report scaffold is required"
    # Never re-scaffold a report already saved/edited in Desktop.
    if any(PAGES.rglob("visual.json")):
        raise FileExistsError("Report contains visuals; refuse destructive regeneration")
    save_theme()
    make_pages()
    print("PBIR Atlas report generated:", REPORT)


if __name__ == "__main__":
    build()
