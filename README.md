# Kommunal Finansiell Riskindikator (KRI)

**Datadriven analys av strukturell ekonomisk sårbarhet i Sveriges 290 kommuner**

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

- **SCB Statistikdatabasen** - Balansräkning, befolkning, skattekraft
- **Arbetsförmedlingen / Kolada** - Arbetslöshet
- **Analysperiod:** 2010-2024 (15 år)

---

## Installation

### Requirements

- Python 3.11 or higher
- pip (Python package manager)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/your-username/kommun-risk-dashboard.git
cd kommun-risk-dashboard
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Fetch data and build the index:
```bash
python scripts/run_pipeline.py
```

5. Run the dashboard:
```bash
streamlit run app/main.py
```

---

## Project Structure

```
kommun-risk-dashboard/
├── data/
│   ├── raw/           # Raw API data
│   ├── processed/     # Cleaned and computed data
│   ├── cache/         # API response cache
│   └── geo/           # GeoJSON files for map
├── src/
│   ├── config.py      # Configuration, API paths, labels
│   ├── data_fetcher.py    # API clients (SCB, Kolada)
│   ├── data_cleaner.py    # Data cleaning pipeline
│   ├── index_builder.py   # KRI computation
│   ├── clustering.py      # Classification and peer groups
│   ├── validators.py      # Data quality validation
│   └── report_gen.py      # PDF report generation
├── app/
│   ├── main.py        # Streamlit app entry point
│   ├── pages/         # Dashboard pages
│   ├── components/    # Reusable UI components
│   └── styles/        # Theme and design system
├── docs/
│   ├── PRD.md         # Product Requirements
│   ├── METHODOLOGY.md # Methodology documentation
│   └── TASKS.md       # Development tasks
├── tests/             # Test files
├── scripts/           # Utility scripts
├── report/            # Generated PDF reports
├── requirements.txt
└── README.md
```

---

## Technical Details

### Data Pipeline

1. **Fetch** - API clients retrieve data from SCB and Kolada
2. **Clean** - Transform raw data, compute derived variables
3. **Build** - Z-score normalization, weighted index computation
4. **Classify** - Quantile-based risk classification (Low/Medium/High)
5. **Validate** - Data quality checks and flagging

### KRI Formula

```
KRI(i,t) = Σ(wk × zk(i,t))
```

Where:
- `i` = municipality
- `t` = year
- `wk` = weight for variable k
- `zk` = z-score normalized value for variable k

Z-scores are computed cross-sectionally (all municipalities within one year).

### Classification

- **Låg risk (Low)**: KRI below 25th percentile
- **Medel risk (Medium)**: KRI between 25th and 75th percentile
- **Hög risk (High)**: KRI above 75th percentile

---

## Dashboard Pages

1. **Riksöversikt** - National overview with map, KPIs, and distribution
2. **Riskdekomposition** - Risk driver analysis per municipality
3. **Kommunanalys** - Deep dive with trend data and peer comparison

---

## API Documentation

### SCB PxWeb API

The project uses SCB's PxWeb API with POST requests containing JSON query bodies.

Example query:
```json
{
  "query": [
    {"code": "Region", "selection": {"filter": "vs:RegionKommun07", "values": []}},
    {"code": "Tid", "selection": {"filter": "item", "values": ["2010","2024"]}}
  ],
  "response": {"format": "json"}
}
```

### Kolada API

REST API for municipal key performance indicators:
- KPI search: `GET /v2/kpi?title=arbetslöshet`
- Data fetch: `GET /v2/data/kpi/{id}/year/{years}`

---

## License

MIT License

---

## Contact

For questions about methodology or implementation, see the documentation in `docs/`.

---

*Källa: SCB, Arbetsförmedlingen*
