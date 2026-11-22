# UX modernization log

Working log for `UX_UI_MODERNIZATION_PLAN.md`. Dates are 2026-11-21 / 22.

## Baseline (before the modernization, after the §A0 pre-modernization fixes)

| Check | Result |
|---|---|
| `python -m pytest -q` | 109 passed, 1 skipped |
| `python scripts/verify_swedish_ui.py` | PASS, 9 files |
| Streamlit | 1.67.0, streamlit-echarts 0.7.0 |

## After the modernization

| Check | Result |
|---|---|
| `python -m pytest -q` | 148 passed, 1 skipped (39 new: 12 page smoke tests, 12 component/chart/map tests, 15 formatting tests) |
| `python scripts/verify_swedish_ui.py` | PASS, 15 files |
| `python -m pyflakes app/` | clean |
| App start | no config warnings (every `[theme]` and `[theme.sidebar]` key accepted) |

## Browser verification (Playwright, Microsoft Edge, headless)

| Check | Result |
|---|---|
| All 5 pages at 1440, 1024 and 390 px | 0 exceptions, exactly one `h1` per page, no horizontal page scroll |
| Cold server, first request a deep link to `/riksoversikt` | renders with sidebar (failed before the `app/pages` → `app/views` rename) |
| Year 2015 chosen on Riksöversikt, then every sidebar link | year stays 2015 on all 5 pages; URL carries `?ar=2015` |
| Sidebar on phone (390 px) | starts collapsed, navy menu button opens it; desktop collapses and re-opens |
| Risk filter "Hög" | caption "Visar 73 av 290 kommuner"; KPI deltas say "mot 2023, samma urval"; map greys out non-Hög kommuner with an unchanged colour scale |
| PDF download (Riksöversikt) | `kri_rapport_2024.pdf`, valid PDF, generated on click |
| CSV "Alla kommuner" with filter | 73 rows, `;` separator, Swedish headers |
| "Öppna kommun" → Eskilstuna | opens Kommunanalys with Eskilstuna; CSV `kri_0484_Eskilstuna.csv` |
| Kommunanalys → Riskdekomposition | same kommun selected |
| Keyboard only | "Om" popover reached by Tab and opened with Enter; 8 KPI help icons reachable; focus ring 2 px solid |
| Console | only the known harmless 404s from Streamlit's `/<page>/_stcore/health` probes |

## Findings during implementation

- **Legacy multipage mode (fixed).** With the views in `app/pages/`, Streamlit
  ran a deep-linked page without the router on a fresh server (`_mpa_v1`), so
  the page had no sidebar and crashed on the missing year. The folder was
  renamed to `app/views/`; `test_every_page_runs_through_the_router` guards it.
- **AppTest and `bind="query-params"`.** Setting the pills value directly in
  AppTest did not stick while the views were in `app/pages/`; after the rename
  `set_value` works and is tested, and `?ar=` is tested separately.
- **Download buttons with help** render two `<button>` nodes inside one
  `stDownloadButton` (Streamlit internals). One widget, one visible button.

## Indicator palette, colour-vision check (T10)

Method: Machado et al. simulation matrices on linear RGB, CIE76 ΔE in Lab, minimum over all pairs.

| Palette | normal | deuteranopia | protanopia | tritanopia | min contrast on white |
|---|---|---|---|---|---|
| Plan proposal (`#2F5D9E #7B5EA7 #2A8A86 #5E6B7D #A07A2C`) | 22.2 | **7.2** | **3.8** | 15.6 | 4.0 |
| Adopted (`#1F4E8C #9A78D6 #2C8F89 #333B47 #A8792A`) | 32.6 | 25.7 | 23.6 | 19.6 | 3.5 |

The proposal collapsed debt vs unemployment under protanopia and dependency vs
population under deuteranopia (ΔE < 10). The adopted palette varies lightness
as well as hue and keeps every graphic at least 3:1 against white (WCAG 1.4.11).

## Known limitations

- The Folium/branca map legend prints tick values with a decimal point ("0.3");
  branca has no locale option. Tooltips on the map use Swedish formatting.
- The Folium map is not keyboard-operable (pan/zoom by mouse or touch); every
  value it shows is also in the tables and the "Alla kommuner" table.
- A handful of CSS rules still target Streamlit-internal `data-testid`
  selectors (sidebar pills, expand button, metric label). They are commented
  as version-sensitive; re-check them after a Streamlit major upgrade.
