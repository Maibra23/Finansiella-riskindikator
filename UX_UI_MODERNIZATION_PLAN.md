# UX/UI Modernization Plan: KRI Kontrollpanel

**Product:** Kommunal Finansiell Riskindikator (KRI), Streamlit dashboard
**Baseline audited:** branch `master` @ `f1f1d96` (2026-10-25), identical to `origin/master`
**Plan date:** 2026-11-17
**Status:** PROPOSAL, awaiting approval. No source files have been modified.

> Branch check performed before the audit:
> - `master` = `origin/master` (`f1f1d96`) is the latest version.
> - `proposal/data-validity` (`27e362f`) is fully merged into `master`.
> - `backup/local-master-before-sync` and `origin/cursor/dev-environment-setup-a214` share **no common history** with `master` (pre-rewrite history) and lack newer modules (`src/risk_scale.py`, `src/sensitivity.py`, their tests). They are stale and must not be used as a base.

---

## How to read this document

- **Part A** explains *what* should change and *why*, grounded in the code.
- **Part B** explains *how*: prioritized tasks, a five-day schedule, one self-contained Claude Code prompt per task, a regression checklist, and a rollback strategy.
- Items marked **⚠ REVIEW** change observable behaviour, not only appearance. Each is listed in §A10 and must be explicitly approved, rejected, or modified before implementation.
- File references use `path:line` against `f1f1d96`.

---

# PART A: UX/UI MODERNIZATION PROPOSAL

## A1. Executive summary

### Current product assessment

KRI is a focused, methodologically serious analytics product: a composite financial-vulnerability index for all 290 Swedish municipalities, 2010 - 2024 (4 350 observations), with risk decomposition, peer analysis, a weight-sensitivity band, CSV/PDF export, and an unusually honest methodology page. The data layer is solid: 109 tests pass, the Swedish-copy checker passes, and all five pages render without exceptions under a headless `AppTest` run.

The visual identity (navy + gold, "banking / public-sector analytics") is appropriate for the domain and worth keeping. The problems lie **underneath the surface**: the application shell, the consistency of data presentation, and several interaction defects that undermine trust in a product whose whole value is trustworthiness.

### Main UX/UI weaknesses (ranked by impact)

1. **Inconsistent and partly wrong financial signalling.** Kommunanalys inverts the KPI delta colour/arrow: a worsening KRI shows a **green ▼** (`app/pages/kommunanalys.py:199-214` combined with `.delta-down` = green in `app/styles/theme.py:320-325`). Riksöversikt uses the opposite convention. Decimal separators switch between `0,42` (Startsida/Riksöversikt) and `0.42` (Kommunanalys/Riskdekomposition).
2. **The shell is copy-pasted five times.** Sidebar brand, navigation, year pills, risk legend and footer are duplicated in every page file (~40 - 90 lines each). This causes real defects: returning to **Startsida resets the selected year and the risk filter** (`app/main.py:103-110, 132-139` ignore `session_state`). Riskdekomposition does not remember the selected municipality, while Kommunanalys does.
3. **Controls that do nothing or lie.** The risk filter on Startsida has no effect on any visible content. On Riksöversikt, the map's help text says the map "always shows the selected year's data", but the code passes the *filtered* frame: filtered-out municipalities are painted as if KRI = 0 (neutral grey), and the colour breakpoints are recomputed from the filtered subset, so they no longer match the risk classes (`app/pages/riksoversikt.py:393`, `app/components/sweden_choropleth.py:113, 119`).
4. **False affordances and hidden actions.** Landing "Vad hittar du här?" cards look clickable (hover shadow) but are not links. Step cards also lift on hover. The CSV and PDF exports, the only "output" actions in the product, are buried in a collapsed expander at the bottom of Kommunanalys.
5. **Accessibility gaps.** Gold eyebrow text is 2.4:1 contrast, tertiary text 2.5:1, and white-on-amber "Medel" badges 2.4:1 (all fail WCAG AA 4.5:1). KPI explanations exist only as HTML `title` attributes, which keyboard and touch users cannot reach. The peer and history tables communicate best/worst by colour tint alone.
6. **Styling architecture is fragile.** One 1 000-line CSS string with ~150 `!important` rules targets Streamlit-internal `data-testid` selectors. Much of it (dark sidebar, sidebar button text colour, link colours) can now be expressed natively through `[theme]` / `[theme.sidebar]` in `.streamlit/config.toml` (verified available in the installed Streamlit 1.67.0).

### Modernization objectives

| # | Objective | Measured by |
|---|---|---|
| O1 | One app shell, one source of state | `st.navigation` router; year/filter/kommun persist across all pages |
| O2 | Correct, consistent financial presentation | One formatting module, Swedish separators everywhere, uniform delta semantics |
| O3 | Honest controls | Every control visibly affects what it claims; no false affordances |
| O4 | WCAG 2.1 AA for text and essential UI | All text tokens ≥ 4.5:1; help text keyboard-reachable; no colour-only meaning |
| O5 | Clearer task flow | Primary actions (analyse a kommun, export) visible without expanding anything |
| O6 | Maintainability | Native theme config replaces CSS overrides; duplicated code removed; regression harness in `tests/` |

### Expected improvements

A product that looks like the same brand but feels markedly more mature: calmer surfaces, consistent numerals, visible actions, a sidebar that behaves the same on every page, and no states where the UI contradicts the data. Code size in `app/` should *shrink* (estimated −300 to −500 lines) despite the improvements.

---

## A2. Existing application assessment

### A2.1 Architecture (as built)

```
app/main.py                 entry point + landing page + sidebar (copy 1 of 5)
app/pages/riksoversikt.py   national overview         + sidebar (copy 2) + own data loader
app/pages/riskdekomposition.py  driver analysis       + sidebar (copy 3) + own data loader
app/pages/kommunanalys.py   municipality deep dive    + sidebar (copy 4) + own data loader
app/pages/kallor.py         sources & method          + sidebar (copy 5) + own sensitivity loader
app/styles/theme.py         set_page_config + ~1000 lines injected CSS + HTML render helpers + ECharts style helpers
app/components/charts.py    6 ECharts option builders (JS formatters via placeholder wrapper)
app/components/sweden_choropleth.py  Folium + branca choropleth, rendered with st_folium
app/components/landing_visuals.py    weight bars + flow SVG (HTML)
src/config.py               COLORS, DIVERGING_SCALE, RISK_CLASS_COLORS, MAP_TILES, TYPOGRAPHY, SWEDISH_LABELS, MUNICIPALITIES, WEIGHTS, SENSITIVITY
src/risk_scale.py           RiskScale: single source for zone boundaries (used by charts)
src/clustering.py           get_peer_municipalities (Euclidean distance on z-scores)
src/validators.py           get_municipality_flags (special-case notes)
src/report_gen.py           generate_report(kri_df, report_year) -> PDF bytes (ReportLab, ~2 s)
data/processed/*.parquet    kri_results (4350 × 21), kri_sensitivity (optional layer)
scripts/verify_swedish_ui.py  AST checker: no English, no en/em dash, no "a / b" counts, no "x till y" ranges in app/
```

- **Multipage mechanism:** legacy `pages/` auto-discovery, with auto-nav hidden (`client.showSidebarNavigation = false`) and custom `st.sidebar.page_link` lists. `main.py` does **not** run when a sub-page is shown, which is why every page re-implements the sidebar.
- **State:** `st.session_state` keys `kri_df`, `selected_year`, `selected_risk`, `selected_risks`, `selected_municipality`. Widget keys differ per page (`main_year_pills`, `rv_year_pills`, `rd_year_pills`, `ka_year_pills`, `rv_risk_pills`, `main_risk_pills`).
- **Caching:** `@st.cache_data` on four separate but identical parquet loaders plus the GeoJSON loader.
- **No auth, no database, no write paths.** Network access is used only by the offline pipeline (`scripts/run_pipeline.py`) and by the map basemap tiles (Esri) at runtime.
- **Environment finding:** `streamlit-echarts` was **not installed** in the active local Python 3.12 environment, so three of four pages could not render locally. It was installed during this audit (resolved to 0.7.0, which requires `streamlit>=1.53`). `requirements.txt` declares `streamlit>=1.49.0` and `streamlit-echarts>=0.4.0`, an inconsistent floor, and Streamlit Cloud will resolve to whatever is newest at deploy time.

### A2.2 Navigation (as built)

Sidebar (dark navy, fixed 260 px): brand block → "Navigation" → Startsida, Riksöversikt, Riskdekomposition, Kommunanalys, Källor → "Välj år" pills → (Startsida, Riksöversikt only) risk legend + "Filtrera riskklass" pills → source footer ("Senast uppdaterad 2024-12-31", which is a hardcoded string, not a data vintage).

Issues:
- Order puts **Riskdekomposition before Kommunanalys**, although the natural journey is national → one municipality → why. Both are municipality-level views but are not grouped.
- No breadcrumbs or "you are here" beyond link highlight. The page eyebrows are inconsistent ("Sida 01 · Nationell översikt", "Analysverktyg", "Kommunanalys" (duplicates the title), "KRI · Kommunal Finansiell Riskindikator").
- Riskdekomposition's footer block is missing (documented in `docs/ux-ui-design-system.md` §5.5).
- Global Streamlit header is hidden with CSS. The sidebar re-open control is rescued with a `collapsedControl` test-id selector, which is a known fragility across Streamlit versions.

### A2.3 Visual identity (as built)

- Palette: navy `#0B1F3F`, gold `#C4A35A`, risk green/amber/red, neutral greys. Appropriate and recognisable, so it is **kept**.
- Type: Source Sans Pro + IBM Plex Mono via Google Fonts `<link>` (Streamlit already ships Source Sans 3, so this is a second download of nearly the same face). Mono is used for every number (KPI values, deltas, tables, axis labels), which reads "terminal" rather than "financial statement".
- Radius 4 px on cards, but 8 px on the inline Riskdekomposition summary card. 2 px on pills.
- Landing hero uses a three-stop gradient. Steps and nav cards have hover shadows.
- Many raw hex values in page files (`#2E7D5B`, `#D4A03C`, `#B94A48`, `#6B7280`, `#EEF0F3`, `#9CA3AF`, `#1A1A2E`) despite the `COLORS` dict.

### A2.4 Component patterns (as built)

| Pattern | Implementation | Used on | Issues |
|---|---|---|---|
| Page header | `render_page_header()` HTML | all 4 sub-pages | `Analysår` meta shown on Källor with "2010 - 2024" (not a year) |
| Card header | `render_card_header()` HTML | all sub-pages | Tag chips ("Histogram", "Rankning", "Tidserie") add noise, not information |
| KPI card | `render_kpi_card()` HTML + `title` tooltip | Riksöversikt (4), Kommunanalys (6) | tooltip inaccessible; delta semantics differ per page |
| Summary strip | inline HTML f-strings | Riskdekomposition, Kommunanalys | duplicated, different designs, `.` decimals, white-on-amber badge |
| Bordered container | `st.container(border=True)` + CSS override | Riksöversikt, Startsida | CSS forces padding/radius on an internal test-id |
| HTML table | `_table_html()` + `.kri-table` | Riksöversikt (top/bottom 15) | not sortable; fine for top-15 |
| Data table | `st.dataframe` + pandas Styler | Kommunanalys, Källor | colour-only extremes; `.` decimals; "Avstånd" unexplained |
| Explanations | `st.expander` + `st.caption` | Riksöversikt (4 expanders), Källor | four expanders stacked under charts, help far from the thing it explains |
| Charts | `st_echarts` + builders | 3 pages | `smooth: true` on annual data; contribution bar colours encode nothing (position-based palette); hardcoded "/ 290" in tooltips |
| Map | Folium + `st_folium(returned_objects=[])` | Riksöversikt | filter/scale defect (see A1) |

### A2.5 Interaction patterns (as built)

- Year: sidebar pills (single). Risk: sidebar pills (multi, empty = all).
- Municipality: `st.selectbox` (Kommunanalys sorted A-Ö and persisted; Riskdekomposition sorted by rank, not persisted, always defaults to rank 1).
- Comparison: `st.multiselect` max 5 with hardcoded defaults (Huddinge, Karlskrona, Malmö, Växjö, Kiruna).
- View toggle: `st.segmented_control` (KRI vs raw debt histogram).
- Export: `st.download_button` (CSV) and a two-step `st.button` → generate → `st.download_button` (PDF). The second button disappears on the next rerun, and the PDF is regenerated on every click (not cached).

### A2.6 Main usability problems (consolidated)

| ID | Problem | Evidence | Severity |
|---|---|---|---|
| U1 | KPI delta colour/arrow inverted on Kommunanalys | `kommunanalys.py:199-214` | Critical (misinforms) |
| U2 | Year/filter reset when visiting Startsida | `main.py:103-110,132-139` | High |
| U3 | Map paints filtered-out kommuner as KRI 0 and rescales breakpoints | `riksoversikt.py:393`, `sweden_choropleth.py:113,119`; contradicts copy at `riksoversikt.py:403-404` | High |
| U4 | Riksöversikt KPI deltas compare a filtered current year with an unfiltered previous year | `riksoversikt.py:222-277` | High (misleading when filtered) |
| U5 | Mixed decimal separators | `kommunanalys.py:186,233,252`, `riskdekomposition.py:200` | High (trust) |
| U6 | Risk filter on Startsida has no effect | `main.py:132-156` vs landing stats `main.py:176-184` | Medium |
| U7 | Landing nav cards look clickable but are not | `theme.py:891-903`, `main.py:269-304` | Medium |
| U8 | Exports hidden in collapsed expander; PDF not cached | `kommunanalys.py:480-517` | Medium |
| U9 | Contrast failures (gold text, tertiary text, white on amber) | measured: 2.40, 2.54, 2.36 | Medium (AA fail) |
| U10 | KPI help only via `title` attribute | `theme.py:1109-1112` | Medium |
| U11 | Riskdekomposition does not reuse selected kommun | `riskdekomposition.py:166-173` | Medium |
| U12 | "Kommuner med hög risk: 73 - 290" reads like a range | `main.py:205-206` | Low |
| U13 | Hardcoded "290", "2010 - 2024", "Senast uppdaterad 2024-12-31" | several | Low |
| U14 | Six KPI cards in one row; long uppercase labels wrap badly below ~1300 px | `kommunanalys.py:228` | Low |
| U15 | Hover lift on non-interactive step cards | `theme.py:842-845` | Low |
| U16 | Histogram tooltip divides by 290 even when filtered | `charts.py:131` | Low |
| U17 | Trend lines smoothed (`smooth: true`), implying intra-year values | `charts.py:427` | Low (analytic honesty) |
| U18 | Contribution bar palette assigned by sorted position, not by indicator or sign | `charts.py:214-235` | Low |

---

## A3. Feature and functionality inventory

Classification: **C** = core, **S** = supporting, **A** = advanced, **AD** = administrative (offline/dev), **X** = experimental/optional layer.

| ID | Feature | Class | Location | User interaction | Dependencies | Current UX/UI issues | Modify? |
|---|---|---|---|---|---|---|---|
| F01 | Load KRI results (cached) + missing-file error | C | `main.py:47-59` (+3 copies) | none (automatic) | `data/processed/kri_results.parquet` | duplicated loaders | Consolidate (no behaviour change) |
| F02 | Sidebar navigation (5 pages) | C | every page | click links | `st.page_link`, `config.toml` | duplicated; order; no grouping | Yes: `st.navigation` |
| F03 | Global year selection (2010 - 2024) | C | sidebar pills, 4 pages | single select | `session_state.selected_year` | resets on Startsida (U2) | Yes: single widget |
| F04 | Risk-class filter (multi, empty = all) | C | sidebar on Startsida + Riksöversikt | multi select | `session_state.selected_risks` | no effect on Startsida (U6); scope unclear | ⚠ Move into Riksöversikt page |
| F05 | Risk legend (dots) | S | sidebar | read | — | duplicated hex | Move with F04 |
| F06 | Landing hero + lead | S | `main.py:186-194` | read | `theme.render_landing_hero` | gradient; no CTA | Restyle, add CTAs |
| F07 | Landing stat strip (KRI interval, high-risk count, period, N) | S | `main.py:196-222` | read (year-aware) | F03 | "73 - 290" ambiguity | ⚠ wording |
| F08 | "Vad är KRI?" explanation | S | `main.py:224-239` | read | — | — | Layout only |
| F09 | Index weights bars + flow SVG | S | `landing_visuals.py` | read | `WEIGHTS` | — | Keep |
| F10 | "Så fungerar det" 3 steps | S | `main.py:243-267` | read | — | false hover affordance | Remove hover |
| F11 | "Vad hittar du här?" cards | S | `main.py:269-304` | none (visual only) | — | not clickable (U7) | Add real links |
| F12 | Credibility strip (sources, KRI v1.0) | S | `main.py:306-316` | read | — | duplicated with footers | Merge into footer |
| F13 | Riksöversikt KPI row (median KRI, high-risk count, median debt, mean pop. change) with YoY deltas + explanations | C | `riksoversikt.py:298-361` | read, hover | F03, F04 | U4, U10, "std" unit | Yes |
| F14 | Choropleth map, hover tooltip (8 fields), pan/zoom, legend | C | `sweden_choropleth.py`, `riksoversikt.py:383-405` | hover, pan, zoom | Folium, Esri tiles, GeoJSON | U3 | ⚠ scale + filter display |
| F15 | KRI distribution histogram with risk-zone colours, median line | C | `charts.py:67-209` | hover | `RiskScale` | U16 | Minor |
| F16 | Raw debt histogram toggle | A | `riksoversikt.py:409-430` | segmented control | — | — | Keep |
| F17 | Top-15 highest / lowest risk tables with risk pills | C | `riksoversikt.py:452-577` | read | F04 | — | Restyle |
| F18 | Uncertainty column (rank p05 - p95 or "gränsfall"), robustness subtitle | A / X | `riksoversikt.py:460-518` | read | `kri_sensitivity.parquet` (optional) | — | Keep; must still degrade silently when file absent |
| F19 | Explanatory expanders: map, distribution, rankings, uncertainty | S | `riksoversikt.py:394-551` | expand | — | far from content | Move into per-card help popovers |
| F20 | Municipality selector (persisted) | C | `kommunanalys.py:140-151` | searchable select | `session_state.selected_municipality` | — | Share with F27 |
| F21 | Summary strip (risk class, KRI, rank, uncertainty) | C | `kommunanalys.py:180-192` | read | F18 | `.` decimals, white-on-amber | Shared component |
| F22 | Six KPI cards with YoY deltas | C | `kommunanalys.py:228-277` | read | — | U1, U14 | Yes |
| F23 | Weight-sensitivity sentence (robust / gränsfall) | A / X | `kommunanalys.py:285-302` | read | F18 | buried as caption | Callout |
| F24 | KRI trend vs Rikssnitt with risk bands | C | `kommunanalys.py:310-328` | hover | `RiskScale.pooled` | hardcoded years, smooth | Minor |
| F25 | 10 most similar kommuner (peer table, extremes highlighted) | A | `kommunanalys.py:336-414` | read | `clustering.get_peer_municipalities` | colour-only, "Avstånd" | Legend + help |
| F26 | Full history table (all years) with extremes highlighted | C | `kommunanalys.py:422-467` | read, sort, scroll | — | `.` decimals | Formatting |
| F27 | CSV export (municipality history; `;` and `,` decimal, UTF-8 BOM) | C | `kommunanalys.py:469-496` | download | — | hidden in expander | Promote |
| F28 | National PDF report for selected year | C | `kommunanalys.py:498-517` | two-step button | `src/report_gen.generate_report` | hidden; regenerated each time; scope (national) on a municipality page | Promote, cache, ⚠ also expose on Riksöversikt |
| F29 | Data quality: flags + completeness metrics + missing per variable | S | `kommunanalys.py:519-555` | read | `validators.get_municipality_flags` | inside export expander | Own section |
| F30 | Riskdekomposition municipality selector + KRI summary card | C | `riskdekomposition.py:166-214` | select | — | not persisted, inline HTML | Shared component |
| F31 | Contribution bar (5 factors) | C | `charts.py:212-265` | hover | — | U18 | Colour by sign |
| F32 | Radar: kommun z-scores vs Rikssnitt, auto-extending frame | A | `charts.py:268-344` | hover | — | — | Keep |
| F33 | Compare 2 - 5 kommuner (grouped bars, total KRI in tooltip) with defaults | A | `riskdekomposition.py:253-293` | multiselect | — | palette | Indicator palette |
| F34 | Multi-kommun KRI trend + Rikssnitt | A | `riskdekomposition.py:301-330` | hover, legend scroll | — | smooth | Minor |
| F35 | Källor: variables & sources table | S | `kallor.py:112-186` | read | — | — | Add source links (P2) |
| F36 | Källor: API documentation (expander) | S | `kallor.py:193-246` | expand | — | — | Keep |
| F37 | Källor: weight sensitivity method + results + δ table | A | `kallor.py:253-320` | read | F18 | δ-table is static text | Keep |
| F38 | Källor: PCA rejection, limitations (expanders) | A | `kallor.py:322-370` | expand | — | — | Keep |
| F39 | Källor: licence table | S | `kallor.py:377-410` | read | — | — | Keep |
| F40 | Page config, About menu, hidden chrome | S | `theme.py:24-40, 72-90` | menu | — | fragile selectors | Keep config, reduce CSS |
| F41 | Data pipeline, sensitivity build, validation scripts | AD | `scripts/*.py` | CLI | network APIs | n/a (out of UI scope) | No |
| F42 | Swedish-copy verifier | AD | `scripts/verify_swedish_ui.py` | CLI | AST | n/a | No (must keep passing) |
| F43 | Test suite (109 pass, 1 skipped) | AD | `tests/` | CLI | data files | no UI smoke tests | Add smoke tests |

**Non-negotiable:** every row above must remain reachable and behave as before, except where a ⚠ REVIEW item in §A10 is approved.

---

## A4. Proposed design direction

### A4.1 Positioning: "statistical publication, interactive"

Users are not traders. They are municipal finance officers (ekonomichefer), regional analysts, journalists, researchers, students and elected officials, and they need **defensible numbers with provenance**. The right reference is the craft of the best Swedish statistical publishers (SCB, ESV, Riksbanken's reports) combined with the interaction quality of modern fintech tools, not a crypto-style dark dashboard.

### A4.2 Design principles

1. **Numbers first, decoration last.** Every visual element must carry data, structure, or a call to action. Remove gradients, tag chips that repeat the chart type, and hover lifts on static content.
2. **One meaning per colour.** Green/amber/red mean risk class and nothing else. Indicators get their own neutral categorical palette. Navy is structure, and gold is brand/selection only.
3. **Say it, don't only colour it.** Every colour-coded state is paired with a text label, sign, or icon.
4. **Provenance at the point of use.** Each card answers "what is this, and where does it come from" via a help popover in its header, not a separate expander stack.
5. **Same control, same place, same behaviour.** Global context (year) lives in the sidebar; page-specific filters live at the top of the page they affect.
6. **Swedish numeric typography.** Decimal comma, narrow no-break space thousands separator, ASCII hyphen with spaces for ranges (project rule), units always shown, tabular figures.

### A4.3 Reference products (quality bar, not templates)

| Reference | What to borrow | What not to borrow |
|---|---|---|
| Stripe Dashboard | KPI typography: large tabular numerals, small muted label, delta with explicit comparison period | Purple brand, marketing gradients |
| Linear | Quiet chrome, grouped sidebar sections, consistent spacing | Dark-by-default |
| Mercury / Ramp | Calm cards with 1 px borders and no shadows; clear primary action per screen | Consumer-banking friendliness |
| Wise | Plain-language explanations next to numbers | Bright green brand |
| Fortnox (modern) | Swedish financial number formatting and table density | Heavy enterprise toolbars |
| SCB / Kolada | Source citation conventions, table structure, terminology | Dated visual style |

### A4.4 Rationale for keeping the existing brand

The navy/gold identity already signals public finance and is consistent across sidebar, PDF report and README. Replacing it would cost time without improving decisions. The modernization therefore **refines** it: fixes contrast, restrains gold to non-text use on light surfaces, replaces mono numerals with tabular sans numerals, and moves to native Streamlit theming.

---

## A5. Proposed information architecture

### A5.1 Navigation (⚠ REVIEW R5)

Implemented with `st.navigation(..., position="hidden")` plus custom `st.sidebar.page_link(st.Page)` entries so the branded sidebar is preserved. URL paths are kept identical to today (`/`, `/riksoversikt`, `/kommunanalys`, `/riskdekomposition`, `/kallor`).

```
KRI Kontrollpanel  (brand)
─ ÖVERSIKT
   Startsida
   Riksöversikt
─ KOMMUN
   Kommunanalys          (moved above Riskdekomposition)
   Riskdekomposition
─ METOD
   Källor och metod      (label change only; URL /kallor unchanged)
─ ANALYSÅR
   [2010 … 2024] pills   (one widget, one key, persists everywhere)
─ footer: Källa: SCB, Kolada · Data 2010 - 2024 · KRI v1.0
```

Risk-class filter: removed from the sidebar and placed in a **filter bar at the top of Riksöversikt** (the only page it affects). `session_state["selected_risks"]` keeps its name and semantics (empty = all).

### A5.2 Shared context

| Key | Owner | Read by |
|---|---|---|
| `selected_year` | router sidebar pills (`key="global_year"`) | all pages |
| `selected_risks` | Riksöversikt filter bar (`key="rv_risk_filter"`) | Riksöversikt |
| `selected_municipality` | selector on Kommunanalys **and** Riskdekomposition (shared) | both |
| `kri_df` | router (kept for backward compatibility) | all |

### A5.3 Content hierarchy per page (summary)

| Page | Question it answers | Primary content | Primary action |
|---|---|---|---|
| Startsida | What is KRI and where do I start? | concept + live stats | "Öppna riksöversikten", "Analysera en kommun" |
| Riksöversikt | Where is risk concentrated this year? | KPIs → map + distribution → rankings | filter by risk class; export PDF |
| Kommunanalys | How exposed is *this* kommun and how has it changed? | summary → KPIs with sparklines → trend → peers → history | change kommun; export CSV / PDF |
| Riskdekomposition | *Why* is this kommun's risk what it is? | contributions + radar → comparison → trend | compare up to 5 |
| Källor och metod | Can I trust this? | sources → sensitivity → limitations → licence | — |

### A5.4 Journey improvements

- Startsida offers two explicit entry points instead of leaving users to discover the sidebar.
- Choosing a kommun on Kommunanalys carries over to Riskdekomposition (and back). Each page has a contextual link to the other ("Visa riskdrivare för {kommun}" / "Visa kommunanalys för {kommun}").
- From Riksöversikt, users can jump straight to a kommun. Links cannot live inside the HTML ranking tables, so a compact selectbox "Öppna kommun" above the tables sets `selected_municipality` and navigates via `st.switch_page` (P2, T16).

---

## A6. Page-by-page redesign specification

### A6.0 Application shell (all pages)

**Current:** duplicated sidebar per file; header hidden via CSS; 1 480 px max width; 260 px forced sidebar width.

**Proposed:**
- `app/main.py` becomes a ~60-line router: `apply_streamlit_theme()` → `load_kri_data()` → `render_sidebar()` → `pg.run()`.
- Landing content moves to `app/pages/startsida.py` (new file, content unchanged except §A6.1).
- `app/ui/shell.py` (new): `render_sidebar(pages) -> int` (returns selected year), `render_page_header(...)`, `render_footer()`.
- Remove the forced `width: 260px !important` (it fights Streamlit's resizable/mobile sidebar). Use `min-width` only.
- Keep `#MainMenu`/`footer` hidden. Re-test the sidebar expand control on 1.67 and use the current test-id if needed (documented as a known fragile selector).

**Must remain unchanged:** page URLs, page titles, About menu text, data error message when parquet is missing.

### A6.1 Startsida (`app/pages/startsida.py`, moved from `app/main.py`)

**Current layout:** gradient hero → 4-cell stat strip → "Vad är KRI?" → index weights + flow SVG → 3 steps with arrows → bordered panel with 3 non-clickable cards → credibility strip.

**Problems:** U6, U7, U12, U15; long vertical scroll at 1440×900 (≈4 screens); gradient hero; duplicated credibility/footer.

**Proposed layout (desktop):**
1. **Hero**, solid navy (`primary`), no gradient, padding reduced ~30 %. Eyebrow (gold on navy is 6.8:1, OK), H1, lead.
2. **CTA row** directly below the hero: two `st.page_link` buttons styled as primary/secondary: "Öppna riksöversikten" → Riksöversikt, "Analysera en kommun" → Kommunanalys.
3. **Stat strip** (unchanged data): `KRI-intervall {år}` `-1,37 - 1,17` · `Hög risk {år}` **`73 av 290`** (⚠ R8) · `Analysperiod` `2010 - 2024` · `Kommuner` `290`. Values in tabular sans 28 px, not mono.
4. **Two-column band** (`st.columns([1.1, 1])`): left "Vad är KRI?" text; right "Indexet i överblick" (weights + flow SVG). Stacks on narrow screens.
5. **Steps**: three cards, no hover effect, arrows kept.
6. **"Vad hittar du här?"**: three `st.container(border=True)` cards, each containing icon + title + description **and an `st.page_link` "Gå till {sida}"**, so the card becomes a real navigation element (F11 fix).
7. Credibility strip removed; content moves to the global footer (F12 preserved there).

**Responsive:** CTA row and two-column band stack below 640 px (Streamlit column behaviour). Stat strip keeps the existing 2- and 1-column breakpoints.

**Must remain:** all copy, live year-aware stats, weights visual, steps content, three destination descriptions.

### A6.2 Riksöversikt (`app/pages/riksoversikt.py`)

**Current layout:** header → 4 KPI cards → map (1.55) | histogram (1.0) with toggle → 4 expanders → 2 HTML tables → footer.

**Problems:** U3, U4, U10, U16; 4 stacked expanders; "std" unit on median KRI; sidebar risk filter scope unclear.

**Proposed layout:**
1. **Page header**: eyebrow "Översikt", H1 "Riksöversikt", subtitle, right meta "Analysår 2024".
2. **Filter bar** (`st.container(horizontal=True)` or columns): label "Riskklass", `st.pills` multi (`Hög`, `Medel`, `Låg`, each with a coloured dot via `format_func`, e.g. "● Hög"), and a live summary caption "Visar 73 av 290 kommuner" / "Visar alla 290 kommuner". Empty selection = all (unchanged semantics).
3. **KPI row**: 4 × `st.metric(border=True)`: Median KRI · Högriskkommuner (`73 av 290`) · Medianskuld per capita (`kr`) · Befolkningsförändring, 5 år (`%`). Each has `help=` (the existing `_KPI_TIP_*` texts, which become keyboard-accessible) and `delta` + `delta_description` "mot 2023". Delta semantics per §A7.5. **⚠ R3:** when a filter is active the previous year is filtered by the same risk classes, and the delta description reads "mot 2023, samma urval".
4. **Map | distribution** (ratio kept). Card header row: title + subtitle + an "ⓘ" `st.popover("Om kartan")` holding the existing expander text (corrected). Tag chips removed.
   - **⚠ R2 Map:** colour scale always built from the **unfiltered** year (matches risk classes). Municipalities outside the filter are drawn with a light neutral fill (`#EEF0F3`, 0.35 opacity) and the tooltip shows "Ej i urvalet" instead of being painted as KRI 0. Help copy is rewritten to match.
   - Histogram tooltip denominator uses the actual count shown (U16).
5. **Rankings**: two bordered cards (unchanged data and robust subtitle), one shared popover "Om rankning och osäkerhet" combining the two former expanders. Table typography: tabular sans numerals, right-aligned, risk pills with text.
6. **Export row (⚠ R12, additive):** "Ladda ner rapport (PDF)" for the selected year, using the same cached generator as Kommunanalys. (P2 also adds "Ladda ner alla kommuner (CSV)" and a sortable all-290 table in an expander "Alla kommuner {år}".)
7. **Footer** via shared helper.

**Empty state:** if the filter leaves 0 rows (only possible if data changes), show `st.info("Inga kommuner matchar filtret.")` instead of KPIs computed on empty frames (today they silently show `0,00`).

**Must remain:** all four KPIs and their explanations, map tooltips (8 fields), pan/zoom, legend, histogram toggle, top/bottom 15, uncertainty column and its silent absence when the sensitivity file is missing.

### A6.3 Kommunanalys (`app/pages/kommunanalys.py`)

**Current layout:** header → selectbox → inline summary strip → 6 KPI cards → caption → sensitivity caption → trend → peer table → history table → expander (CSV, PDF, data quality) → footer.

**Problems:** U1, U5, U8, U14; summary strip uses white text on amber; exports hidden; data quality hidden inside "Dataexport".

**Proposed layout:**
1. **Page header**: eyebrow "Kommun", H1 "Kommunanalys".
2. **Context row** (`st.columns([1.2, 2, 1.2])`):
   - Kommun selectbox (shared `selected_municipality`).
   - **Summary block** (shared component `render_kommun_summary`): risk badge (tinted background + dark text, e.g. "Hög risk"), `KRI 1,07`, `Rang 6 av 290`, `Osäkerhet 3 - 9` (when available).
   - **Actions**: `st.download_button` "Ladda ner data (CSV)" and the PDF control (same button labels as today; see §A7.7 for PDF caching).
3. **Sensitivity callout**: the existing robust/gränsfall sentence in a bordered container with an icon (`:material/verified:` robust, `:material/warning:` gränsfall). Same text.
4. **KPI grid** 3 × 2 (`st.columns(3)` twice), `st.metric(border=True, chart_data=<15-year series>, chart_type="line")`: KRI-poäng, Rang, Skuld per capita, Arbetslöshet, Försörjningskvot, Skattekraft (% av rikssnitt). Deltas fixed (**⚠ R1**): arrow follows the sign of the change; colour follows good/bad (`delta_color="inverse"` where higher is worse; `normal` for skattekraft and rang). Values in Swedish format. The explanatory caption stays below the grid.
5. **Trend card**: title "KRI-trend {first} - {last}" from data (U13), lines unsmoothed (**⚠ R9**).
6. **Peer table card**: same columns, Swedish number formats; `column_config` help for "Avstånd" ("Euklidiskt avstånd mellan kommunernas fem z-poäng; lägre = mer lik"); caption legend "Rött = sämst i kolumnen, grönt = bäst" so the meaning is stated in text.
7. **History table card**: same, Swedish formats.
8. **Datakvalitet** card (moved out of the export expander, same content: flags, three metrics, missing list), collapsed by default via `st.expander("Datakvalitet")`.
9. Contextual link: `st.page_link` "Visa riskdrivare för {kommun}" → Riskdekomposition.

**Responsive:** 3-column KPI grid becomes 1 column below 640 px (Streamlit default). Sparklines keep the cards meaningful when stacked.

**Must remain:** all six KPIs with YoY comparison, sensitivity sentence, trend vs Rikssnitt, 10 peers with extremes highlighting, full history table, CSV (same filename pattern, `;` separator, `,` decimal, UTF-8 BOM, same columns), national PDF, data quality section.

### A6.4 Riskdekomposition (`app/pages/riskdekomposition.py`)

**Current layout:** header → selectbox (sorted by rank, default rank 1) | inline KPI card → contribution bar | radar → compare multiselect → grouped bars → multi trend → footer.

**Problems:** U11, U17, U18; inline HTML card duplicates Kommunanalys strip with different design; `.` decimals; hardcoded "2010 - 2024".

**Proposed layout:**
1. Header (eyebrow "Kommun", H1 "Riskdekomposition").
2. Context row: shared selectbox (**⚠ R6**: initial value = `selected_municipality` if set, else the highest-risk kommun as today; options remain sorted by rank with the rank shown via `format_func`, e.g. "6 · Eskilstuna", while the stored value stays the name) + shared summary block.
3. **Contributions card** (two columns): left contribution bar **coloured by sign** (positive = `high_risk`, negative = `low_risk`, |v| < 0.01 = neutral) with value labels `+0,61`; one-line explanation "Bidragen summeras till KRI {värde}". Right radar (unchanged logic).
4. **Comparison card**: multiselect (2 - 5, same defaults), grouped bars using the fixed **indicator palette** (same colour for "Skuld" everywhere).
5. **Trend card**: dynamic year range, unsmoothed.
6. Contextual link "Visa kommunanalys för {kommun}".

**Must remain:** contribution values, radar with auto-extending frame, comparison defaults and max 5, info message under 2 selections, trend incl. Rikssnitt.

### A6.5 Källor och metod (`app/pages/kallor.py`)

**Current:** header (meta "2010 - 2024" under "Analysår") → sources table → API expander → sensitivity method + results + δ table → PCA expander → limitations expander → licence table.

**Proposed (light touch):**
- Header meta label becomes "Analysperiod" (not "Analysår").
- Page H1 "Datakällor och metod" (was "Datakällor & Metod"). Nav label "Källor och metod" (**⚠ R5**).
- Section headers use the shared card header without tag chips.
- (P2) Sources table: add a `LinkColumn` "Källa" pointing to the SCB table / Kolada KPI pages; add a link to `docs/methodology.md` on GitHub.
- Year pills in sidebar are shown but do not affect this page. Add a caption under the H1 "Avsnittet gäller hela analysperioden." so the global control's irrelevance is explicit.

**Must remain:** all text, both expanders, δ table values, licence table, sensitivity result sentence (computed from data).

---

## A7. Component and design system changes

### A7.1 Colour tokens (`src/config.py` → `COLORS`, new keys added, none removed)

| Token | Value | Use | Contrast (on white) |
|---|---|---|---|
| `primary` | `#0B1F3F` | sidebar, headings, primary buttons | 16.2 |
| `primary_hover` (new) | `#16305C` | hover on primary surfaces | — |
| `secondary` | `#4A6FA5` | supporting blue | 5.0 |
| `accent` | `#C4A35A` | **decorative/selection only** (gold bar, selected pill fill on navy, chart pointer). Never body text on light backgrounds | 2.4 (non-text) |
| `accent_text` (new) | `#8A6A1F` | gold-toned text on light surfaces (eyebrows) | 5.05 |
| `bg` | `#F7F8FA` | app background | — |
| `card_bg` | `#FFFFFF` | surfaces | — |
| `surface_muted` (new) | `#F1F3F6` | table header, filter bar | — |
| `border` | `#E3E6EB` (was `#EEF0F3`) | card borders (now visible) | decorative |
| `border_strong` (new) | `#C9CFD8` | inputs, dividers that identify controls | ≥ 1.6 |
| `text_primary` | `#1A1A2E` | body | 17.1 |
| `text_secondary` | `#6B7280` | labels, captions | 4.83 |
| `text_tertiary` | `#6E7581` (was `#9CA3AF`) | footnotes on white | 4.64 |
| `low_risk` | `#2E7D5B` | Låg (fill and text) | 5.0 |
| `medium_risk` | `#D4A03C` | Medel **fill only** (map, bars) | 2.36 (non-text) |
| `medium_risk_text` (new) | `#8F5F0A` | Medel text and badges | 5.51 |
| `high_risk` | `#B94A48` | Hög (fill and text) | 5.08 |

Badges always use tinted background (12 % of the risk colour) + dark risk text + 1 px border. **No white text on amber.**

`INDICATOR_COLORS` (new, categorical, deliberately avoids red/green/amber):

| Indicator | Colour |
|---|---|
| Skuld per capita | `#2F5D9E` |
| Arbetslöshet | `#7B5EA7` |
| Försörjningskvot | `#2A8A86` |
| Befolkningstillväxt | `#5E6B7D` |
| Skattekraft | `#A07A2C` |

(Validate distinguishability with a colour-vision-deficiency simulator in T10; adjust if any pair collapses.)

### A7.2 Native theme (`.streamlit/config.toml`)

Verified available in Streamlit 1.67.0: `theme.*` and `theme.sidebar.*` incl. `backgroundColor`, `textColor`, `primaryColor`, `borderColor`, `linkColor`, `baseRadius`, `font`, `headingFont`, `codeFont`, `chartCategoricalColors`, `dataframeHeaderBackgroundColor`, `metricValueFontSize`, `metricValueFontWeight`, `red/green/orange*Color`.

```toml
[client]
showSidebarNavigation = false

[theme]
base = "light"
primaryColor = "#0B1F3F"
backgroundColor = "#F7F8FA"
secondaryBackgroundColor = "#F1F3F6"
textColor = "#1A1A2E"
borderColor = "#E3E6EB"
linkColor = "#2F5D9E"
baseRadius = "6px"
font = "sans-serif"            # Streamlit's bundled Source Sans 3
codeFont = "monospace"         # bundled Source Code Pro
metricValueFontSize = "1.75rem"
metricValueFontWeight = 600
dataframeHeaderBackgroundColor = "#F1F3F6"
greenColor = "#2E7D5B"
redColor = "#B94A48"
orangeColor = "#8F5F0A"
chartCategoricalColors = ["#2F5D9E", "#7B5EA7", "#2A8A86", "#5E6B7D", "#A07A2C"]

[theme.sidebar]
backgroundColor = "#0B1F3F"
secondaryBackgroundColor = "#16305C"
textColor = "#E8ECF4"
primaryColor = "#C4A35A"
borderColor = "#24365A"
linkColor = "#FFFFFF"
```

Exact key/value types must be verified at implementation (T02) by starting the app and checking for config warnings in the terminal.

This replaces the CSS blocks at `theme.py:121-223` and `557-592` (sidebar colours, link colours, pill colours) wherever native theming produces the same result. Remaining CSS is kept only for things the theme cannot express (brand block, hero, stat strip, risk pills, table styling).

### A7.3 Typography

| Role | Size / weight | Font | Notes |
|---|---|---|---|
| Page title (H1) | 28 / 700, -0.4 px | Source Sans 3 | one per page |
| Section/card title | 16 / 650 | Source Sans 3 | sentence case |
| Body | 15 / 400, 1.6 lh | Source Sans 3 | max 68ch for prose |
| Caption / help | 13 / 400 | Source Sans 3 | `text_secondary` |
| Micro label (KPI label, table header, eyebrow) | 12 / 600, uppercase, 0.06em | Source Sans 3 | only these three uses |
| KPI value | 28 - 32 / 600 | Source Sans 3, `tabular-nums` | via `metricValueFontSize` |
| Table numbers | 13.5 / 400 | Source Sans 3, `tabular-nums`, right-aligned | |
| Code, API, identifiers | 12.5 | monospace | Källor only |

Drop the Google Fonts `<link>` for Source Sans Pro and IBM Plex Mono (one fewer external dependency and render-blocking request). Numbers use `font-variant-numeric: tabular-nums` instead of mono.

### A7.4 Spacing, radius, elevation

- Spacing scale (px): 4 · 8 · 12 · 16 · 24 · 32 · 48. Page gutter 24, card padding 20, grid gap 16 ("medium"), section gap 32.
- Radius: 6 px cards and inputs (via `baseRadius`), 4 px pills/badges.
- Elevation: **none** on cards (1 px border only). Focus ring: 2 px `secondary` outline with 2 px offset.
- Remove `st.markdown("<div style='height:16px'>")` spacers. Use `st.space()` (available in 1.67) or container gaps.

### A7.5 KPI / metric component

Replace `render_kpi_card` (HTML) with `kpi()` in `app/ui/components.py`, wrapping `st.metric(label, value, delta, delta_color, help, border=True, delta_description, chart_data)`.

Delta rule (single, product-wide):
- Arrow = sign of the numeric change (▲ increased, ▼ decreased), via `delta_arrow="auto"`.
- Colour = desirability: `delta_color="inverse"` when higher is worse (KRI, skuld, arbetslöshet, försörjningskvot, högriskantal), `"normal"` when higher is better (skattekraft, befolkningstillväxt, rang, since a higher rank number means lower risk), `"off"` for "Saknas"/no previous year.
- Delta text always includes the unit: `+0,12`, `+3,4 %`, `+0,30 p.e.` (procentenheter written in full in `help`), `-4 platser`.
- `delta_description` = "mot 2023".

Keep `render_kpi_card` in `theme.py` (unused) until T12 removes it, so rollback stays trivial.

### A7.6 Other components

| Component | Spec |
|---|---|
| `render_page_header(eyebrow, title, subtitle, meta_value, meta_label="Analysår")` | Eyebrow from fixed set: "Översikt", "Kommun", "Metod". `meta_label` lets Källor say "Analysperiod" |
| `card_header(title, subtitle, help_md=None)` | Title + subtitle on left, optional `st.popover(":material/info:")` on right. No tag chip |
| `risk_badge(risk_class)` | Tinted pill with text "Hög risk"/"Medel risk"/"Låg risk"; single implementation (HTML) reused in tables, summaries, tooltips |
| `render_kommun_summary(row, sens_row)` | Badge · KRI · Rang X av N · Osäkerhet a - b. Shared by Kommunanalys and Riskdekomposition |
| `render_footer()` | "Källa: SCB Statistikdatabasen · Arbetsförmedlingen via Kolada · KRI v1.0 · Data 2010 - 2024" |
| Buttons | Primary (navy) = one per screen max (e.g. CTA, PDF). Secondary for other actions. Use native `type=` |
| Forms/inputs | Native widgets only; labels visible (no `label_visibility="collapsed"` without an adjacent visible label) |
| Tables | Top-15: HTML `.kri-table` (kept). Data tables: `st.dataframe` + Styler for formatting/highlight + `column_config` for help/width + `alt` text |
| Notifications | `st.info` (neutral guidance), `st.warning` (data caveats), `st.error` (failures, no raw exception text to users; log details), `st.success` sparingly, `st.toast` after PDF ready |
| Empty states | `st.info` with what to do next ("Välj minst 2 kommuner …") |
| Loading | `st.spinner` with Swedish verb phrase; data load spinner kept ("Laddar data...") |

### A7.7 Charts (`app/components/charts.py`)

- Global: `aria: {enabled: true}` (ECharts generates screen-reader descriptions); `animationDuration` 250; `smooth: false` for all annual lines (⚠ R9).
- Number formatting in all JS formatters via one shared JS helper string (decimal comma, sign, narrow NBSP thousands), replacing ad-hoc `toFixed(..).replace('.',',')`.
- Contribution bar: colour by sign; value labels at bar end.
- Grouped bars: `INDICATOR_COLORS`.
- Histogram: denominator = len(scores).
- Axis value labels: sans (not mono), 11 px, `text_secondary`.
- Chart heights: 320 (small), 380 (standard), 440 (map). Keep existing heights unless layout requires.

### A7.8 Formatting module (`app/formatting.py`, new)

Pure functions with unit tests: `fmt_decimal(v, nd)`, `fmt_int(v)`, `fmt_signed(v, nd)`, `fmt_pct(v, nd)`, `fmt_pp(v, nd)`, `fmt_kr(v)`, `fmt_count_of(n, total)` → "73 av 290", `fmt_range(a, b)` → "3 - 9". Replaces `_fmt_decimal` (2 copies), `_fmt_int_space`, inline f-strings, and Styler format strings. `format_swedish_int` in `theme.py` becomes a thin alias for compatibility (it is imported by pages and possibly by tests).

---

## A8. Industry-specific improvements

| Requirement | How the redesign meets it |
|---|---|
| Consistent currency formatting | `fmt_kr`: "121 706 kr" (NBSP grouping), everywhere incl. tables and map tooltip |
| Percentage vs percentage points | KPI deltas for rates use "p.e." with full term in `help`; levels use "%" |
| Decimal precision | KRI 2 dp, contributions 2 dp in UI (3 dp kept in tooltips where it exists today), rates 1 dp, dependency ratio 3 dp, kr 0 dp |
| Negative values | ASCII hyphen-minus `-0,41` (project rule), explicit `+` for positive deltas and contributions |
| Actual vs estimated | Every value is actual published data; data-quality flags (interpolation, special cases) surfaced in the Kommunanalys Datakvalitet card. Sensitivity band clearly labelled as a robustness measure, not a forecast |
| Periods | Year always visible in page meta and KPI delta description ("mot 2023") |
| Colour not sole signal | risk badges carry text; deltas carry sign + arrow; table extremes get a text legend; map tooltip states class |
| Provenance | per-card help popovers cite source and method; footer on every page; Källor och metod one click away |
| Relative-not-absolute risk classes | add the README's caveat ("Riskklasser är relativa: 25 % av kommunerna är Hög risk varje år") to the Riksöversikt high-risk KPI help and the rankings popover |
| Numerical alignment | right-aligned tabular numerals in all tables |
| Export | CSV keeps Swedish Excel conventions (`;`, `,`, BOM); PDF cached per year and offered where users look for it |

---

## A9. Performance and technical improvements (redesign-relevant only)

1. **Single data load per session** via `app/data.py` (`@st.cache_data`), removing four duplicated loaders. Same parquet file and same dtype handling.
2. **PDF caching:** `@st.cache_data(show_spinner=False)` wrapper around `generate_report(kri_df, year)` keyed by year (~2 s per generation today, repeated on every click). Use `st.download_button(on_click="ignore")` so the download does not rerun the page.
3. **Riskdekomposition/Kommunanalys loops** that filter `kri_df` per year per kommun (`riskdekomposition.py:314-327`, `kommunanalys.py:320-324`) replaced with one `pivot`/`groupby` (same values, about 30 fewer DataFrame scans per rerun).
4. **Map:** GeoJSON copy + per-row `iterrows` is acceptable (≈290 rows). Keep it, but build the colormap from the unfiltered year (R2). Consider `@st.cache_data` on the per-year property dict (P2).
5. **Fewer reruns:** shared year widget means one rerun per change instead of state reconciliation across differently-keyed widgets.
6. **CSS:** fewer `!important` overrides means less breakage on Streamlit upgrades. Optional P2: move remaining CSS to `app/styles/kri.css` read once and injected.
7. **Dependencies:** pin `streamlit>=1.67,<2` and `streamlit-echarts>=0.7,<0.8` (0.7 requires Streamlit ≥ 1.53, and theme keys used here were verified on 1.67). **No new third-party dependencies are proposed.** AgGrid, Plotly and Lucide were considered and rejected: `st.dataframe` + `column_config` covers sorting/search/pinning, ECharts already covers every chart, and Streamlit's built-in `:material/...:` icons cover iconography without a new package.

---

## A10. Feature preservation matrix

| Feature | Current implementation | Proposed change | Preserved? | Risk |
|---|---|---|---|---|
| F01 Data load | 4 identical cached loaders | one `app/data.py` loader | Yes | Low |
| F02 Navigation | 5 copies of `page_link` list | `st.navigation` router, sections, same URLs | Yes (order ⚠ R5) | **Medium** |
| F03 Year | per-page pills, resets on Startsida | one global pill widget | Yes, bug fixed (R11) | Medium |
| F04 Risk filter | sidebar (Startsida, Riksöversikt) | Riksöversikt filter bar | Yes on Riksöversikt; ⚠ R4 removed from Startsida (had no effect) | Low |
| F05 Risk legend | sidebar HTML | dots inside filter options + map legend | Yes | Low |
| F06 - F10 Landing content | HTML helpers | restyled, two-column band | Yes | Low |
| F07 Stat strip | "73 - 290" | ⚠ R8 "73 av 290" | Yes | Low |
| F11 Landing cards | visual only | real `st.page_link` | Improved | Low |
| F12 Credibility | landing strip | global footer | Yes | Low |
| F13 Riksöversikt KPIs | HTML cards, title tooltips | `st.metric` + `help`; ⚠ R3 like-for-like deltas; ⚠ R13 drop "std" unit | Yes | Medium |
| F14 Map | filtered frame drives colours | ⚠ R2 unfiltered scale, out-of-filter greyed | Yes, corrected | Medium |
| F15 - F16 Histograms | ECharts | denominator fix, formatting | Yes | Low |
| F17 - F18 Rankings + uncertainty | HTML tables | restyled; silent fallback kept | Yes | Low |
| F19 Explanations | 4 expanders | 2 popovers in card headers (same text) | Yes | Low |
| F20/F30 Kommun selection | separate, one persisted | shared `selected_municipality` (⚠ R6) | Yes | Low |
| F21/F30 Summary | two inline HTML variants | one shared component | Yes | Low |
| F22 Kommun KPIs | HTML cards, inverted deltas | `st.metric` + sparkline; ⚠ R1 correct colours | Yes, corrected | Medium |
| F23 Sensitivity sentence | caption | callout, same text | Yes | Low |
| F24/F34 Trends | smooth lines | ⚠ R9 straight lines, dynamic title | Yes | Low |
| F25 - F26 Tables | Styler, `.` decimals | Swedish formats, legend, help | Yes | Low |
| F27 CSV | in expander | visible action row; same file format and name | Yes | Low |
| F28 PDF | in expander, uncached | visible, cached; ⚠ R12 also on Riksöversikt | Yes | Low |
| F29 Data quality | inside export expander | own expander | Yes | Low |
| F31 Contribution bar | position palette | sign colours + labels | Yes | Low |
| F32 Radar | unchanged | unchanged | Yes | None |
| F33 Comparison | grouped bars | indicator palette | Yes | Low |
| F35 - F39 Källor | as is | header meta label, ⚠ R5 nav label; P2 links | Yes | Low |
| F40 Page config | `set_page_config` + CSS | same config, less CSS | Yes | Low |
| F41 - F43 Admin | scripts/tests | add smoke tests; nothing removed | Yes | None |

### ⚠ REVIEW items: behaviour changes requiring your decision

| ID | Change | Why | Behaviour affected | Safer alternative |
|---|---|---|---|---|
| **R1** | Fix Kommunanalys KPI delta colour/arrow | Worsening shows green ▼ today | Arrow/colour of 6 KPIs | none; current output is wrong |
| **R2** | Map: unfiltered colour scale; out-of-filter kommuner greyed with "Ej i urvalet" | Today they are painted as KRI 0 and breakpoints drift from risk classes, contradicting the help text | Map look when a filter is active | Make the map ignore the filter entirely (matches today's help text) |
| **R3** | Riksöversikt deltas compare like with like when filtered | Today: filtered 2024 vs unfiltered 2023 | Delta values only when a filter is active | Hide deltas while a filter is active |
| **R4** | Risk filter moves from sidebar into Riksöversikt page; removed from Startsida | It only affects Riksöversikt; on Startsida it did nothing | Location of the control | Keep it in the sidebar but show it only on Riksöversikt |
| **R5** | Nav order (Kommunanalys before Riskdekomposition), sections, label "Källor och metod" | Matches journey; groups municipality views | Sidebar order/labels (URLs unchanged) | Keep order and labels; add sections only |
| **R6** | Riskdekomposition remembers the shared kommun | Continuity between kommun pages | Default selection when arriving from Kommunanalys | Keep default = rank 1 |
| **R7** | Sidebar footer: replace "Senast uppdaterad 2024-12-31" | It is a hardcoded, misleading date (data rebuilt 2026-10-21) | Footer text | Use "Data 2010 - 2024" only. **Need your preferred wording/date.** |
| **R8** | "73 - 290" → "73 av 290" | Dash reads as a range; "av" passes the Swedish-copy checker | Copy | Keep as is |
| **R9** | Trend lines unsmoothed | Smoothing implies values between annual observations | Line shape | Keep smoothing |
| **R10** | Pin dependency floors (`streamlit>=1.67,<2`, `streamlit-echarts>=0.7,<0.8`) | Current floors are inconsistent; theme keys verified on 1.67 | Deploy environment | Pin exact versions |
| **R11** | Year persists when visiting Startsida | Bug fix | Year after navigation | — |
| **R12** | National PDF also offered on Riksöversikt | It is a national report; users look for it there | Additive | Keep only on Kommunanalys |
| **R13** | Remove "std" unit after Median KRI | KRI is a weighted mean of z-scores, not itself in standard deviations; explain in help instead | KPI unit text | Keep "std" |

---

## A11. Expected outcomes

| Improvement | Usability | Consistency | Accessibility | Productivity | Maintainability |
|---|---|---|---|---|---|
| Router + single sidebar | state never lost | identical shell | one landmark structure | fewer clicks to re-set context | −250 lines duplication |
| Formatting module | numbers read the same everywhere | Swedish conventions | screen readers get consistent numerics | faster scanning | tested pure functions |
| `st.metric` KPIs | correct deltas | one delta rule | keyboard-reachable help | sparklines show trend without scrolling | less HTML |
| Contrast tokens | readable labels | tokens in one place | AA text contrast | — | no raw hex in pages |
| Visible exports | output in one click | same action row pattern | real buttons | PDF cached (~2 s → instant on repeat) | — |
| Map/KPI correctness fixes | no contradictory states | map = tables = histogram | — | trust | regression tests added |
| Native theme | — | sidebar/widgets themed by Streamlit | native focus states preserved | — | far fewer `!important` |
| Smoke tests | — | — | — | safe iteration | every page exercised in CI-able tests |

---

# PART B: STEP-BY-STEP IMPLEMENTATION ROADMAP

## B1. Implementation principles

1. Preserve all functionality in §A3. Default = unchanged behaviour unless an approved ⚠ R-item says otherwise.
2. One task = one focused commit (or a few), message prefix `ux(Txx):`.
3. Do not touch `src/` business logic (`index_builder`, `data_cleaner`, `data_fetcher`, `sensitivity`, `clustering`, `report_gen`) except for **adding** tokens/labels to `src/config.py`. Never remove or rename existing `COLORS`/`SWEDISH_LABELS` keys (tests and `report_gen` may use them).
4. No new third-party dependencies.
5. All user-visible text in Swedish. `python scripts/verify_swedish_ui.py` must pass after every task touching `app/` or `SWEDISH_LABELS`.
6. After every task: `python -m pytest -q` (expect ≥ 109 passed plus new tests) and the smoke test from T00.
7. Keep changes reversible: old helpers stay until the final cleanup task removes unused ones.
8. Windows note for this machine: the `python` command is a pyenv-win batch shim. Do **not** pass `>=` or multi-line code via `python -c`. Put scripts in files and quote version specifiers in a requirements file.

## B2. Prioritized task breakdown

Capacity: 5 days × ~8 h = 40 h. **P0 + P1 planned = 37 h** (≈ 8 % buffer). P2 only if ahead of schedule. P3 deferred.

| ID | Pri | Task | Objective | Files | Depends | Est. | Risk |
|---|---|---|---|---|---|---|---|
| T00 | P0 | Branch, environment, smoke-test harness | Safe base + regression net | `requirements.txt`, `tests/test_app_smoke.py` | — | 1.5 h | Low |
| T01 | P0 | Formatting module | One Swedish number format | `app/formatting.py`, `tests/test_formatting.py`, `app/styles/theme.py` | T00 | 2.5 h | Low |
| T02 | P0 | Tokens, native theme, contrast | Design-system foundation | `src/config.py`, `.streamlit/config.toml`, `app/styles/theme.py` | T00 | 3 h | Medium |
| T03 | P0 | Shared data access | One loader set | `app/data.py`, pages | T00 | 1.5 h | Low |
| T04 | P0 | App shell: router, single sidebar, footer, header | Fix state loss, remove duplication | `app/main.py`, `app/pages/startsida.py` (new), `app/ui/shell.py` (new), all pages | T02, T03 | 5 h | **High** |
| T05 | P0 | KPI component + delta semantics | Correct, accessible KPIs | `app/ui/components.py` (new), `riksoversikt.py`, `kommunanalys.py` | T01, T04 | 3 h | Medium |
| T06 | P0 | Riksöversikt redesign incl. map/filter fixes | Core national view | `riksoversikt.py`, `sweden_choropleth.py`, `charts.py`, `tests/test_map.py` | T05 | 4.5 h | Medium |
| T07 | P0 | Kommunanalys redesign incl. exports | Core municipal view | `kommunanalys.py`, `app/ui/components.py`, `app/data.py` | T05 | 4 h | Medium |
| T08 | P1 | Riskdekomposition redesign | Driver view consistency | `riskdekomposition.py`, `charts.py` | T07 | 3 h | Low |
| T09 | P1 | Startsida redesign | Clear entry points | `app/pages/startsida.py`, `theme.py` | T04 | 2 h | Low |
| T10 | P1 | Chart system polish | Consistent, accessible charts | `charts.py`, `theme.py`, `tests/test_risk_scale.py` | T02 | 2.5 h | Low |
| T11 | P1 | States, responsive and accessibility pass | AA + narrow screens + empty/error states | all `app/` | T06-T10 | 3 h | Low |
| T12 | P0 | Regression QA, cleanup, docs, report | Verified delivery | `docs/ux-ui-design-system.md`, `README.md`, theme cleanup | all | 4 h | Low |
| T13 | P2 | All-290 sortable table + year CSV on Riksöversikt | Analytical depth | `riksoversikt.py` | T06 | 2 h | Low |
| T14 | P2 | Källor polish (source links, method link) | Provenance | `kallor.py` | T04 | 1.5 h | Low |
| T15 | P2 | Extract CSS to `app/styles/kri.css` | Maintainability | `theme.py`, `kri.css` | T12 | 2 h | Low |
| T16 | P2 | "Öppna kommun" jump from Riksöversikt | Journey | `riksoversikt.py` | T06, T07 | 1 h | Low |
| T17 | P3 | URL-shareable state (`st.query_params` for år/kommun) | Shareable links | shell, pages | T04 | 2 h | Medium |
| T18 | P3 | Visual regression screenshots (Playwright) | QA automation | `tests/visual/` | needs Chrome installed | 3 h | Low |
| T19 | P3 | Dark theme (`[theme.dark]`) | Preference | config, charts | T02 | 4 h | Medium |

## B3. Five-day schedule

| Day | Theme | Tasks | Hours | Exit criteria |
|---|---|---|---|---|
| 1 | Foundation and design system | T00, T01, T02, T03 | 8.5 | Branch exists; smoke tests green; formatting tested; theme applied with no visual regressions beyond intended colour/typography changes |
| 2 | Shell and navigation | T04, T05 | 8 | Single sidebar; year persists across all 5 pages; URLs unchanged; KPI component in place; R1 fixed |
| 3 | Core pages | T06, T07 | 8.5 | Riksöversikt and Kommunanalys match §A6.2/§A6.3; exports visible; map fix covered by test |
| 4 | Remaining pages and charts | T08, T09, T10 | 7.5 | Riskdekomposition and Startsida match spec; charts unified |
| 5 | QA and refinement | T11, T12 | 7 | Full checklist B5 passed; docs updated; final report written |

If Day 2 (T04) overruns, which is the highest-risk task, defer T09's two-column band and T10's JS-formatter consolidation (keep their bug fixes) rather than compressing QA on Day 5.

**Deferred by design:** T13 - T19 (unless time remains, in order T13 → T16 → T14 → T15).

## B4. Implementation prompts

> Each prompt is self-contained. Paste it into Claude Code from the repo root, on branch `ux/modernization`. Every prompt assumes `UX_UI_MODERNIZATION_PLAN.md` exists in the repo and may be consulted for token values and specs.

---

### Prompt T00: Branch, environment and smoke-test harness

```
TASK T00 (P0): Prepare a safe working branch and a regression harness for the KRI Streamlit dashboard.

CONTEXT
- Repo: Kommunal Finansiell Riskindikator. Streamlit app, entry app/main.py, pages in app/pages/ (riksoversikt, riskdekomposition, kommunanalys, kallor). Latest code is master @ f1f1d96.
- Pages use legacy pages/ multipage + st.sidebar.page_link("main.py"), so a sub-page cannot be run directly as an AppTest entrypoint; it must be reached with AppTest.switch_page from app/main.py.
- streamlit-echarts was missing locally; streamlit-echarts 0.7.0 requires streamlit>=1.53. Installed Streamlit is 1.67.0.
- On this Windows machine `python` is a pyenv-win batch shim: never pass ">=" on the command line (it becomes a redirect) and never use multi-line `python -c`. Use files.

REQUIREMENTS
1. git checkout master && git pull, then git checkout -b ux/modernization. Tag the baseline: git tag ux-baseline-f1f1d96 f1f1d96.
2. requirements.txt: change only these two lines (approved R10):
   streamlit>=1.67.0,<2
   streamlit-echarts>=0.7.0,<0.8
   Install with: python -m pip install -r requirements.txt
3. Create tests/test_app_smoke.py (pytest marker: integration) that:
   - builds AppTest.from_file(<abs path to app/main.py>, default_timeout=180)
   - runs main, then switch_page to each of: pages/riksoversikt.py, pages/riskdekomposition.py, pages/kommunanalys.py, pages/kallor.py (after T04 the paths will change; write the list as a module constant PAGES so T04 only edits that constant)
   - asserts len(at.exception) == 0 and len(at.error) == 0 for each page
   - asserts a known Swedish heading text is present on each page (e.g. "Riksöversikt", "Riskdekomposition", "Kommunanalys", "Datakällor"), searching at.markdown values
   - skips cleanly if data/processed/kri_results.parquet is missing
4. Record a baseline: run `python -m pytest -q` and `python scripts/verify_swedish_ui.py`; paste the summary lines into a new file docs/ux-modernization-log.md under "Baseline".

MUST REMAIN INTACT: all source under app/ and src/ unchanged in this task.

TESTING: pytest must show 109+ passed (plus the new smoke tests) and 1 skipped as before; verifier PASS.

ACCEPTANCE CRITERIA / DONE
- Branch ux/modernization and tag ux-baseline-f1f1d96 exist.
- Smoke tests pass on the unmodified app.
- docs/ux-modernization-log.md contains the baseline numbers.
- Commit: "ux(T00): branch baseline, pin streamlit deps, add page smoke tests".
```

---

### Prompt T01: Swedish formatting module

```
TASK T01 (P0): Create one tested module for all user-facing number formatting.

CONTEXT
- Duplicated helpers today: _fmt_decimal in app/main.py:163 and app/pages/riksoversikt.py:204; _fmt_int_space (riksoversikt.py:217); format_swedish_int in app/styles/theme.py:1069; inline f-strings using "." decimals in kommunanalys.py (e.g. lines 186, 233, 252, 400-407, 457-465) and riskdekomposition.py:200.
- Project rules (enforced by scripts/verify_swedish_ui.py): decimal comma; thousands separator narrow no-break space U+202F (theme.format_swedish_int uses U+00A0, keep that function's output unchanged for compatibility); ranges use ASCII hyphen with spaces "3 - 9"; never "x till y" between numbers; never "a / b" for counts; no en/em dashes.

REQUIREMENTS
1. New file app/formatting.py with pure functions (no Streamlit import):
   fmt_decimal(v, nd=2) -> "1,07", "-0,41", "0,00" (never "-0,00"), thousands with U+202F
   fmt_int(v) -> "121 706" (U+202F)
   fmt_signed(v, nd=2) -> "+0,61" / "-0,17" / "0,00"
   fmt_pct(v, nd=1) -> "4,1 %" (U+202F before %)
   fmt_pp(v, nd=1) -> "+0,3 p.e."
   fmt_kr(v) -> "121 706 kr"
   fmt_count_of(n, total) -> "73 av 290"
   fmt_range(a, b) -> "3 - 9" (ints) ; fmt_range_decimal(a, b, nd=2) -> "-1,37 - 1,17"
   All accept numpy/pandas scalars; NaN/None -> "Saknas".
2. tests/test_formatting.py (marker unit): cover signed zero, negatives, NaN, rounding at .5, large numbers, every function.
3. Replace _fmt_decimal and _fmt_int_space in main.py and riksoversikt.py with imports from app.formatting. Keep their call sites' output identical (same nd values).
4. Do NOT yet change kommunanalys/riskdekomposition (T07/T08 do that).
5. Keep theme.format_swedish_int as is (other modules import it).

MUST REMAIN INTACT: Every string rendered on Startsida and Riksöversikt must be byte-identical to before (compare with AppTest markdown output before/after).

TESTING: pytest -q; verify_swedish_ui.py PASS; smoke tests pass. Add one test asserting fmt_decimal(-0.001) == "0,00".

DONE: module + tests committed as "ux(T01): add Swedish formatting module".
```

---

### Prompt T02: Design tokens, native theme and contrast

```
TASK T02 (P0): Establish the design-system foundation: tokens, native Streamlit theme, contrast fixes.

CONTEXT
- Tokens live in src/config.py COLORS (do not remove or rename existing keys: report_gen and tests may use them).
- app/styles/theme.py apply_streamlit_theme() injects ~1000 lines of CSS, including sidebar colours/link colours/pill colours with many !important rules (theme.py ~121-223 and ~557-592) and a Google Fonts <link> for Source Sans Pro + IBM Plex Mono.
- Streamlit 1.67 supports [theme] and [theme.sidebar] keys incl. backgroundColor, secondaryBackgroundColor, textColor, primaryColor, borderColor, linkColor, baseRadius, font, codeFont, metricValueFontSize, metricValueFontWeight, dataframeHeaderBackgroundColor, chartCategoricalColors, greenColor, redColor, orangeColor.
- Measured contrast failures: accent #C4A35A as text on white 2.40; text_tertiary #9CA3AF on white 2.54; white on medium_risk #D4A03C 2.36.

REQUIREMENTS
1. src/config.py COLORS: change values border -> "#E3E6EB", text_tertiary -> "#6E7581"; ADD keys primary_hover "#16305C", accent_text "#8A6A1F", surface_muted "#F1F3F6", border_strong "#C9CFD8", medium_risk_text "#8F5F0A". Add INDICATOR_COLORS dict keyed by the five indicator ids used in WEIGHTS (debt, unemployment, dependency_ratio, population_growth, tax_base) with values #2F5D9E, #7B5EA7, #2A8A86, #5E6B7D, #A07A2C. Add SPACING = {"xs":4,"sm":8,"md":12,"lg":16,"xl":24,"2xl":32,"3xl":48} and RADIUS = {"card":6,"pill":4}.
2. .streamlit/config.toml: keep [client] showSidebarNavigation=false; add [theme] and [theme.sidebar] exactly as in UX_UI_MODERNIZATION_PLAN.md §A7.2. Start the app (python -m streamlit run app/main.py --server.headless true) and confirm no config warnings in the terminal; adjust any key Streamlit rejects and note it in docs/ux-modernization-log.md.
3. theme.py CSS:
   - Remove the Google Fonts <link>; font-family rules become "Source Sans 3", "Source Sans Pro", sans-serif (Streamlit bundles Source Sans 3).
   - Replace font-family IBM Plex Mono on numbers (.kpi-value, .kpi-delta, .lp-stat-value, .kri-table td.num, .rank-cell, sidebar buttons, .card-tag, .lp-step-num) with the sans stack + font-variant-numeric: tabular-nums. Keep monospace only for code.
   - Eyebrow/lp-eyebrow/lp-section-title text on LIGHT backgrounds use accent_text; gold on navy (sidebar, hero) stays accent.
   - Remove sidebar colour/link/button rules that the native [theme.sidebar] now produces; keep only what is still visibly needed (brand block, selected-pill gold fill if native primaryColor does not give it). Verify visually in a browser at 1440 px before deleting each block.
   - Remove `width: 260px !important` on the sidebar; keep min-width 260px.
   - Remove hover box-shadow/border change on .lp-step (non-interactive).
   - Add a global :focus-visible outline: 2px solid COLORS["secondary"], offset 2px.
   - Risk pill .medel text uses medium_risk_text.
4. No raw hex in new CSS: interpolate COLORS keys.

MUST REMAIN INTACT: all pages render; sidebar still dark navy with readable links; selected year pill visually distinct; risk pills unchanged in meaning; nothing else moves.

TESTING: smoke tests; pytest; verify_swedish_ui; manual browser check of all 5 pages at 1440 and 768 px; re-run the contrast script values for the changed tokens (record in log).

ACCEPTANCE: no text token below 4.5:1 on its background; no config warnings; app visually coherent.
DONE: commit "ux(T02): design tokens, native theme, contrast fixes".
```

---

### Prompt T03: Shared data access module

```
TASK T03 (P0): Consolidate data loading.

CONTEXT
- Identical parquet loaders exist in app/main.py:47 (load_kri_data, shows st.error + st.stop if missing), riksoversikt.py:89 (_load), riskdekomposition.py:71, kommunanalys.py:70. Sensitivity loaders in riksoversikt.py:97, kommunanalys.py:78, kallor.py:29 (return None if file missing or unreadable, silently). kallor.py:43 _modal_agreement(year).
- All cast df["year"] to int.

REQUIREMENTS
1. New app/data.py with:
   load_kri_data() -> pd.DataFrame  (@st.cache_data(show_spinner="Laddar data..."); same missing-file st.error text and st.stop as main.py today)
   load_sensitivity() -> pd.DataFrame | None  (@st.cache_data(show_spinner=False); same silent None behaviour)
   modal_agreement(year:int) -> int | None  (logic moved from kallor.py)
   year_slice(df, year) helper (copy) and kommun_history(df, code) helper.
   cached_pdf(year:int) -> bytes  (@st.cache_data(show_spinner=False), calls src.report_gen.generate_report(kri_df=load_kri_data(), report_year=year)).
2. Replace all page-local loaders with imports. Keep st.session_state["kri_df"] being set (some code reads it).
3. Do not change any computed values.

TESTING: smoke tests; pytest; add tests/test_data_module.py (marker integration) checking shape (4350, 21), int year dtype, sensitivity columns present or None.
DONE: commit "ux(T03): shared data access module".
```

---

### Prompt T04: App shell with st.navigation

```
TASK T04 (P0, HIGH RISK): Replace the five duplicated sidebars with a single st.navigation router.

CONTEXT
- Today: app/main.py = entry + landing + sidebar; each of app/pages/*.py re-renders brand, page_link list, year pills (keys main_year_pills/rv_year_pills/rd_year_pills/ka_year_pills), and (main, riksoversikt) a risk legend + risk pills. main.py ignores session_state for its pills, so visiting Startsida resets selected_year and selected_risks (bug U2).
- Streamlit 1.67: st.navigation(pages|{section: pages}, position="sidebar"|"hidden"|"top"), st.Page(path, title=, url_path=, default=, icon=), st.page_link accepts Page objects.
- URL paths today: "/" (main), "/riksoversikt", "/riskdekomposition", "/kommunanalys", "/kallor". These MUST stay identical.
- Approved review items: R4 (risk filter leaves the sidebar), R5 (order/sections/labels), R7 (footer wording: use the text the product owner approved; if none was given use "Källa: SCB, Kolada · Data 2010 - 2024"), R11.

REQUIREMENTS
1. Move the landing content (main.py lines ~163-316 incl. its imports) unchanged into new file app/pages/startsida.py. It reads year from st.session_state["selected_year"] and kri_df from app.data.load_kri_data().
2. New app/ui/shell.py:
   render_sidebar(pages: dict) -> int: brand block (same HTML/classes), section labels ÖVERSIKT / KOMMUN / METOD with st.sidebar.page_link(Page) entries in order Startsida, Riksöversikt | Kommunanalys, Riskdekomposition | Källor och metod; "Analysår" label + ONE st.sidebar.pills(key="global_year", default=st.session_state.get("selected_year", max_year)); writes st.session_state["selected_year"]; footer.
   render_page_header(eyebrow, title, subtitle, meta_value, meta_label="Analysår") (move from theme.py, keep theme.render_page_header as a re-export).
   render_footer() for the main column.
3. app/main.py becomes the router:
   apply_streamlit_theme(); kri_df = load_kri_data(); st.session_state["kri_df"] = kri_df
   define st.Page objects: startsida (default=True, title "Startsida", url_path omitted/""), riksoversikt (url_path="riksoversikt"), kommunanalys ("kommunanalys"), riskdekomposition ("riskdekomposition"), kallor ("kallor", title "Källor och metod").
   pg = st.navigation([...], position="hidden"); render_sidebar(...); pg.run()
4. In every page file delete the sidebar block, the per-page year pills, and per-page apply_streamlit_theme() calls (router does it once; keep the function idempotent anyway). Pages read selected_year from session_state.
5. Risk filter: delete from sidebar. In riksoversikt.py add (temporarily, T06 styles it) st.pills("Riskklass", ["Hög","Medel","Låg"], selection_mode="multi", key="rv_risk_filter", default=st.session_state.get("selected_risks") or None) at top of page; write selected_risks to session_state. Keep selected_risk alias in session_state for backward compatibility.
6. Replace all page-local footer HTML with render_footer().
7. Update tests/test_app_smoke.py PAGES constant to the new st.Page paths and add a test: set year 2015 on Riksöversikt, switch to Startsida, then Kommunanalys: selected_year must still be 2015 (U2 regression test).
8. Check the sidebar collapse/expand control still works with hidden header CSS in a real browser; if the test-id changed in 1.67, update the selector and comment it as version-sensitive.

MUST REMAIN INTACT: every page reachable from the sidebar and by direct URL (/riksoversikt etc.); Startsida content; About menu; data-missing error; risk filter semantics on Riksöversikt (empty = all).

TESTING: smoke tests incl. persistence test; pytest; verify_swedish_ui; manual: click every nav link, refresh on each URL, change year on each page, collapse/expand sidebar, check narrow width (390 px) sidebar overlay.

ACCEPTANCE: zero duplicated sidebar code in app/pages; year persists across all pages; URLs unchanged.
DONE: commit "ux(T04): st.navigation router, single sidebar, shared header/footer".
```

---

### Prompt T05: KPI component and delta semantics

```
TASK T05 (P0): Replace HTML KPI cards with an accessible st.metric-based component and fix delta semantics.

CONTEXT
- theme.render_kpi_card (HTML; tooltip only as title attribute). Used on riksoversikt.py (4 cards, explanations in _KPI_TIP_* constants) and kommunanalys.py (6 cards via _delta_info).
- BUG U1 (approved R1): kommunanalys._delta_info returns direction "down" when a higher-is-worse value increases, and CSS paints delta-down green, so a worsening KRI shows green ▼.
- st.metric(label, value, delta, delta_color "normal"|"inverse"|"off", help=, border=True, delta_arrow "auto"|"up"|"down"|"off", delta_description=, chart_data=, chart_type="line").
- Rank: 1 = most vulnerable, so a HIGHER rank number is BETTER.

REQUIREMENTS
1. New app/ui/components.py with:
   kpi(label, value: str, *, delta: str|None, better_when: "higher"|"lower"|None, help: str|None, period_label: str|None, spark: list[float]|None) -> None
   - better_when="lower" -> delta_color="inverse"; "higher" -> "normal"; None or delta None -> delta_color="off".
   - delta must start with "+" or "-" (use app.formatting.fmt_signed etc.), so st.metric arrow = sign of change.
   - "Oförändrat" case: pass delta=None and put "Oförändrat mot {år}" in delta_description... if delta_description is not shown without delta, append it to help instead. Verify in browser.
   - spark -> chart_data with chart_type="line".
2. Riksöversikt: four kpi() calls. Labels: "Median KRI", "Högriskkommuner", "Medianskuld per capita", "Befolkningsförändring, 5 år". Values via app.formatting (high-risk value "73 av 290" using fmt_count_of). Remove " std" unit (approved R13; if rejected keep it). help = existing _KPI_TIP_* text, plus for high-risk: "Riskklasserna är relativa: en fjärdedel av kommunerna klassas som Hög risk varje år." better_when: KRI lower, high-risk lower, debt lower, population higher.
3. R3 (if approved): previous-year comparison frames use the SAME risk-class filter applied to the previous year's own risk_class; delta_description "mot {prev}, samma urval" when filter active, else "mot {prev}". If R3 rejected: hide deltas while a filter is active.
4. Kommunanalys: six kpi() calls in a 3×2 grid, spark = the kommun's 15-year series for that indicator. better_when: KRI lower, Rang higher, Skuld lower, Arbetslöshet lower, Försörjningskvot lower, Skattekraft higher. Delta units: KRI 2 dp, rang "+4 platser", skuld "+1 234 kr", arbetslöshet/skattekraft "+0,3 p.e.", försörjningskvot 3 dp.
5. Keep theme.render_kpi_card in place (unused) for rollback; T12 removes it.
6. Unit tests (tests/test_components.py) for the pure mapping function better_when -> delta_color and for delta string construction.

MUST REMAIN INTACT: same four + six indicators, same values, same YoY comparison year, explanations available (now via help icon).

TESTING: AppTest: at.metric list has 4 elements on Riksöversikt and 6 on Kommunanalys; for a kommun whose KRI increased year over year (find one in data in the test), metric delta string starts with "+". Manual: keyboard-tab to a metric help icon and open it.
DONE: commit "ux(T05): accessible KPI component, correct delta semantics".
```

---

### Prompt T06: Riksöversikt redesign

```
TASK T06 (P0): Implement the Riksöversikt layout from UX_UI_MODERNIZATION_PLAN.md §A6.2, including the map/filter correctness fix.

CONTEXT
- File app/pages/riksoversikt.py (after T04/T05). Map: app/components/sweden_choropleth.py (build_choropleth_map(kri_df, year) builds colormap from the frame it receives; render_choropleth(filtered_df, year, height=440)). Histogram builders in app/components/charts.py.
- BUG U3 (approved R2): filtered-out kommuner get _kri=0.0 (painted neutral) and the colormap is rebuilt from the filtered subset. Copy at riksoversikt.py ~403 claims the map always shows the whole year.
- BUG U16: build_distribution_histogram tooltip divides by hardcoded 290.
- Approved R12: national PDF export also on this page (use app.data.cached_pdf).

REQUIREMENTS
1. Header via shell.render_page_header(eyebrow="Översikt", title="Riksöversikt", subtitle unchanged, meta_value=str(year)).
2. Filter bar under header: st.container(border=True) with st.pills label "Riskklass" (visible label), options Hög/Medel/Låg, format_func adding a coloured dot via Material icon or "●"-prefixed text, key rv_risk_filter; caption "Visar {n} av 290 kommuner" or "Visar alla 290 kommuner" (n from data; "290" from len(year_df)).
3. KPI row from T05.
4. Map card: card_header("Geografisk fördelning", subtitle, help_md=<corrected text>). Change build_choropleth_map signature to build_choropleth_map(kri_df, year, include_codes: set[str] | None = None): colormap ALWAYS from the full year; features whose code is not in include_codes get fillColor COLORS["border"], fillOpacity 0.35, and tooltip Riskklass "Ej i urvalet" (other fields still shown). render_choropleth(year_df, year, include_codes=set(filtered codes) or None). Cache key must include the filter so the map refreshes. Update tests/test_map.py with a test: with include_codes of only Hög kommuner, the colormap index equals the unfiltered one and an excluded feature has the neutral fill.
   Corrected help text (Swedish): explain colours, breakpoints = årets 25:e och 75:e percentil (samma som riskklasserna), and "Kommuner utanför riskfiltret visas i ljusgrått."
5. Distribution card: segmented control kept; card_header with help popover containing the former expander text; histogram denominator = len(scores) (add param total: int to builder, default len(kri_scores)).
6. Rankings: two cards unchanged in data; one popover "Om rankning och osäkerhet" merging the two former expanders (only include the uncertainty part when sens_df is not None). Table numerals tabular, risk pills via shared risk_badge.
7. Export row: st.download_button "Ladda ner rapport (PDF)" with data=cached_pdf(year) wrapped in st.spinner("Genererar PDF-rapport...") the first time; on_click="ignore"; file name kri_rapport_{year}.pdf.
   If generating on every page view is too slow (>1 s on first visit), use a st.button that stores bytes in session_state then shows the download button, and keep it visible across reruns.
8. Empty state: if filtered_df is empty, st.info("Inga kommuner matchar filtret.") and skip KPI/table rendering.
9. Remove the four st.expander blocks (content now lives in popovers). No text may be lost: diff old vs new Swedish copy.

MUST REMAIN INTACT: all features F13-F19; uncertainty column hidden silently when the sensitivity file is missing (test by temporarily renaming the parquet in a test with monkeypatch on app.data.load_sensitivity).

TESTING: pytest incl. new map test; smoke; verify_swedish_ui; manual: each filter combination, hover map, toggle histogram, download PDF and open it.
DONE: commit "ux(T06): Riksöversikt redesign, map filter/scale fix, PDF export".
```

---

### Prompt T07: Kommunanalys redesign

```
TASK T07 (P0): Implement Kommunanalys per UX_UI_MODERNIZATION_PLAN.md §A6.3.

CONTEXT
- app/pages/kommunanalys.py after T04/T05: selectbox (persisted in session_state["selected_municipality"]), inline summary HTML, KPI grid (T05), sensitivity caption, trend, peer table (Styler + _highlight_extremes), history table, expander with CSV, PDF (two-step), data quality.
- CSV today: display_history.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"), file kri_{code}_{name with _}.csv, key ka_download_csv. These must not change.

REQUIREMENTS
1. Header: eyebrow "Kommun", title "Kommunanalys", subtitle unchanged, meta year.
2. Context row st.columns([1.2, 2, 1.2]): selectbox (label "Välj kommun", same key/options/persistence); app.ui.components.render_kommun_summary(sel_row, sens_row) (new shared component: risk badge with tinted bg + dark text, "KRI 1,07", "Rang 6 av 290" using fmt_count_of with N=len(year_df), "Osäkerhet 3 - 9" if available); actions column with the existing CSV st.download_button (same label/data/filename/key/help, add on_click="ignore") and the PDF control using app.data.cached_pdf(year) (labels "Ladda ner rapport (PDF)" / SWEDISH_LABELS["download_pdf"], help text unchanged).
3. Sensitivity sentence: same text inside st.container(border=True) with icon :material/verified: (robust) or :material/warning: (gränsfall).
4. KPI grid (T05) then the existing explanatory caption.
5. Trend card: title f"KRI-trend {min_year} - {max_year}" from data; build series with one pivot instead of the per-year loop; same values.
6. Peer table: format with app.formatting via Styler.format (Swedish decimals); keep _highlight_extremes; add column_config help for "Avstånd": "Euklidiskt avstånd mellan kommunernas fem z-poäng. Lägre värde = mer lik."; caption under table: "Rött = sämst värde i kolumnen, grönt = bäst." ; st.dataframe(..., alt="Tabell över de tio mest liknande kommunerna").
   Peer failure: st.warning("Kunde inte beräkna jämförbara kommuner.") and log the exception (do not show raw exception text).
7. History table: Swedish formats via Styler.format, keep highlights; alt text.
   IMPORTANT: the CSV must still be produced from the unformatted display_history DataFrame exactly as before.
8. Data quality: own st.expander("Datakvalitet") with unchanged content.
9. st.page_link to the Riskdekomposition page, label f"Visa riskdrivare för {kommun}".
10. Replace all raw hex and inline style HTML in this file with components/tokens.

MUST REMAIN INTACT: F20-F29 entirely; CSV bytes identical for a given kommun (add a test comparing to a golden CSV generated from the baseline tag for one kommun, e.g. 0484 Eskilstuna).

TESTING: smoke; CSV golden test; pytest; verify_swedish_ui; manual: switch kommun, check deltas, download CSV (open in Excel sv-SE), download PDF.
DONE: commit "ux(T07): Kommunanalys redesign, visible exports".
```

---

### Prompt T08: Riskdekomposition redesign

```
TASK T08 (P1): Implement Riskdekomposition per §A6.4.

CONTEXT
- app/pages/riskdekomposition.py: selectbox sorted by rank (key rd_muni_select, default index 0), inline KPI HTML card, build_horizontal_contribution_bar (palette by sorted position), build_radar, compare multiselect (DEFAULT_COMPARE_MUNICIPALITIES, max 5, info under 2), grouped bars, multi trend.
- Approved R6: initial selection = session_state["selected_municipality"] if present in options, else highest-risk kommun.

REQUIREMENTS
1. Header eyebrow "Kommun". Context row: selectbox options = names sorted by rank, format_func showing f"{rank} · {name}", value stored = name; on change write session_state["selected_municipality"]. Shared render_kommun_summary (from T07).
2. Contributions card (card_header "Riskbidrag per faktor", help popover explaining that bidragen summeras till KRI): change build_horizontal_contribution_bar to colour by sign (v>0.01 high_risk, v<-0.01 low_risk, else text_tertiary) and add right-side value labels formatted "+0,61" (JS formatter, decimal comma). Keep sorting. Caption "Bidragen summeras till KRI {fmt_decimal(kri)}".
3. Radar unchanged.
4. Comparison: grouped bars palette = INDICATOR_COLORS mapped by indicator name (not by index).
5. Trend: dynamic year range title; vectorised series building.
6. page_link "Visa kommunanalys för {kommun}".
7. Update tests/test_risk_scale.py or add tests for the contribution bar colours by sign.

MUST REMAIN INTACT: F30-F34; comparison defaults; max 5; info message; Rikssnitt series.
TESTING: smoke; pytest; verify_swedish_ui; manual: navigate Kommunanalys(kommun X) -> Riskdekomposition shows X; change to Y -> Kommunanalys shows Y.
DONE: commit "ux(T08): Riskdekomposition redesign, shared kommun selection".
```

---

### Prompt T09: Startsida redesign

```
TASK T09 (P1): Implement Startsida per §A6.1.

CONTEXT: app/pages/startsida.py (moved in T04). Helpers in app/styles/theme.py (render_landing_*), app/components/landing_visuals.py. Approved R8 ("73 av 290").

REQUIREMENTS
1. Hero: solid COLORS["primary"] background (remove gradient), reduce vertical padding ~30 %. Copy unchanged.
2. CTA row under hero: st.columns([1,1,3]) with st.page_link(riksoversikt Page, label="Öppna riksöversikten", icon=":material/map:") and st.page_link(kommunanalys Page, label="Analysera en kommun", icon=":material/search:"). Style the first as primary via a scoped CSS class or a native st.button+st.switch_page if page_link cannot be styled (keyboard-focusable either way).
3. Stat strip: high-risk value fmt_count_of(n, N); interval fmt_range_decimal; values tabular sans.
4. "Vad är KRI?" and "Indexet i överblick" side by side: st.columns([1.1, 1]).
5. Steps: unchanged content, no hover effect.
6. "Vad hittar du här?": three st.container(border=True) cards, each: icon + title + desc (existing render_landing_nav_card body without hover) + st.page_link(Page, label=f"Gå till {titel}").
7. Remove render_landing_credibility call (footer now carries sources); keep the helper until T12.

MUST REMAIN INTACT: all landing copy; year-aware stats; weights + flow SVG.
TESTING: smoke; verify_swedish_ui; manual at 1440/768/390 px; Tab through all links.
DONE: commit "ux(T09): Startsida with working entry points".
```

---

### Prompt T10: Chart system polish

```
TASK T10 (P1): Unify ECharts presentation.

CONTEXT: app/components/charts.py (6 builders, JS formatters wrapped with _js()), theme.get_echarts_base_options/get_axis_style/get_tooltip_style.

REQUIREMENTS
1. Base options: add "aria": {"enabled": True}; animationDuration 250; textStyle fontFamily sans stack.
2. Add one JS helper string _JS_FMT defining function f(v,nd) producing Swedish numbers (decimal comma, U+202F thousands, ASCII minus) and use it in every formatter instead of toFixed().replace().
3. Value axis labels: sans font, axisLabel formatter using _JS_FMT so ticks show "0,5" not "0.5".
4. build_line_trend: smooth False (approved R9); keep risk bands.
5. Replace hardcoded tooltip hex (#1A1A2E, #6B7280, #9CA3AF, #F3F4F6, #B94A48, #2E7D5B) with COLORS values.
6. Run a colour-vision-deficiency check on INDICATOR_COLORS (e.g. compute pairwise deltaE under deuteranopia simulation in a small script) and adjust any pair with deltaE < 10; record in log.
7. Update tests in tests/test_risk_scale.py if they assert on removed literals; add a test that every builder output contains aria.enabled.

MUST REMAIN INTACT: every chart's data, risk-zone logic (RiskScale), tooltips' information content.
TESTING: pytest; smoke; manual hover on each chart.
DONE: commit "ux(T10): chart system polish".
```

---

### Prompt T11: States, responsive and accessibility pass

```
TASK T11 (P1): Make every page robust in empty/error/loading states, at narrow widths, and against WCAG 2.1 AA.

REQUIREMENTS
1. States inventory: for each page list loading (spinners), empty (no rows, <2 compare selections, missing sensitivity file, missing GeoJSON), and error paths (PDF failure, peer failure, parquet missing). Each must show a Swedish st.info/st.warning/st.error with a next step; no raw exception text; log exceptions with logging.getLogger(__name__).exception.
2. Responsive: test 1440, 1024, 768, 390 px. Fix: horizontal page scroll (none allowed), tables scroll inside their container, map height 360 at < 768 px if feasible via CSS on the iframe container, KPI grids stack. Record findings in docs/ux-modernization-log.md.
3. Accessibility: exactly one h1 per page; all widgets have visible labels or adjacent visible text; focus visible on links, pills, buttons, popovers; colour never the only signal (badges have text, table legend present, deltas signed); st.dataframe alt texts; decorative SVGs aria-hidden; check contrast of any new colour combination.
4. Run scripts/verify_swedish_ui.py and fix any violation.

TESTING: smoke; pytest; manual keyboard-only walkthrough of all pages; Lighthouse accessibility (Chrome DevTools) score recorded per page if Chrome available.
DONE: commit "ux(T11): states, responsive and accessibility pass".
```

---

### Prompt T12: Regression QA, cleanup, documentation, final report

```
TASK T12 (P0): Verify everything, remove dead code, update docs, write the final report.

REQUIREMENTS
1. Execute the full checklist in UX_UI_MODERNIZATION_PLAN.md §B5 and the feature regression list (F01-F43). Mark each item pass/fail in docs/ux-modernization-log.md. Fix failures or record them as known issues.
2. Remove now-unused helpers (render_kpi_card, render_landing_credibility, unused CSS classes such as .card-tag, .kpi-*, .riskklass-*) ONLY after grep confirms no references in app/, src/, scripts/, tests/.
3. Grep app/ for raw hex colours; replace with COLORS tokens (allow only inside src/config.py and SVG generated from tokens).
4. Update docs/ux-ui-design-system.md to the new system (tokens, theme config, components, navigation, state keys, delta rule, formatting module) and README "Pages" table (labels/order).
5. Write docs/ux-modernization-report.md: completed changes per task, modified files (git diff --stat ux-baseline-f1f1d96..HEAD), preserved functionality table, tests performed with results, remaining issues, deferred items (T13-T19), known limitations (Streamlit-internal selectors still used, Folium map not keyboard-operable, etc.).
6. Final: pytest, smoke, verify_swedish_ui all green.
DONE: commit "ux(T12): QA, cleanup, docs and final report". Do not merge; leave for owner review.
```

---

### Prompts T13 - T16 (P2, only if time remains)

```
T13 (P2): On Riksöversikt add st.expander("Alla kommuner {år}") with st.dataframe of all kommuner for the year (columns: Rang, Kommun, Riskklass, KRI, Skuld per capita (kr), Arbetslöshet (%), Försörjningskvot, Befolkningstillväxt (%), Skattekraft (%), Osäkerhet when available), Swedish formatting via Styler, column_config help per indicator, pinned Kommun column, respects the risk filter, plus st.download_button "Ladda ner alla kommuner (CSV)" using the same CSV conventions as Kommunanalys (sep=";", decimal=",", utf-8-sig). Tests: row count equals filtered count; CSV parses back with pandas sep=";" decimal=",". No existing behaviour changes.

T14 (P2): On Källor och metod add a "Källa" LinkColumn to the sources table (SCB table pages for BalansKn, BefolkningNy, SkatteKraft; Kolada KPI N03937) and a link to docs/methodology.md on GitHub (https://github.com/Maibra23/Kommunal-Finansiell-Riskindikator/blob/master/docs/methodology.md). Verify every URL returns HTTP 200 before committing. All existing text unchanged.

T15 (P2): Move the remaining CSS string from apply_streamlit_theme() into app/styles/kri.css using {{token}} placeholders substituted from COLORS at load time (cached). No visual change: compare AppTest markdown output and manual screenshots before/after.

T16 (P2): Above the Riksöversikt ranking tables add a compact selectbox "Öppna kommun" (options = filtered kommuner by rank); on selection set session_state["selected_municipality"] and st.switch_page to Kommunanalys. Test with AppTest that the destination shows the chosen kommun.
```

## B5. Testing and regression checklist

### Automated (every task)

- [ ] `python -m pytest -q`: all prior tests pass + new tests
- [ ] `tests/test_app_smoke.py`: 5 pages, 0 exceptions, 0 errors
- [ ] `python scripts/verify_swedish_ui.py` → PASS
- [ ] App starts with no config warnings (`python -m streamlit run app/main.py`)

### Application-level

- [ ] Startup with data present; startup with `kri_results.parquet` renamed shows the Swedish error and stops cleanly
- [ ] Startup with `kri_sensitivity.parquet` renamed: no uncertainty column, no sensitivity sentence, no errors, Källor still renders
- [ ] Startup with `kommuner.geojson` renamed: map warning shown, rest of page works
- [ ] Navigation: every sidebar link; every landing CTA and card link; contextual links between kommun pages; direct URL load + browser refresh on `/`, `/riksoversikt`, `/kommunanalys`, `/riskdekomposition`, `/kallor`; browser back/forward
- [ ] Session state: year persists across all pages incl. Startsida; risk filter persists when leaving/returning to Riksöversikt; selected kommun shared both ways
- [ ] Calculations: for years 2010, 2017, 2024 spot-check KPI values against a pandas script (median KRI, high-risk count, median debt, mean population growth, deltas) and Kommunanalys KPIs for Filipstad, Eskilstuna, Nykvarn, Kiruna (values quoted in README)
- [ ] Charts: hover tooltips on histogram (both views), contribution bar, radar, grouped bars, both trend charts; values match tables
- [ ] Map: hover tooltip fields; pan; zoom buttons; legend; filter greys out non-selected kommuner; colours unchanged with/without filter
- [ ] Tables: top/bottom 15 match `rank`; peer table 10 rows; history table 15 rows; sorting by column header works in st.dataframe
- [ ] Exports: CSV byte-identical to baseline for a sample kommun, opens correctly in Excel (sv-SE); PDF downloads from Kommunanalys and Riksöversikt, opens, year correct; repeated PDF download is instant (cached)
- [ ] Error handling: forced exception in peer calculation shows Swedish warning, no traceback
- [ ] Responsive: 1440, 1024, 768, 390 px, with no horizontal page scroll, sidebar opens/closes, KPI grids stack, tables scroll internally
- [ ] Accessibility: keyboard-only walkthrough; focus visible; help popovers reachable; one h1 per page; contrast of all text tokens ≥ 4.5:1; no colour-only meaning
- [ ] Browsers: Chrome, Firefox, Edge (latest); Safari if available

### Feature-by-feature regression (from §A3)

| Feature | Check | Pass |
|---|---|---|
| F01 | data loads once; missing-file message | ☐ |
| F02 | 5 pages reachable, URLs unchanged | ☐ |
| F03 | year changes all year-dependent content on every page | ☐ |
| F04/F05 | filter Hög/Medel/Låg/combos/empty on Riksöversikt | ☐ |
| F06-F12 | all landing copy present; stats correct for selected year; links work | ☐ |
| F13 | 4 KPIs, values and deltas correct, help readable | ☐ |
| F14 | map tooltip 8 fields; filter behaviour per R2 | ☐ |
| F15/F16 | histogram zones match risk classes; raw toggle | ☐ |
| F17/F18 | top/bottom 15; uncertainty column & subtitle; silent fallback | ☐ |
| F19 | all former expander text present in popovers | ☐ |
| F20/F30 | kommun selection shared, searchable | ☐ |
| F21 | summary badge/KRI/rank/uncertainty | ☐ |
| F22 | 6 KPIs, correct delta colours (R1), sparklines | ☐ |
| F23 | sensitivity sentence robust/gränsfall | ☐ |
| F24/F34 | trends incl. Rikssnitt and risk bands | ☐ |
| F25/F26 | peer + history tables, highlights + legend, Swedish decimals | ☐ |
| F27 | CSV unchanged | ☐ |
| F28 | PDF on both pages, cached | ☐ |
| F29 | data quality flags/metrics/missing list | ☐ |
| F31-F33 | contributions (sign colours), radar, comparison (2 - 5, defaults, info) | ☐ |
| F35-F39 | all Källor sections and tables | ☐ |
| F40 | page title, icon, About menu | ☐ |
| F41-F43 | scripts untouched; tests green | ☐ |

## B6. Rollback strategy

1. **Original preserved:** `master` is untouched during the project. Tag `ux-baseline-f1f1d96` marks the baseline. All work happens on `ux/modernization`.
2. **Traceability:** one task per commit (or small commit series) with prefix `ux(Txx):`. `git log --oneline --grep "ux(T06)"` lists a task's commits, and `git diff ux-baseline-f1f1d96..HEAD -- <file>` shows cumulative change.
3. **Revert a single task:** `git revert <sha>` (in reverse order if a task has several commits). Tasks are ordered so later tasks depend on earlier ones (see B2 "Depends"). Reverting T04 requires reverting T05-T12 first, or reapplying T04 manually. T06-T11 are mutually independent except for shared components.
4. **Old helpers kept until T12** (`render_kpi_card`, landing credibility, etc.), so reverting a page task never breaks imports.
5. **Failed implementation recovery:** if a task leaves the app broken and the fix is not obvious within 30 minutes, `git reset --hard` to the previous task's commit on the branch (local only, never on master), record the failure in `docs/ux-modernization-log.md`, and re-plan the task.
6. **Deployment:** Streamlit Cloud keeps deploying `master`. Merge `ux/modernization` only after T12 sign-off, as a PR, so the whole modernization can be reverted with one revert of the merge commit if needed.
7. **Environment rollback:** the dependency pin (T00) is a two-line change in `requirements.txt` and is reverted with the T00 commit.

---

## Stage 4: Internal review of this plan

| Check | Result |
|---|---|
| Missing pages | All 5 views covered (Startsida, Riksöversikt, Kommunanalys, Riskdekomposition, Källor) plus the shell |
| Overlooked features | Cross-checked against every widget and render call in `app/`: 43 features inventoried; PDF, CSV, data quality, sensitivity layer and its silent fallback, raw-debt histogram, comparison defaults, About menu all accounted for |
| Unnecessary changes | Rejected: new libraries (AgGrid, Plotly, Lucide), dark mode, rebrand, tabs on Källor, replacing HTML top-15 tables. Kept radar and Folium map as is |
| Conflicting decisions | Gold restricted to non-text on light surfaces but kept on navy (contrast 6.8). Risk colours reserved for risk only, indicators get a separate palette. Mono font removed for numbers but kept for code |
| Technical compatibility | `st.navigation`, `st.Page`, `st.metric(border, chart_data, delta_arrow, delta_description)`, `st.pills`, `st.popover`, `st.badge`, `st.space`, `download_button(on_click="ignore")`, `dataframe(alt=)`, and every `[theme]`/`[theme.sidebar]` key used were verified to exist in the installed Streamlit 1.67.0. streamlit-echarts 0.7.0 rendered all charts in the headless smoke run. Unverified: exact visual result of some theme keys and whether `delta_description` shows without a delta, both flagged in the prompts |
| Risks to functionality | Highest: T04 (router). Mitigated by smoke tests from T00, URL preservation, persistence test, and keeping old helpers. Next: T06 map change, covered by a new map test. CSV golden test protects exports |
| Estimates | P0+P1 = 37 h against 40 h capacity. T04 is the most likely overrun, and the plan names what to defer in that case. P2/P3 explicitly excluded from the 5-day commitment |
| Scope reduction applied | CSS extraction, all-290 table, source links, jump-from-ranking, URL state, visual regression, dark mode moved to P2/P3 |

---

## Decisions needed from you before implementation

1. Approve, reject, or modify each **⚠ REVIEW** item R1-R13 (§A10).
2. **R7:** preferred sidebar/footer data-vintage wording (e.g. "Data 2010 - 2024 · Byggd 2026-10-21" or no date).
3. Confirm the 5-day scope = P0 + P1 (T00-T12), with P2 only if time remains.
4. Confirm work happens on a new branch `ux/modernization` from `master` @ `f1f1d96`.
