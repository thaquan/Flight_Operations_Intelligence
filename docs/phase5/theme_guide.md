# Phase 5 / M5.1 - Aviation Command theme guide

**Status:** Proposed for design review. Power BI pages and a connected
semantic model are not built yet.

## Files

- [Executive Overview visual preview](dashboard_preview.svg) - static,
  high-resolution concept, using Phase 4 verified aggregate KPIs.
- [Power BI theme JSON](../../powerbi/themes/FlightOperationsIntelligence.json) -
  the importable color and typography configuration.
- [Report requirements](report_requirements.md) - audience, pages,
  data constraints, acceptance criteria.
- [KPI catalog](kpi_catalog.md) - precise formulas, denominator rules,
  QA reference values.
- [Page wireframes](dashboard_wireframes.md) - content and interaction plan.

## Visual language

| Token | Hex | Where it belongs |
| --- | --- | --- |
| Navy / navigation | `#102A43` | Left rail, selected-value callouts |
| Ink / primary text | `#172B4D` | Titles and KPI values |
| Canvas | `#F5F7FB` | Power BI page background |
| White | `#FFFFFF` | Cards and chart panels |
| Teal | `#087F8C` | On-time/success, selection accents |
| Amber | `#E6A04B` | Arrival delay >=15 min |
| Rose | `#D95F65` | Cancellations/negative alert |
| Blue | `#3C7BB6` | Scheduled volume and neutral data |
| Slate blue | `#6B7FA8` | Diverted flights |
| Secondary gray | `#61758A` | Captions, axes and helper text |
| Border | `#E6ECF3` | Subtle card outlines and gridlines |

Use **Segoe UI** with **Segoe UI Semibold** for key numbers and headings;
avoid decorative fonts, saturated gradients, and ornamental maps that
compete with data. Design intent is calm operational confidence, with
highlights reserved for exceptions.

Default report proportions: 16:9 canvas, ~14-16% navigation, 18-24px outer
spacing, 12-18px card gaps, 12-16px card radius in the preview. Power BI
requires visual backgrounds, page composition, and shape layout to be
placed in the report; the JSON theme **does not auto-create those visuals**.

## Apply in Power BI Desktop

1. Open the `.pbix` or `.pbip` report once it exists in M5.2.
2. Use the Report Design/Theme command **Import theme** (or its equivalent
   shown in your Desktop version) and select
   `powerbi/themes/FlightOperationsIntelligence.json`.
3. Confirm the import succeeds; Power BI applies the theme's structural,
   data series and text color defaults.
4. Manually set page/canvas background, navigation shapes, card containers
   and KPI-specific conditional formatting following the preview.
5. Validate chart labels, color semantics, navigation, tooltips, and filter
   state in every report page.

Microsoft reference:
[Use report themes in Power BI](https://learn.microsoft.com/power-bi/create-reports/desktop-report-themes)
and [Create custom report themes](https://learn.microsoft.com/power-bi/create-reports/report-themes-create-custom).

Theme colors establish default order, not guaranteed category mapping on
all visual types. Explicitly assign the semantic colors to any KPI or data
series where the meaning must remain fixed after filtering.

## Preview data provenance

The preview's KPI counts and full-period rates are taken from
`docs/phase4/quality_report.json`. Annual delayed-arrival rates
**20.82% (2024)** and **22.31% (2025)** are Phase 3 reconciliation results.
The right-side progress components show scaled totals rather than an
additional source-derived metric. No airline ranking or airport value is
invented in this concept.

The preview is a **static SVG**, not a connected Power BI visual and not
evidence of final report quality. On approval, M5.2 begins the PostgreSQL
connection and semantic model.
