# TASKS: Kommunal Finansiell Riskindikator (KRI)
# 5 Day Execution Plan with Cursor IDE and Claude Code

---

## Tool Assignment Overview

| Tool | Strength | Used for |
|------|----------|----------|
| **Claude Code** | Fast scaffolding, file generation, refactoring, testing | Project structure, config files, data pipeline, API clients, computation logic |
| **Cursor IDE** | Interactive editing, debugging, UI iteration, visual control | Streamlit UI, chart design, styling, interactive debugging, fine tuning |

---

## DAY 1: Project Structure + Data Pipeline

### Task 1.1: Scaffold project structure
**Executor:** Claude Code
**What:** Create the full folder structure, requirements.txt, .gitignore, config.py, README.md
**Why:** A correct project structure from the start prevents reorganization later. All subsequent tasks reference these files.
**How:** Claude Code generates all files in one pass based on the PRD.

**Prompt for Claude Code:**
```
Context: Read the following files for the full project specification:
- docs/PRD.md
- docs/METHODOLOGY.md

Task: Scaffold the complete project structure for Kommunal Finansiell Riskindikator (KRI).
Create the following:

1. Full folder structure as defined in PRD section 3 (Technical Architecture)

2. requirements.txt with:
   - streamlit>=1.30.0
   - pandas>=2.0.0
   - numpy>=1.24.0
   - plotly>=5.18.0
   - requests>=2.31.0
   - httpx>=0.25.0
   - scipy>=1.11.0
   - scikit-learn>=1.3.0
   - reportlab>=4.0.0
   - openpyxl>=3.1.0

3. src/config.py containing:
   - SCB_API_BASE = "https://api.scb.se/OV0104/v1/doris/sv/ssd/"
   - KOLADA_API_BASE = "https://api.kolada.se/v2/"
   - All API paths for each variable (see METHODOLOGY.md section 2.1)
   - KRI weights: WEIGHTS = {"debt": 0.25, "unemployment": 0.25, "dependency_ratio": 0.20, "population_growth": 0.15, "tax_base": 0.15}
   - Time period: START_YEAR = 2010, END_YEAR = 2024
   - Risk colors and design constants from PRD section 5
   - SWEDISH_LABELS dictionary mapping all English variable names to Swedish display names (see PRD section 9)
   - Full list of all 290 municipality codes

4. .gitignore (Python, data caches, .env)

5. README.md with project description (Swedish user facing text, English technical text), installation instructions, usage

All code variable names, comments, and docstrings in English.
All user facing strings (stored in SWEDISH_LABELS) in Swedish.
```

---

### Task 1.2: Build SCB API client
**Executor:** Claude Code
**What:** Create src/data_fetcher.py with functions to fetch each variable from SCB's PxWeb API
**Why:** SCB's API requires POST requests with JSON query bodies. Each table has a unique structure that must be mapped correctly.
**How:** A class SCBFetcher with methods per variable, plus error handling and caching.

**Prompt for Claude Code:**
```
Context: Read the following files:
- docs/METHODOLOGY.md (section 2.1 for all API paths and variable details)
- src/config.py (API endpoints and configuration)

Task: Create src/data_fetcher.py with a complete SCB API client.

Requirements:
1. Class SCBFetcher with methods:
   - fetch_balance_sheet() -> DataFrame (Long term liabilities, all municipalities, 2010 to 2024)
   - fetch_population_by_age() -> DataFrame (Population by age group, all municipalities, 2005 to 2024)
   - fetch_tax_base() -> DataFrame (Tax base share of national avg, all municipalities, 2010 to 2024)
   - fetch_income_statement() -> DataFrame (Annual result, all municipalities, 2010 to 2024)
   - fetch_tax_rate() -> DataFrame (Municipal tax rate, all municipalities, 2010 to 2024)

2. SCB PxWeb API mechanics:
   - POST to the table API URL with a JSON body specifying which variables, regions, and years to fetch
   - Response comes in JSON stat format
   - Example query body structure:
     {"query": [{"code": "Region", "selection": {"filter": "vs:RegionKommun07", "values": []}},
                {"code": "Tid", "selection": {"filter": "item", "values": ["2010","2011",...,"2024"]}}],
      "response": {"format": "json"}}
   - Empty values array for Region = all municipalities

3. Built in caching: save fetched data as parquet in data/cache/ with timestamp
4. Retry logic: 3 attempts with exponential backoff on API errors
5. Logging: log every API call and any errors
6. Function fetch_all() that fetches all variables and returns a dict of DataFrames

All code in English (variable names, comments, docstrings).
```

---

### Task 1.3: Build unemployment data fetcher (Arbetsformedlingen / Kolada)
**Executor:** Claude Code
**What:** Add a method/class in data_fetcher.py for unemployment data
**Why:** Unemployment comes from Arbetsformedlingen, not SCB. Can alternatively be fetched via Kolada API which is simpler.
**How:** Try Kolada first (simpler API). If it fails, fall back to direct Arbetsformedlingen data.

**Prompt for Claude Code:**
```
Context: Read the following files:
- docs/METHODOLOGY.md (section 2.1, Variable 2: Unemployment)
- src/config.py
- src/data_fetcher.py (existing SCB client)

Task: Add unemployment data fetching to the data pipeline.

Strategy (in priority order):
1. Try Kolada API first:
   - Search KPI: GET http://api.kolada.se/v2/kpi?title=arbetslöshet
   - Find KPI with municipality_type "K" (municipalities only)
   - Fetch data: GET http://api.kolada.se/v2/data/kpi/<ID>/year/2010,2011,...,2024
   - Kolada returns data for all municipalities in one call

2. If Kolada does not have a suitable KPI:
   - Download CSV/Excel from Arbetsformedlingen statistics page
   - Parse into DataFrame with columns: municipality_code, year, unemployment_pct

3. Fallback: use SCB AKU (Labor Force Survey) at county level and disaggregate

Class KoladaFetcher with methods:
- search_kpi(title: str) -> list[dict]
- fetch_kpi_data(kpi_id: str, years: list[int]) -> DataFrame
- fetch_unemployment() -> DataFrame

Same caching and retry logic as SCBFetcher.
```

---

### Task 1.4: Data cleaning and validation
**Executor:** Claude Code
**What:** Create src/data_cleaner.py that takes raw DataFrames and produces clean, merged analysis data
**Why:** Raw API data has different formats, missing values, and needs transformation into computable variables.
**How:** Pipeline: cleaning -> derived variable computation -> merging -> validation

**Prompt for Claude Code:**
```
Context: Read the following files:
- docs/METHODOLOGY.md (sections 2, 3, and 6 for data spec, model, and missing data handling)
- src/config.py
- src/data_fetcher.py

Task: Create src/data_cleaner.py with a complete data cleaning pipeline.

Class DataCleaner with methods:

1. clean_balance_sheet(df) -> DataFrame
   - Extract only "Langfristiga skulder" from the balance sheet
   - Convert from tkr to kr
   - Compute per capita (divide by population)

2. compute_dependency_ratio(pop_df) -> DataFrame
   - Calculate: (population 0 to 19 + population 65+) / population 20 to 64
   - Return per municipality and year

3. compute_population_growth(pop_df) -> DataFrame
   - Calculate 5 year rolling growth: ((pop_t / pop_{t minus 5}) minus 1) * 100
   - NOTE: Requires data from 2005 to compute 2010 values

4. clean_tax_base(df) -> DataFrame
   - Extract "Andel av riksmedelvärdet, procent"
   - No further transformations needed

5. merge_all(debt, unemployment, dependency, population, tax_base) -> DataFrame
   - Merge all into a single DataFrame with columns:
     municipality_code, municipality_name, year, debt_per_capita, unemployment,
     dependency_ratio, population_growth, tax_base_relative
   - Handle missing data per METHODOLOGY section 6.2

6. validate(df) -> dict
   - Count missing values per variable and municipality
   - Flag municipalities with incomplete data
   - Return validation report as dict

7. Special case handling:
   - Gotland (code 0980): flag with warning about split municipal/regional accounting
   - Knivsta (code 0330): municipality formed in 2003, interpolate early years if needed
   - Municipalities with boundary changes: document in validation report

Output: A clean DataFrame saved as data/processed/kri_base_data.parquet
```

---

### Task 1.5: Run data pipeline and verify
**Executor:** Cursor IDE
**What:** Run the pipeline interactively, inspect output, fix any bugs
**Why:** API calls can fail, data may have unexpected formats. Interactive debugging is required.
**How:** Run in Cursor terminal, inspect DataFrames, adjust as needed.

**Prompt for Cursor:**
```
Context: Open and read:
- src/config.py
- src/data_fetcher.py
- src/data_cleaner.py
- docs/METHODOLOGY.md

Task: Create a test/runner script scripts/run_pipeline.py that:
1. Fetches all data via SCBFetcher and KoladaFetcher
2. Runs the DataCleaner pipeline
3. Prints summary statistics:
   - Number of municipalities per year
   - Missing values per variable
   - Min/max/mean per variable
   - List of municipalities with missing data (flagged ones)
4. Saves results to data/processed/kri_base_data.parquet

Run the script and fix any errors iteratively.
```

---

## DAY 2: Index Calculation + Classification

### Task 2.1: Build KRI computation module
**Executor:** Claude Code
**What:** Create src/index_builder.py that computes KRI scores for all municipalities and years
**Why:** Core logic of the entire project. Must be correct, testable, and documented.
**How:** Z score normalization, direction correction, weighted summation.

**Prompt for Claude Code:**
```
Context: Read the following files:
- docs/METHODOLOGY.md (section 3: Model Specification, complete formula and weight details)
- src/config.py (weights and configuration)
- data/processed/kri_base_data.parquet (input data)

Task: Create src/index_builder.py with KRI computation logic.

Class KRIBuilder with methods:

1. normalize(df, year) -> DataFrame
   - Compute z score for each variable cross sectionally (all municipalities within one year)
   - z = (x minus mean) / std
   - Handle missing values (exclude from mean/std computation)

2. correct_direction(df) -> DataFrame
   - Variables where high = high risk: debt_per_capita, unemployment, dependency_ratio (keep as is)
   - Variables where high = low risk: population_growth, tax_base_relative (multiply by minus 1)

3. compute_kri(df) -> DataFrame
   - KRI = sum(weight_k * z_score_k) for all 5 variables
   - Weights from config.py WEIGHTS dict
   - Return DataFrame with columns: municipality_code, municipality_name, year, kri_score,
     z_debt, z_unemployment, z_dependency, z_population, z_tax_base,
     contribution_debt, contribution_unemployment, contribution_dependency,
     contribution_population, contribution_tax_base
   - contribution_X = weight_X * z_X (each variable's contribution to total KRI)

4. classify(df) -> DataFrame
   - Add column 'risk_class': 'Låg', 'Medel', 'Hög' (Swedish labels!)
   - Quantile based per year: below 25th percentile = Låg, above 75th = Hög
   - Add column 'rank' (1 to 290, 1 = highest risk)

5. compute_all_years(base_df) -> DataFrame
   - Iterate over all years 2010 to 2024
   - Return complete KRI dataset

6. build() -> DataFrame
   - Orchestrate full flow: read data -> normalize -> correct -> compute -> classify
   - Save results as data/processed/kri_results.parquet
   - Return result DataFrame

Include basic validations:
- Verify weights sum to 1.0
- Verify z scores have mean near 0 and std near 1
- Log each step
```

---

### Task 2.2: Build cluster analysis
**Executor:** Claude Code
**What:** Create src/clustering.py with extended classification and peer group analysis
**Why:** Beyond quantile classification, peer groups are needed for municipality comparison in the deep dive page.
**How:** K means as alternative, plus Euclidean distance for peer finding.

**Prompt for Claude Code:**
```
Context: Read:
- docs/METHODOLOGY.md (section 3.4 Classification method)
- src/index_builder.py
- src/config.py

Task: Create src/clustering.py with cluster and peer group analysis.

Functions:

1. kmeans_classification(kri_df, k=3) -> DataFrame
   - Run k means with k=3 on KRI scores
   - Map clusters to risk labels based on centroid values
   - Return DataFrame with cluster labels

2. get_peer_municipalities(municipality_code, kri_df, n=10) -> DataFrame
   - Find the n most similar municipalities based on the 5 z score variables
   - Use Euclidean distance
   - Return list of peer municipalities and their distances

3. compute_risk_transitions(kri_df) -> DataFrame
   - Calculate how municipalities move between risk classes over time
   - Identify municipalities that deteriorated markedly (jumped from Low to High)
   - Identify municipalities that improved markedly

4. compute_distribution_stats(kri_df, year) -> dict
   - Compute distribution statistics for a given year
   - Mean, median, std, skewness, kurtosis
   - Percentiles: 10, 25, 50, 75, 90
```

---

### Task 2.3: Validate KRI results
**Executor:** Cursor IDE
**What:** Run validation tests, inspect results, sanity check against known municipalities
**Why:** Ensure the index produces reasonable results before building the UI.
**How:** Interactively in Cursor, create test script.

**Prompt for Cursor:**
```
Context: Open and read:
- src/index_builder.py
- src/clustering.py
- docs/METHODOLOGY.md (section 4: Evaluation and validation)

Task: Create tests/test_index.py with validation tests:

1. test_weights_sum(): Weights must sum to 1.0
2. test_zscore_properties(): z scores should have mean near 0, std near 1
3. test_known_municipalities():
   - Danderyd (0162) should have KRI below median (low risk)
   - Dorotea (2425) should have KRI above 75th percentile (high risk)
   - Stockholm (0180) should have KRI in medium to low risk
4. test_classification_distribution():
   - Approximately 25% in Low, 50% in Medium, 25% in High
5. test_temporal_stability():
   - Correlation between KRI year t and KRI year t+1 should be > 0.85

Run the tests and report results. Fix any issues in the computation logic.
```

---

## DAY 3: Streamlit Dashboard (Page 1 + Design System)

### Task 3.1: Design system and theme
**Executor:** Claude Code
**What:** Create app/styles/theme.py with all design constants and Streamlit configuration
**Why:** Consistent design requires a centralized design system. All pages reference the same theme.
**How:** Define colors, typography, chart templates as reusable functions.

**Prompt for Claude Code:**
```
Context: Read:
- docs/PRD.md (section 5: Design Specification, complete color palette and typography)
- docs/PRD.md (section 9: Language Rules, SWEDISH_LABELS)

Task: Create app/styles/theme.py with a complete design system.

Contents:

1. COLORS dict with all colors from PRD:
   - primary, secondary, accent, low_risk, medium_risk, high_risk
   - background, text_primary, text_secondary, grid_lines

2. Function apply_streamlit_theme() that sets:
   - st.set_page_config(page_title="KRI Dashboard", layout="wide", page_icon="📊")
   - Custom CSS via st.markdown() for:
     - Font: Source Sans Pro (imported via Google Fonts)
     - Background color: #F7F8FA
     - Heading colors: #1B2A4A
     - Metric cards with white background, subtle shadow, rounded corners
     - Sidebar styling in dark blue (#1B2A4A)
     - Tables with zebra striping
   - CRITICAL: All visible text in the CSS/HTML must be Swedish

3. Function get_plotly_template() -> dict
   - Return plotly template with:
     - White background
     - Gridlines in #E5E7EB
     - Font: Source Sans Pro
     - Color scale: [primary, secondary, accent] + risk colors
     - No gradients, no 3D

4. Function get_risk_color(risk_class: str) -> str
   - Accept Swedish risk class names ("Låg", "Medel", "Hög")
   - Return the appropriate hex color

5. KPI card component:
   - Function render_kpi_card(title, value, delta=None, prefix="", suffix="")
   - title parameter receives Swedish text
   - White background, thin border, large bold KPI number, small gray title
```

---

### Task 3.2: Streamlit main app and Page 1 (Riksoversikt)
**Executor:** Cursor IDE
**What:** Create app/main.py and app/pages/1_riksoversikt.py with national overview
**Why:** The first page is the most important impression. Must immediately show the project's ambition level.
**How:** Streamlit multipage app with wide layout.

**Prompt for Cursor:**
```
Context: Open and read:
- docs/PRD.md (sections 5 and 6 for design and page structure)
- app/styles/theme.py (design system)
- data/processed/kri_results.parquet (KRI data)
- docs/METHODOLOGY.md
- src/config.py (SWEDISH_LABELS)

Task: Build Streamlit app with Page 1: Riksoversikt.

CRITICAL: ALL text visible to the user must be in Swedish. Use SWEDISH_LABELS from config.py.

app/main.py:
- Apply theme
- Configure multipage navigation
- Load data with @st.cache_data
- Sidebar with: year selector (slider 2010 to 2024), risk class filter
- Sidebar labels in Swedish ("Välj år", "Filtrera riskklass")

app/pages/1_riksoversikt.py:

Layout (top to bottom):

ROW 1: Title
- "Kommunal Finansiell Riskindikator" as H1
- "Strukturell ekonomisk sårbarhet i Sveriges 290 kommuner" as subtitle
- Selected year displayed prominently

ROW 2: KPI cards (4 columns)
- "Genomsnittligt KRI" (Average KRI score, with delta vs previous year)
- "Högrisk kommuner" (Number of high risk municipalities)
- "Medianskuld per capita" (Median debt per capita in kr)
- "Befolkningsförändring" (National population change %)

ROW 3: Two columns
- Left (60%): Sweden map (choropleth) with municipalities colored by risk class
  - Use plotly choropleth_mapbox or GeoJSON of Swedish municipalities
  - If GeoJSON not available: create scatter_geo with municipality centroids
  - Colors: green (low), amber (medium), red (high)
  - All hover text in Swedish
- Right (40%): DISTRIBUTION CHART
  - Histogram of all 290 municipalities' KRI scores
  - X axis label: "KRI Poäng"
  - Y axis label: "Antal kommuner"
  - Background colors marking risk zones (green, yellow, red)
  - Vertical line at median with Swedish annotation

ROW 4: Two tables side by side
- Left: "Topp 15 högst risk" (rank, municipality, KRI score, risk class)
- Right: "Topp 15 lägst risk" (rank, municipality, KRI score, risk class)
- Table headers in Swedish

All plotly charts use the template from theme.py.
All text in Swedish, no exceptions.
```

---

### Task 3.3: Sweden map implementation
**Executor:** Claude Code
**What:** Create app/components/sweden_map.py with map visualization
**Why:** The map is the most visually impressive element. Requires GeoJSON data for Swedish municipalities.
**How:** Centroids or GeoJSON; render via streamlit-echarts using `build_sweden_geo_scatter` in `app/components/charts.py`.

**Prompt for Claude Code:**
```
Context: Read:
- docs/PRD.md (sections 5 and 6)
- app/styles/theme.py

Task: Create app/components/sweden_map.py with map functionality.

Function render_sweden_map(kri_df, year) wrapping st_echarts with options from build_sweden_geo_scatter:

1. GeoJSON source for Swedish municipalities:
   - Primary: download from SCB geodata or Lantmateriet open data
   - URL option: https://raw.githubusercontent.com/okfse/sweden-geojson/master/swedish_municipalities.geojson
   - Alternative: use a simplified polygon file
   - Save locally in data/geo/kommuner.geojson

2. Map municipality_code to GeoJSON features
   - SCB municipality codes are 4 digits (e.g., "0180" for Stockholm)
   - GeoJSON property names vary; match on municipality code

3. Create choropleth:
   - Color by risk class (green/amber/red) or KRI score (continuous blue to red)
   - Hover info in Swedish: municipality name, KRI score, rank, risk class

4. ECharts geo / scatter configuration:
   - Centered on Sweden (lat ~63, lon ~17)
   - Appropriate zoom level
   - Clean background (no base map or minimal)
   - Styling from get_echarts_base_options / theme

5. Fallback if GeoJSON does not work:
   - Scatter plot with municipality centroids (lat/lon)
   - Circle size = population, color = risk class
   - All labels in Swedish
```

---

## DAY 4: Dashboard Pages 2 + 3 + Interactivity

### Task 4.1: Page 2 Risk Decomposition
**Executor:** Cursor IDE
**What:** Build app/pages/2_riskdekomposition.py with risk driver analysis
**Why:** Shows deeper analytical competence. Controllers want to see WHAT drives the risk.
**How:** Stacked bar chart, radar chart, comparison panel.

**Prompt for Cursor:**
```
Context: Open and read:
- docs/PRD.md (section 6, Page 2)
- app/styles/theme.py
- data/processed/kri_results.parquet
- src/config.py (SWEDISH_LABELS)

Task: Build Page 2: Riskdekomposition.

ALL user facing text in Swedish.

Layout:

ROW 1: Title + dropdown
- "Riskdekomposition" as H1
- Dropdown to select municipality (label: "Välj kommun", default: highest KRI municipality)

ROW 2: Two columns
- Left: Horizontal bar chart
  - Shows the 5 risk components' contributions (contribution_debt, contribution_unemployment, etc.)
  - Color coded bars (one color per variable)
  - Swedish variable names as labels
  - Clearly shows which factor drives risk the most
  - Use st_echarts with build_horizontal_contribution_bar from app/components/charts.py

- Right: Radar chart (spider chart)
  - 5 axes, one per variable (Swedish names on axes)
  - Shows selected municipality vs national average ("Rikssnitt")
  - Use streamlit-echarts: build_radar from app/components/charts.py

ROW 3: Comparison
- Multiselect to pick 2 to 5 municipalities (label: "Jämför kommuner")
- Grouped bar chart comparing risk components side by side
- Swedish labels throughout
- Use st_echarts with build_grouped_bars_comparison from app/components/charts.py

ROW 4: Time trend
- Line chart showing KRI score evolution 2010 to 2024 for selected municipalities
- Color per municipality
- Risk zone background colors
- X axis: "År", Y axis: "KRI Poäng"
- Use st_echarts with build_line_trend from app/components/charts.py
```

---

### Task 4.2: Page 3 Municipality Deep Dive
**Executor:** Cursor IDE
**What:** Build app/pages/3_kommunanalys.py with detailed municipality analysis
**Why:** The functionality a controller would actually use daily.
**How:** Searchable dropdown, detail panel, peer comparison.

**Prompt for Cursor:**
```
Context: Open and read:
- docs/PRD.md (section 6, Page 3)
- app/styles/theme.py
- src/clustering.py (peer group functionality)
- data/processed/kri_results.parquet
- src/config.py (SWEDISH_LABELS)

Task: Build Page 3: Kommunanalys.

ALL user facing text in Swedish.

Layout:

ROW 1: Municipality selector
- Searchable dropdown (st.selectbox with all 290 municipalities, label: "Välj kommun")
- Display immediately: KRI score, Rank (# of 290), Risk class (with color)

ROW 2: KPI cards (6)
- "KRI Poäng"
- "Rang"
- "Skuld per capita"
- "Arbetslöshet"
- "Försörjningskvot"
- "Skattekraft (% av rikssnitt)"
- Each card with delta vs previous year

ROW 3: Trend line chart
- KRI score 2010 to 2024
- With reference line for national average (labeled "Rikssnitt")
- Risk zone background colors
- Clear marking of selected year
- Axis labels in Swedish
- Use streamlit-echarts: build_line_trend from app/components/charts.py

ROW 4: Peer comparison
- Table header: "10 mest liknande kommuner"
- Columns: Rang, Kommun, KRI, Skuld, Arbetslöshet, Försörjning, Befolkning, Skattekraft

ROW 5: Detailed data table
- All underlying indicators for selected municipality, all years
- Column headers in Swedish
- Downloadable as CSV (st.download_button, label: "Ladda ner data")

ROW 6: Data quality panel
- Expandable section (label: "Datakvalitet")
- Show whether municipality has complete data
- Show any flags (Gotland warning, interpolated values)
- All text in Swedish
```

---

### Task 4.3: Data quality validation in UI
**Executor:** Claude Code
**What:** Create src/validators.py and integrate validation into the dashboard
**Why:** Users must know which municipalities have incomplete data.
**How:** Validate all 290 municipalities, flag in UI.

**Prompt for Claude Code:**
```
Context: Read:
- docs/METHODOLOGY.md (section 6: Handling Incomplete Data)
- src/data_cleaner.py
- data/processed/kri_base_data.parquet

Task: Create src/validators.py with data quality validation.

Functions:

1. validate_completeness(df) -> DataFrame
   - Check every municipality for every variable and year
   - Return DataFrame with columns: municipality_code, variable, year, status
   - Status values: "OK", "Interpolerad", "Saknas", "Flaggad" (Swedish status labels)

2. get_municipality_flags(municipality_code) -> list[str]
   - Return list of flags in Swedish, e.g.:
     - "Gotland: Delad redovisning kommun/region (65%/35%)"
     - "Knivsta: Kommun bildad 2003, begränsad historik"
     - "Interpolerade värden för arbetslöshet 2010-2011"

3. get_data_quality_summary() -> dict
   - Count of municipalities with complete data
   - Count with interpolated data
   - Count with missing data
   - List of most problematic municipalities

4. Integration notes for Streamlit:
   - Add an expandable "Datakvalitet" section on each page
   - Show summary with green/yellow/red indicators
   - All displayed text in Swedish
   - No new chart library: future chart pages use streamlit-echarts with the same theme helpers as Page 1
```

---

## DAY 5: PDF Report + Polish + Publish

### Task 5.1: PDF report generation
**Executor:** Claude Code
**What:** Create src/report_gen.py that generates a 5 page PDF report
**Why:** A PDF report is a concrete deliverable that can be shared with employers.
**How:** Generate with reportlab based on KRI data.

**Prompt for Claude Code:**
```
Context: Read:
- docs/PRD.md (section 7: Deliverables)
- docs/METHODOLOGY.md (complete methodology description)
- data/processed/kri_results.parquet

Task: Create src/report_gen.py that generates a professional PDF report.

CRITICAL: All report content must be in Swedish. The report is a Swedish language document.

Report structure (5 pages):

PAGE 1: Cover page
- Title: "Kommunal Finansiell Riskindikator 2024"
- Subtitle: "Analys av strukturell ekonomisk sårbarhet i Sveriges 290 kommuner"
- Date
- Author

PAGE 2: Executive summary
- Swedish executive summary (5 to 8 sentences)
- Key findings: count of high/medium/low risk
- Top 5 most vulnerable municipalities
- Top 5 most robust municipalities

PAGE 3: Methodology
- Brief description of KRI model (in Swedish)
- Variable descriptions (in Swedish)
- Weight rationale
- Data sources

PAGE 4: Results
- Distribution chart (histogram)
- Top 20 highest risk table
- Trend chart (aggregated national average)

PAGE 5: Conclusions and limitations
- Main conclusions (Swedish)
- Policy implications (Swedish)
- Limitations (Swedish)
- Suggestions for further analysis

Use reportlab with professional layout:
- Margins: 2.5 cm
- Font: Helvetica
- Color scheme matching dashboard (PRD section 5)
- Footer with page number and "Källa: SCB, Arbetsförmedlingen"
```

---

### Task 5.2: UX polish and review
**Executor:** Cursor IDE
**What:** Review the entire dashboard, fix visual issues, improve UX
**Why:** Final quality control makes the difference between "student project" and "professional analysis."
**How:** Checklist driven review.

**Prompt for Cursor:**
```
Context: Open all files in app/ directory. Read docs/PRD.md section 5 for design spec and section 9 for language rules.

Task: UX polish. Run through the following checklist:

LANGUAGE CHECK (most critical):
- [ ] Zero English text visible anywhere in the UI
- [ ] All chart axis labels in Swedish
- [ ] All chart legends in Swedish
- [ ] All tooltips in Swedish
- [ ] All table headers in Swedish
- [ ] All sidebar labels in Swedish
- [ ] All button labels in Swedish
- [ ] All error messages in Swedish
- [ ] Footnotes about data sources in Swedish

VISUAL:
- [ ] All charts use consistent colors from theme
- [ ] KPI cards have correct formatting (thousand separators, decimals)
- [ ] Tables have zebra striping
- [ ] Hover tooltips work on all charts
- [ ] All ECharts charts use get_echarts_base_options() as base merge
- [ ] All ECharts tooltips use consistent styling from get_tooltip_style()
- [ ] All ECharts axes use consistent styling from get_axis_style()
- [ ] No ECharts default theme leakage (orange colors, default fonts)

FUNCTIONAL:
- [ ] Year selector works and updates all elements
- [ ] Municipality selector is searchable
- [ ] Download buttons work (CSV, PDF)
- [ ] Load times under 5 seconds
- [ ] No error messages during normal use

ACCESSIBILITY:
- [ ] Color combinations have sufficient contrast
- [ ] Charts readable even without color (patterns if needed)
```

---

### Task 5.3: GitHub publication
**Executor:** Claude Code
**What:** Prepare and publish GitHub repository
**Why:** The GitHub repo is a deliverable and demonstrates professional code management.
**How:** Create complete README, ensure .gitignore, initialize repo.

**Prompt for Claude Code:**
```
Context: Read:
- docs/PRD.md
- requirements.txt
- All files in src/ and app/

Task: Prepare GitHub publication.

1. Update README.md with:
   - Project description (Swedish for the user facing description, English for technical sections)
   - Screenshot placeholder
   - Installation: git clone, pip install, streamlit run
   - Data flow description
   - Technical architecture (brief)
   - License (MIT)
   - Contact

2. Create .env.example with any environment variables

3. Verify .gitignore:
   - data/cache/*
   - data/raw/*
   - *.parquet
   - __pycache__
   - .env
   - .streamlit/secrets.toml

4. Create setup script: scripts/setup.sh that installs dependencies and fetches data

5. Git init, initial commit
```

---

## Time Budget Per Day

| Day | Focus | Estimated hours |
|-----|-------|----------------|
| 1 | Project structure + Data pipeline | 6 to 8 hours |
| 2 | Index calculation + Validation | 4 to 6 hours |
| 3 | Dashboard Page 1 + Design system | 6 to 8 hours |
| 4 | Dashboard Pages 2 + 3 | 6 to 8 hours |
| 5 | PDF + Polish + Publish | 4 to 6 hours |

---

## Priority Order If Running Behind Schedule

If Day 4 or 5 takes longer than planned, prioritize in this order:

1. **MUST HAVE:** Page 1 (Riksoversikt) with working KRI, distribution chart, map
2. **SHOULD HAVE:** Page 3 (Kommunanalys) with trend data
3. **NICE TO HAVE:** Page 2 (Riskdekomposition) with radar/bar charts
4. **EXTRA:** PDF report
5. **EXTRA:** GitHub publication with complete README

---

## Context Files That Must Be Available

All prompts above reference these files. Ensure they exist and are current:

| File | Purpose | Created in |
|------|---------|-----------|
| docs/PRD.md | Project definition, design, architecture | Task 1.1 |
| docs/METHODOLOGY.md | Methodology, data, model, limitations | Separate document |
| docs/TASKS.md | This document | Separate document |
| src/config.py | Configuration, API endpoints, weights, SWEDISH_LABELS | Task 1.1 |
| src/data_fetcher.py | API clients | Tasks 1.2, 1.3 |
| src/data_cleaner.py | Data cleaning | Task 1.4 |
| src/index_builder.py | KRI computation | Task 2.1 |
| src/clustering.py | Classification | Task 2.2 |
| src/validators.py | Data quality | Task 4.3 |
| src/report_gen.py | PDF report | Task 5.1 |
| app/styles/theme.py | Design system | Task 3.1 |
| app/main.py | Streamlit app | Task 3.2 |
| data/processed/kri_base_data.parquet | Cleaned base data | Task 1.4 |
| data/processed/kri_results.parquet | KRI results | Task 2.1 |