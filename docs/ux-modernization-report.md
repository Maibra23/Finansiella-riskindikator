# UX/UI modernization, final report

Implementation of `UX_UI_MODERNIZATION_PLAN.md` (P0 + P1, plus the cheap P2/P3
items), on branch `ux/modernization-plan`, uncommitted, for owner review.
Verification details are in `docs/ux-modernization-log.md`; the maintained UI
reference is `docs/ux-ui-design-system.md`.

## Review items: decisions taken

The owner asked for the remaining plan to be completed in one pass, so every
open ⚠ REVIEW item was implemented with the plan's **proposed** option. Each is
small and reversible.

| ID | Implemented | How to reverse |
|---|---|---|
| R2 | Map scale always from the whole year; kommuner outside the risk filter greyed, tooltip "Ej i urvalet" | pass `include_codes=None` in `riksoversikt.py` |
| R3 | Riksöversikt deltas compare like with like when filtered ("mot 2023, samma urval") | compute `prev_df` without the filter |
| R4 | Risk filter moved from the sidebar to the top of Riksöversikt; gone from Startsida (it had no effect there) | n/a (filter only ever affected Riksöversikt) |
| R5 | Sidebar sections Översikt / Kommun / Metod; Kommunanalys above Riskdekomposition; "Källor och metod" | edit `sections` in `app/ui/shell.py` |
| R6 | Riskdekomposition opens on the kommun chosen on Kommunanalys (first visit: rank 1) | ignore `selected_municipality` in `riskdekomposition.py` |
| R9 | Trend lines unsmoothed | `smooth: True` in `build_line_trend` |
| R10 | `streamlit>=1.67.0,<2`, `streamlit-echarts>=0.7.0,<0.8` | `requirements.txt` |
| R11 | Year persists on every page (one widget in the router) | n/a (bug fix) |
| R12 | National PDF also on Riksöversikt | remove the button at the end of `riksoversikt.py` |
| R13 | "std" unit removed from Median KRI (explained in its help text) | n/a |

R1, R7 and R8 were resolved before the modernization (plan §A0).

## Completed per task

| Task | Result |
|---|---|
| T00 | Dependency floors pinned; `tests/test_app_smoke.py` (12 tests: every page through the router, sidebar present, year persistence and URL, shared kommun, KPI delta signs, empty filter, missing sensitivity layer) |
| T01 | `app/formatting.py` + 15 tests; all pages, map tooltips and tables use it |
| T02 | New tokens in `COLORS`, `INDICATOR_COLORS`, `SPACING`, `RADIUS`; native `[theme]`/`[theme.sidebar]`; Google Fonts and IBM Plex Mono removed (bundled Source Sans 3, tabular figures); contrast fixes (eyebrows `accent_text`, tertiary text, Medel badge text); global focus ring; no hover lift on static cards; hero without gradient |
| T03 | `app/data.py`: one cached loader for results and sensitivity, `modal_agreement`, `cached_pdf`; four page-local loaders removed |
| T04 | `st.navigation` router in `app/main.py`; `app/ui/shell.py` (sidebar, header, footer); five duplicated sidebars removed; URLs unchanged; views moved to `app/views/` (see log: legacy multipage mode) |
| T05 | `app/ui/components.kpi()` on `st.metric`: keyboard-reachable help, sparklines on Kommunanalys, one delta rule |
| T06 | Riksöversikt: filter bar with live count, KPIs, map/scale fix (R2), histogram denominators, "Om" popovers replacing four expanders, empty state, PDF export |
| T07 | Kommunanalys: context row (selector, summary, CSV + PDF), sensitivity callout, 3 × 2 KPI grid with sparklines, trend with dynamic years, peer and history tables in Swedish format with legend and `alt`, data quality in its own expander, link to Riskdekomposition |
| T08 | Riskdekomposition: shared kommun, rank in the selector, shared summary, contribution bars coloured by sign with value labels and a "största riskdrivare" line, indicator palette, vectorised trends, link to Kommunanalys |
| T09 | Startsida: solid hero, stat strip via the formatter, two entry buttons, explanation and index visual side by side, steps without hover, three cards that are real links, credibility strip folded into the footer |
| T10 | Charts: `aria`, one Swedish JS number helper for every tooltip and axis, unsmoothed lines, tokens instead of raw hex, palette checked for colour-vision deficiency (proposal failed, adjusted palette adopted, see log) |
| T11 | States (empty filter, missing layer, missing map, peer failure), responsive check at 1440/1024/390 px, one h1 per page, focus visible, table `alt` texts, keyboard walkthrough |
| T12 | Dead helpers and 29 dead CSS rules removed; design-system doc rewritten; README and methodology updated; this report |
| T13 (P2) | "Alla kommuner {år}" table on Riksöversikt (respects the filter, pinned name, uncertainty) + CSV |
| T14 (P2) | Källor: "Källa" link column (SCB tables, Kolada KPI; all verified HTTP 200) and a link to the methodology on GitHub |
| T16 (P2) | "Öppna kommun" on Riksöversikt jumps to Kommunanalys with that kommun |
| T17 (P3, partial) | The year is bound to the URL (`?ar=2015`); kommun is not |

## Deferred

| Task | Why |
|---|---|
| T15 Extract CSS to `kri.css` | Pure refactor, no user-visible change; `theme.py` is already 161 lines (12 %) smaller |
| T17 kommun in the URL | Two pages own the kommun selector; needs a design decision |
| T18 Visual regression screenshots | Playwright now works (Edge); worth adding as a separate task |
| T19 Dark theme | Out of scope by design |

## Files

New: `app/formatting.py`, `app/data.py`, `app/ui/{__init__,shell,components}.py`,
`app/views/startsida.py`, `tests/test_{app_smoke,components,formatting}.py`,
`docs/ux-modernization-{log,report}.md`.
Moved: `app/pages/*.py` → `app/views/*.py` (git rename, staged).
Changed: `app/main.py`, all views, `app/components/{charts,sweden_choropleth,landing_visuals}.py`,
`app/styles/theme.py`, `src/config.py`, `src/report_gen.py`, `.streamlit/config.toml`,
`requirements.txt`, `scripts/verify_swedish_ui.py` (icon names exempt),
`tests/test_sensitivity.py` (shared loader name), `README.md`, `docs/methodology.md`,
`docs/ux-ui-design-system.md`, `UX_UI_MODERNIZATION_PLAN.md`.

Size: Python under `app/` went from 4 459 to 4 132 lines (net -327, -7 %) despite
three new modules and the added features, within the plan's -300 to -500 target.

## Preserved functionality

All 43 features in plan §A3 remain reachable. Behaviour changes are only the
approved-by-default R-items above. Kommun CSV export: same file name, separator,
decimal and BOM; the unemployment column header reads
"Öppet arbetslösa (% av 18-65 år)" since §A0.

## Known limitations

See the log: branca map legend ticks use a decimal point; the Folium map is not
keyboard-operable; some CSS still targets Streamlit-internal test ids.
