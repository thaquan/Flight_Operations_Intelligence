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
        "left_title": "ARRIVAL DELAY RATE  ·  MONTHLY TREND",
        "left": ("lineChart", [("dim_month", "month_label")],
                 [("mart_network_monthly", "Arrival Delay 15+ Rate")]),
        "right_title": "RELIABILITY / CANCELLATIONS VS DIVERSIONS",
        "right": ("clusteredColumnChart", [("dim_month", "calendar_year")],
                  [("mart_network_monthly", "Cancellation Rate"),
                   ("mart_network_monthly", "Diversion Rate")]),
        "footer": "Historical BTS records, not real-time flight monitoring. Rates use eligible arrivals or scheduled flights as defined.",
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
        "left_title": "ARRIVAL DELAY RATE  ·  REPORTING CARRIER",
        "left": ("clusteredBarChart", [("dim_airline", "airline_code")],
                 [("mart_airline_monthly", "Airline Delay 15+ Rate")]),
        "right_title": "SCHEDULED VOLUME  ·  CARRIER",
        "right": ("clusteredColumnChart", [("dim_airline", "airline_code")],
                  [("mart_airline_monthly", "Airline Scheduled Flights")]),
        "footer": "Compare rates together with volume; low-sample carriers require interpretation.",
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
        "left_title": "BUSIEST ORIGIN AIRPORTS / FLIGHT VOLUME",
        "left": ("clusteredBarChart", [("dim_airport", "airport_code")],
                 [("mart_airport_daily", "Origin Scheduled Flights")]),
        "right_title": "DIRECTED ROUTE  ·  VOLUME & DELAY",
        "right": ("tableEx",
                  [("dim_origin_airport", "airport_code"),
                   ("dim_dest_airport", "airport_code")],
                  [("mart_route_monthly", "Route Scheduled Flights"),
                   ("mart_route_monthly", "Route Delay 15+ Rate")]),
        "footer": "Route map pending validated airport geocodes. Origin and destination counts are never added together.",
    },
    {
        "key": "causes", "title": "Delay Causes",
        "subtitle": "Reported minutes attributed to BTS delay categories",
        "cards": [
            ("mart_delay_causes", "Reported Cause Minutes"),
            ("mart_delay_causes", "Positive Cause Observations"),
        ],
        "left_title": "REPORTED CAUSE MINUTES  ·  BY TYPE",
        "left": ("clusteredBarChart", [("mart_delay_causes", "cause_type")],
                 [("mart_delay_causes", "Reported Cause Minutes")]),
        "right_title": "DELAY MINUTES / CAUSE MIX",
        "right": ("donutChart", [("mart_delay_causes", "cause_type")],
                  [("mart_delay_causes", "Reported Cause Minutes")]),
        "footer": "BTS cause observations may overlap; they are not counts of distinct delayed flights or observed weather.",
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
        "left_title": "DELAY RATE  ·  2024 VS 2025 / SAME CALENDAR MONTH",
        "left": ("lineChart", [("dim_month", "calendar_month")],
                 [("mart_network_monthly", "Arrival Delay 15+ Rate")]),
        "right_title": "MONTHLY DEMAND / 2024 VS 2025",
        "right": ("clusteredColumnChart", [("dim_month", "calendar_month")],
                  [("mart_network_monthly", "Scheduled Flights")]),
        "footer": "Ratios are recomputed from counts in the current filter context; no averaging of monthly percentages.",
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
                "fontColor": color("#FFFFFF" if selected else "#DCEBF4"),
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
    else:
        assert len(categories) == 1
        query_state = {
            "Category": {"projections": [field(t, c, "Column") for t, c in categories]},
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
        if categories[0][1] in friendly_labels:
            category["displayName"] = friendly_labels[categories[0][1]]
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
            field("mart_airport_daily", "Origin Delay 15+ Rate", "Measure"),
        ]}
    return out


def save_theme() -> None:
    theme = json.loads(PALETTE.read_text(encoding="utf-8-sig"))
    digest = hashlib.sha256(PALETTE.read_bytes()).hexdigest()[:10]
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
        is_routes = spec["key"] == "airports"
        left_chart_width = 650 if is_routes else 808
        right_chart_x = 700 if is_routes else 860
        right_chart_width = 552 if is_routes else 392
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
            chart(page_id, "left-chart", spec["left"][0], spec["left"][1],
                  spec["left"][2], 28, left_chart_width, 23),
            chart(page_id, "right-chart", spec["right"][0], spec["right"][1],
                  spec["right"][2], right_chart_x, right_chart_width, 24),
            rectangle(page_id, "footer-rule", 28, 665, 1224, 1, "#DAE5EF", 25),
            text_box(page_id, "footer", spec["footer"], 29, 674,
                     1210, 28, 11, MUTED, 26),
        ]
        if spec["key"] == "seasonal":
            seasonal_overlay_chart(visuals[-4])
        for content in visuals:
            role = content["name"]
            dump(PAGES / page_id / "visuals" / role / "visual.json", content)
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
