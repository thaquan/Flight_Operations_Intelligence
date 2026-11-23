# Phase 5 / M5.1 - Dashboard wireframes

The visual design is named **Aviation Command**: a slim navy navigation
rail, white cards on a cloud-gray canvas, teal as an operational accent, and
amber/red reserved for performance issues. See
[dashboard preview](dashboard_preview.svg).

Use a 16:9 Power BI canvas (e.g. 1280 x 720 in Desktop) and proportionally
translate the visual preview; the 1600 x 980 SVG includes an extra design
footer and is **not** a literal page-size export.

## Shared layout

| Region | Purpose | Behavior |
| --- | --- | --- |
| Left rail (~15% width) | Report identity and five-page navigation | Selected page has teal active indicator |
| Top banner | Section name and data-quality/coverage context | Never hide the reporting period |
| Main title row | Current business question and period slicer | Period filter should expose Jan 2024-Dec 2025 default |
| KPI row | Three to five summary measures | Keep number/denominator tooltips available |
| Main canvas | Analytical comparisons and rankings | Use same card gutters and accessible legends |
| Bottom/right annotation | Methodology, caution, quality | Explicit source and scope statement |

## Page 1 - Executive Overview

| Position | Visual | Notes |
| --- | --- | --- |
| Top row | Scheduled Flights; Delay 15+ Rate; On-Time Rate; Cancellation Rate; Diversion Rate | Five KPI cards; formatting and definition consistent |
| Middle left (wide) | Monthly delay rate trend with year comparison | Use network month mart; monthly points after M5.2; reference design shows verified annual points |
| Middle right | Operational outcome counts | Progress bars need explicit scale; no mixing counts with percentages |
| Bottom left | Quick navigation/insight modules | Calls out carrier, airport/route and delay-cause analysis |
| Bottom right | Interpretation and source caveats | 2 REVIEW; 0 FAIL; BTS only, historical |

## Page 2 - Airline Performance

| Position | Visual | Notes |
| --- | --- | --- |
| Header | Reporting year/month range + airline selector | Single airline optional |
| KPI row | Scheduled; eligible; delay 15+ rate; cancelled; diverted | Use **airline mart**, not network mart |
| Left main | Top-15 carrier rank by delay rate | Minimum 10,000 scheduled flights per selected period, configurable/displayed |
| Right main | Volume vs delay-rate scatter | Circle size = scheduled count, vertical = delay rate |
| Bottom | Selected airline monthly performance | Trend includes data point count and denominators |

## Page 3 - Airports & Routes

| Position | Visual | Notes |
| --- | --- | --- |
| Header | Month and airport role toggle | Default `Origin`; `Destination` explicit |
| Left main | Top-20 airports by scheduled flights | A role filter is always applied |
| Right main | Airport volume vs delay rate | Screen low-volume outliers using visible threshold |
| Bottom | Directed route ranking/table | Origin and Destination selectors are independent |
| Tooltip | Scheduled, eligible, late, cancelled | Never aggregate both role rows |

Do not promise that selecting a carrier filters this page. The current
airport and route marts have no airline key.

## Page 4 - Delay Causes

| Position | Visual | Notes |
| --- | --- | --- |
| KPI row | Total reported cause minutes; positive cause observations | These are not unique delayed flight counts |
| Main | Horizontal bars for carrier, late aircraft, NAS, weather, security | Bars represent **minutes**, not flight incidence |
| Right | Cause share of all selected cause minutes | Recalculate denominator across all five categories |
| Bottom | Trend by month and airline | Distinguish zero reported minutes from NULL/non-reported |

The `weather` cause is a BTS attribution field, not NOAA meteorological
observations. A future NOAA enrichment would require a separate documented
analysis and cannot be implied by this page.

## Page 5 - Seasonal Trends

| Position | Visual | Notes |
| --- | --- | --- |
| Top | Month-of-year overlay: 2024 vs 2025 arrival delay rates | Side-by-side monthly rates from network mart |
| Middle | 24-month monthly trend | Month sort by month-start date, not string |
| Bottom left | Monthly scheduled and eligible volumes | Dual axis only if legibility remains strong |
| Bottom right | Month-to-month and YoY change cards | Display percentage-point change, not percent relative growth, for rates |

## Layout and interaction checklist

- No legend that relies only on red/green: add text and tooltips.
- Prefer bar ranking and a line chart to dense table grids.
- One primary question per page, two to four supporting visuals.
- Subtitles always specify selection and metric denominator.
- Keep visual titles and navigation short; use longer explanations only in
  the methodology panel and tooltips.
- Do not show fabricated airline/airport rankings during design review.
- Keep all report pages usable on desktop; mobile view is a separate
  Power BI layout task during M5.6.
