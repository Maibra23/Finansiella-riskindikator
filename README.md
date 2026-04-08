# Kommunal Finansiell Riskindikator (KRI)

**Datadriven analys av strukturell ekonomisk sårbarhet i Sveriges 290 kommuner**

> An interactive Streamlit dashboard that ranks all 290 Swedish municipalities on a composite financial vulnerability index, covering 2010–2024.

---

## Om projektet

Kommunal Finansiell Riskindikator (KRI) är en interaktiv dashboard som rankar Sveriges 290 kommuner utifrån ett sammansatt finansiellt sårbarhetsindex. Indexet kombinerar fem nyckelvariabler för att identifiera kommuner med strukturell ekonomisk risk.

### Variabler i indexet

| Variabel | Vikt | Riktning |
|----------|------|----------|
| Skuld per capita | 25% | Hög = hög risk |
| Arbetslöshet | 25% | Hög = hög risk |
| Försörjningskvot | 20% | Hög = hög risk |
| Befolkningstillväxt (5 år) | 15% | Negativ = hög risk |
| Skattekraft (% av rikssnitt) | 15% | Låg = hög risk |

### Datakällor

- **SCB Statistikdatabasen** — Balansräkning, befolkning, skattekraft (PxWeb API)
- **Arbetsförmedlingen / Kolada** — Arbetslöshet (KPI N03937)
- **Analysperiod:** 2010–2024 (15 år, 4 350 observationer, 0 saknade värden)

---

## Snabbstart (Quick start)

```bash
# Clone
git clone https://github.com/your-username/kommun-risk-dashboard.git
cd kommun-risk-dashboard

# One-command setup (creates venv, installs deps, fetches data)
bash scripts/setup.sh

# Run the dashboard
streamlit run app/main.py
```

---

## Installation (manual)

### Requirements

- Python 3.11 or higher
- pip (Python package manager)

### Steps

1. Clone the repository:
```bash
git clone https://github.com/your-username/kommun-risk-dashboard.git
cd kommun-risk-dashboard
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate       # Linux / macOS
venv\Scripts\activate          # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Fetch data and build the KRI index:
```bash
python scripts/run_pipeline.py
```
This fetches all data, cleans it, and builds the KRI index in one step.
The pipeline saves both `kri_base_data.parquet` and `kri_results.parquet`.

5. Run the dashboard:
```bash
streamlit run app/main.py
```

---

## Project Structure

```
kommun-risk-dashboard/
├── data/
│   ├── raw/                   # Raw API responses (JSON)
│   ├── processed/             # kri_base_data.parquet, kri_results.parquet
│   ├── cache/                 # API response cache (auto-managed)
│   └── geo/                   # kommuner.geojson, centroids CSV
├── src/
│   ├── config.py              # API endpoints, weights, SWEDISH_LABELS, municipality list
│   ├── data_fetcher.py        # SCBFetcher + KoladaFetcher API clients
│   ├── data_cleaner.py        # Data cleaning and derived variable computation
│   ├── index_builder.py       # KRIBuilder: z-scores, weighting, classification
│   ├── clustering.py          # k-means, peer groups, risk transitions
│   ├── validators.py          # Data quality checks and municipality flags
│   └── report_gen.py          # 5-page PDF report generator (reportlab)
├── app/
│   ├── main.py                # Streamlit entry point + landing page
│   ├── pages/
│   │   ├── riksoversikt.py        # National overview: map, KPIs, distribution
│   │   ├── riskdekomposition.py   # Risk driver analysis per municipality
│   │   ├── kommunanalys.py        # Municipality deep dive + peer comparison
│   │   └── kallor.py              # Data sources and methodology
│   ├── components/
│   │   ├── charts.py              # Apache ECharts option builders
│   │   ├── sweden_choropleth.py   # Folium choropleth map
│   │   └── landing_visuals.py     # Landing page HTML/SVG fragments
│   └── styles/
│       └── theme.py           # Design system, CSS injection, ECharts helpers
├── docs/
│   ├── Prd.md                 # Product Requirements Document
│   ├── METHODOLOGY.md         # Full methodology documentation
│   └── tasks.md               # 5-day development task plan
├── tests/
│   └── test_index.py          # 28 unit tests (weights, z-scores, known municipalities)
├── scripts/
│   ├── run_pipeline.py        # Full ETL: fetch → clean → build → save
│   ├── verify_pipeline.py     # Pipeline output validation
│   ├── verify_swedish_ui.py   # Swedish language compliance check
│   ├── full_data_audit.py     # Comprehensive data quality audit
│   └── setup.sh               # One-command project setup script
├── report/                    # Generated PDF reports (gitignored)
├── .env.example               # Environment variable template
├── requirements.txt
└── README.md
```

---

## Technical Details

### Data Pipeline

```
SCB PxWeb API ──┐
                ├──► DataCleaner ──► KRIBuilder ──► kri_results.parquet
Kolada API ─────┘
```

1. **Fetch** — `SCBFetcher` and `KoladaFetcher` retrieve data via REST APIs with caching and retry logic
2. **Clean** — `DataCleaner` handles unit conversion, derived variables (dependency ratio, 5-year pop. growth), and merging
3. **Normalize** — Cross-sectional z-scores per year across all 290 municipalities
4. **Correct** — Direction correction so that higher z-score always means higher risk
5. **Compute** — Weighted sum → KRI score per municipality-year
6. **Classify** — Quantile-based: bottom 25% = Låg, top 25% = Hög, middle = Medel
7. **Validate** — `DataValidator` flags special municipalities (Gotland, Knivsta, Heby)

### KRI Formula

```
KRI(i,t) = Σ wk × zk(i,t)
```

| Symbol | Meaning |
|--------|---------|
| `i` | Municipality |
| `t` | Year |
| `wk` | Variable weight (sums to 1.0) |
| `zk` | Direction-corrected cross-sectional z-score |

### Classification

| Risk class | Threshold | Color |
|------------|-----------|-------|
| **Låg** | KRI < 25th percentile | 🟢 `#2E7D5B` |
| **Medel** | 25th–75th percentile | 🟡 `#D4A03C` |
| **Hög** | KRI > 75th percentile | 🔴 `#B94A48` |

### Visualization

All charts use **Apache ECharts** via `streamlit-echarts`. Shared styling helpers in `app/styles/theme.py`:

- `get_echarts_base_options()` — grid, animation, background
- `get_tooltip_style()` — white background tooltip with rounded corners
- `get_axis_style(type)` — consistent axis styling

Chart builders in `app/components/charts.py`:

| Function | Chart type | Used on |
|----------|-----------|---------|
| `build_distribution_histogram()` | Histogram | Riksöversikt |
| `build_sweden_geo_scatter()` | Scatter map | Riksöversikt |
| `build_horizontal_contribution_bar()` | Horiz. bars | Riskdekomposition |
| `build_radar()` | Spider/radar | Riskdekomposition |
| `build_grouped_bars_comparison()` | Grouped bars | Riskdekomposition |
| `build_line_trend()` | Line chart | Riskdekomposition, Kommunanalys |

---

## Dashboard Pages

| Page | Description |
|------|-------------|
| **Riksöversikt** | National overview: 4 KPI cards, Sweden choropleth map (risk-coloured), KRI distribution histogram, top/bottom 15 risk tables |
| **Riskdekomposition** | Per-municipality risk driver analysis: contribution bars, radar vs. national avg, multi-municipality grouped bar comparison, KRI trend line |
| **Kommunanalys** | Municipality deep dive: 6 KPI cards with deltas, KRI trend vs. rikssnitt, 10 peer municipalities table, full historical data table + CSV download, data quality panel |
| **Källor** | Data sources table, API documentation, licence information |

All UI text is in Swedish. Code identifiers and comments are in English.

---

## Running Tests

```bash
pytest tests/ -v
# 28 tests covering: weights, z-score properties, known municipalities,
# classification distribution, temporal stability, clustering, peer analysis
```

---

## API Documentation

### SCB PxWeb API

POST requests to table URLs with JSON query bodies:

```json
{
  "query": [
    {"code": "Region", "selection": {"filter": "vs:RegionKommun07", "values": []}},
    {"code": "Tid",    "selection": {"filter": "item", "values": ["2010","2024"]}}
  ],
  "response": {"format": "json"}
}
```

Tables used: `BalansKn` (debt), `BefolkningNy` (population), `SkatteKraft` (tax base), `ResultKn` (income statement)

### Kolada API

REST API for municipal KPIs:
```
GET /v2/kpi?title=arbetslöshet          # search KPIs
GET /v2/data/kpi/N03937/year/2010,...   # fetch unemployment data
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Contact

For questions about methodology or implementation, see `docs/METHODOLOGY.md`.

---

*Källa: SCB, Arbetsförmedlingen/Kolada · KRI v1.0 · 2010–2024*
