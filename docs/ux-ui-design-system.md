# KRI Kontrollpanel, UX/UI design system

How the dashboard is built and styled after the 2026-11 modernization
(`UX_UI_MODERNIZATION_PLAN.md`). This is the reference for changing the UI:
where each thing lives, which token to use, and which rule a new component must
follow.

| Concern | Location |
|---|---|
| Router, page registry | `app/main.py` |
| Pages (views) | `app/views/*.py` |
| Shell: sidebar, page header, footer | `app/ui/shell.py` |
| Components: KPI, card header, risk badge, kommun summary | `app/ui/components.py` |
| Number formatting | `app/formatting.py` |
| Data access (cached) | `app/data.py` |
| Charts (ECharts option builders) | `app/components/charts.py` |
| Map (Folium) | `app/components/sweden_choropleth.py` |
| Landing visuals | `app/components/landing_visuals.py` |
| Remaining CSS, landing HTML helpers, ECharts base | `app/styles/theme.py` |
| Native theme | `.streamlit/config.toml` |
| Tokens and labels | `src/config.py` (`COLORS`, `INDICATOR_COLORS`, `SPACING`, `RADIUS`, `SWEDISH_LABELS`) |

---

## 1. Positioning and principles

A statistical publication, made interactive: numbers with provenance for
municipal finance officers, analysts, journalists and researchers. The navy and
gold identity is kept and refined.

1. **Numbers first, decoration last.** No gradients, no tag chips, no hover lift on static content.
2. **One meaning per colour.** Green, amber and red mean risk class and nothing else. Indicators have their own palette. Navy is structure, gold is brand and selection.
3. **Say it, don't only colour it.** Every coloured state also has text, a sign or an icon.
4. **Provenance at the point of use.** Each card explains itself in an "Om" popover in its header.
5. **Same control, same place.** The year lives in the sidebar; a page-specific filter lives at the top of its page.
6. **Swedish numeric typography.** Decimal comma, narrow no-break space (U+202F) for thousands, ASCII hyphen with spaces for ranges ("3 - 9"), "73 av 290" for counts, tabular figures.

---

## 2. Application shell

### 2.1 Router (`app/main.py`)

`apply_streamlit_theme()` → `st.navigation(PAGES, position="hidden")` →
`load_kri_data()` → `render_sidebar()` → `page.run()`.

| Page | File | URL | Sidebar section |
|---|---|---|---|
| Startsida | `views/startsida.py` | `/` | Översikt |
| Riksöversikt | `views/riksoversikt.py` | `/riksoversikt` | Översikt |
| Kommunanalys | `views/kommunanalys.py` | `/kommunanalys` | Kommun |
| Riskdekomposition | `views/riskdekomposition.py` | `/riskdekomposition` | Kommun |
| Källor och metod | `views/kallor.py` | `/kallor` | Metod |

**Why `app/views/` and not `app/pages/`:** a folder named `pages/` next to the
entry script switches Streamlit into its legacy multipage mode. In that mode a
deep link such as `/riksoversikt` can run the page without the router on a
fresh server, so the page has no sidebar and no year. Never recreate an
`app/pages/` folder. `tests/test_app_smoke.py::test_every_page_runs_through_the_router` guards this.

Pages render after the shell, so heavy imports (ECharts, Folium, scikit-learn)
at the top of a view never delay the branded shell on a cold first visit.

### 2.2 Sidebar (`render_sidebar`)

Brand block → sections ÖVERSIKT / KOMMUN / METOD with `st.page_link(Page)` →
"Analysår" pills → footer ("Källa: SCB, Arbetsförmedlingen via Kolada · Data
2010 - 2024 · KRI v1.0").

The sidebar uses Streamlit's own collapse and expand controls (the expand button
is restyled navy so it is visible on the light page). Width is set natively with
`set_page_config(initial_sidebar_state=260)`, which is "auto": expanded on
desktop, collapsed on phones. Never force the width in CSS; that breaks
collapsing.

### 2.3 Shared state

| Key | Owner | Read by | Notes |
|---|---|---|---|
| `ar` | sidebar year pills | router | `required=True`, `bind="query-params"`: the URL carries `?ar=2015`, so views are shareable |
| `selected_year` | router (from `ar`) | every view | always an `int` |
| `selected_risks` | Riksöversikt filter (`rv_risk_filter`, `persist_state="session"`) | Riksöversikt | empty list = all |
| `selected_municipality` | Kommunanalys and Riskdekomposition selectors | both | shared in both directions |
| `kri_df` | router | legacy readers | kept for backward compatibility |

### 2.4 Page header and footer

`render_page_header(eyebrow, title, subtitle, meta_value, meta_label="Analysår")`
renders the page's only `h1`. Eyebrows come from a fixed set: "Översikt",
"Kommun", "Metod". Källor uses `meta_label="Analysperiod"`.

`render_footer(first_year, last_year)` closes every page with the source line.

---

## 3. Tokens

### 3.1 Colours (`COLORS`, mirrored in `.streamlit/config.toml`)

| Token | Value | Use | Contrast on white |
|---|---|---|---|
| `primary` | `#0B1F3F` | sidebar, headings, primary buttons | 16.2 |
| `primary_hover` | `#16305C` | hover on primary surfaces | |
| `secondary` | `#4A6FA5` | focus ring, supporting blue | 5.0 |
| `accent` | `#C4A35A` | decorative and selection only (gold bar, selected year on navy) | non-text |
| `accent_text` | `#8A6A1F` | gold-toned text on light surfaces (eyebrows) | 5.05 |
| `bg` / `card_bg` / `surface_muted` | `#F7F8FA` / `#FFFFFF` / `#F1F3F6` | surfaces | |
| `border` / `border_strong` | `#E3E6EB` / `#C9CFD8` | card borders / control borders | |
| `text_primary` / `text_secondary` / `text_tertiary` | `#1A1A2E` / `#6B7280` / `#6E7581` | text | 17.1 / 4.8 / 4.6 |
| `low_risk` / `high_risk` | `#2E7D5B` / `#B94A48` | Låg / Hög, fill and text | 5.0 / 5.1 |
| `medium_risk` | `#D4A03C` | Medel **fill only** | non-text |
| `medium_risk_text` | `#8F5F0A` | Medel text and badges | 5.5 |

Existing keys are never removed or renamed (`report_gen` and tests read them).
No raw hex in views or components: use the tokens.

### 3.2 Indicator palette (`INDICATOR_COLORS`)

| Indicator | Colour |
|---|---|
| Skuld per capita (`debt`) | `#1F4E8C` |
| Öppet arbetslösa (`unemployment`) | `#9A78D6` |
| Försörjningskvot (`dependency_ratio`) | `#2C8F89` |
| Befolkningstillväxt (`population_growth`) | `#333B47` |
| Skattekraft (`tax_base`) | `#A8792A` |

Chosen so every pair stays apart (CIE76 ΔE ≥ 19.6) under simulated deuteranopia,
protanopia and tritanopia, and every colour has at least 3:1 contrast on white.
Rerun the check in `docs/ux-modernization-log.md` before changing a value.

### 3.3 Typography

Streamlit's bundled Source Sans 3; no external font request. Numbers use the
same sans with `font-variant-numeric: tabular-nums`. Monospace only for code
on Källor.

| Role | Size / weight |
|---|---|
| Page title (h1) | 28 / 700 (24 below 640 px) |
| Card title | 15 / 700 |
| Body | 15 / 400 |
| Caption, help | 13 / 400, `text_secondary` |
| Micro label (KPI label, table header, eyebrow) | 11-12 / 600, uppercase |
| KPI value | `metricValueFontSize` 1.75rem / 600 |

### 3.4 Spacing, radius, focus

`SPACING` 4 · 8 · 12 · 16 · 24 · 32 · 48 px. `RADIUS` 6 px cards and inputs
(`baseRadius`), 4 px pills. Cards have a 1 px border and no shadow. Every
focusable element shows a 2 px `secondary` outline with 2 px offset.

---

## 4. Components (`app/ui/components.py`)

### 4.1 `kpi(label, value, *, delta, better_when, help, period_label, spark)`

A bordered `st.metric`. **Delta rule, product-wide:**

- the arrow shows the sign of the change (▲ increase, ▼ decrease);
- the colour shows desirability: `better_when="lower"` (KRI, skuld, arbetslöshet,
  försörjningskvot, högriskantal) → red on increase; `"higher"` (skattekraft,
  befolkning, **rang**, because rang 1 is the most vulnerable) → green on increase;
- `delta=None` (no previous year) and "Oförändrat" show grey without an arrow;
- `period_label` says what is compared ("mot 2023", "mot 2023, samma urval");
- delta text carries its unit: `+0,05`, `-2 platser`, `-42 kr`, `+0,5 p.e.`, `+13,2 %`.

Use `indicator_delta(current, previous, nd=, unit=)` to build the text.
`help` is reachable by mouse, keyboard and touch. `spark` adds the 15-year line.

### 4.2 `card_header(title, subtitle, help_md=None)`

Title and subtitle; with `help_md` an "Om" popover on the right holds the
explanation that used to sit in a stack of expanders.

### 4.3 `risk_badge(risk_class)` and `render_kommun_summary(row, sens_row, n_total)`

Badge: tinted background, dark risk-coloured text, the words "Hög risk" /
"Medel risk" / "Låg risk". Never white text on amber. The summary line is
`badge · KRI 1,07 · Rang 6 av 290 · Osäkerhet 3 - 9` (uncertainty only when
the sensitivity layer exists).

### 4.4 Tables

Top 15 on Riksöversikt: HTML `.kri-table` with risk badges. Data tables:
`st.dataframe` with a pandas Styler for Swedish formats and best/worst tints,
`column_config` for help and pinning, `alt` text for screen readers, and a
caption legend ("Rött = sämsta värdet i kolumnen, grönt = bästa").

### 4.5 Exports

`st.download_button(on_click="ignore")`, so a download never reruns the page.
The PDF passes a callable (`lambda: cached_pdf(year)`): it is generated on
click, once per year per server (`app/data.cached_pdf`). CSV keeps Swedish Excel
conventions: `;` separator, `,` decimal, UTF-8 with BOM.

### 4.6 States

| State | Pattern |
|---|---|
| Loading | `st.cache_data(show_spinner="Laddar data...")` |
| Empty filter | `st.info("Inga kommuner matchar filtret. ...")`, rest of page skipped |
| Missing sensitivity layer | no uncertainty column, sentence or interval; no message (degrades silently) |
| Missing GeoJSON | `st.warning` in the map card, rest of page works |
| Missing results file | `st.error` with the pipeline command, `st.stop()` |
| Peer calculation failure | `st.warning` in Swedish, exception logged, no traceback shown |

---

## 5. Formatting (`app/formatting.py`)

`fmt_decimal(v, nd)` · `fmt_int(v)` · `fmt_signed(v, nd)` · `fmt_pct(v, nd)` ·
`fmt_pp(v, nd)` · `fmt_kr(v)` · `fmt_count_of(n, total)` · `fmt_range(a, b)` ·
`fmt_range_decimal(a, b, nd)`. Pure functions; `None`/NaN render "Saknas";
`-0,00` never appears. Chart tooltips and axes use the matching JavaScript helper
`_JS_FMT` in `charts.py`.

---

## 6. Charts (`app/components/charts.py`)

- Base options from `theme.get_echarts_base_options()`: `aria.enabled` (ECharts
  writes a text description for screen readers), 250 ms animation, sans font.
- Risk zones always come from `RiskScale` built on the **unfiltered** year
  (`for_year`) or the whole period (`pooled`), so chart colours match `risk_class`.
- Annual lines are straight (`smooth: False`): smoothing would imply values between years.
- Contribution bars: colour by sign (red raises risk, green lowers it) plus a signed value label.
- Comparison bars: `INDICATOR_COLORS`, the same colour for an indicator everywhere.
- Histogram tooltip denominators are the number of kommuner actually plotted.

The map (`sweden_choropleth.py`) builds its colour scale from the whole year.
With a risk filter, kommuner outside it are drawn light grey with "Ej i urvalet"
in the tooltip. Known limitation: the branca legend ticks use a decimal point.

---

## 7. Copy rules

All user-facing text is Swedish (`scripts/verify_swedish_ui.py` enforces it,
including no en/em dashes, no "x till y" between numbers and no "a / b" counts).
Streamlit icon identifiers (`:material/...:`) are exempt. The unemployment
indicator is always "Öppet arbetslösa (% av 18-65 år)": a share of all residents,
not of the labour force.

---

## 8. Testing

| Test | Covers |
|---|---|
| `tests/test_app_smoke.py` | every page renders through the router; sidebar on every page; year persists across pages and via `?ar=`; kommun selection shared; KPI delta signs; empty filter; missing sensitivity layer |
| `tests/test_components.py` | delta rule, chart conventions (aria, no smoothing, sign colours, indicator palette, denominators), map filter keeps the scale |
| `tests/test_formatting.py` | every formatter incl. signed zero, NaN, numpy scalars |
| `scripts/verify_swedish_ui.py` | Swedish-only UI copy |

Browser checks (Playwright via Edge) are recorded in `docs/ux-modernization-log.md`.
