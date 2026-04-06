# Product Requirements Document (PRD)
# Kommunal Finansiell Riskindikator (KRI) Dashboard

## 1. Project Overview

**Project name:** Kommunal Finansiell Riskindikator for Sweden's Municipalities
**Subtitle (displayed in Swedish in UI):** Datadriven analys av strukturell ekonomisk sårbarhet i svenska kommuner
**Timeline:** 5 working days (Day 1 through Day 5)
**Analysis period:** 2010 to 2024 (15 years)
**Number of municipalities:** 290 Swedish municipalities
**Dashboard language:** Swedish only. Every piece of text a user sees must be in Swedish. Zero English in the UI.
**Code language:** English (variable names, function names, comments, docstrings, file names)
**Platform:** Streamlit (web application)
**Tools:** Cursor IDE + Claude Code

---

## 2. Goals and Purpose

### Primary goal
Build an interactive dashboard that ranks all 290 Swedish municipalities by a composite financial vulnerability index (KRI). The dashboard must signal controller competence and municipal economics literacy to Swedish employers.

### Secondary goals
- Show trend analysis for each municipality over 15 years
- Identify and visualize risk clusters (low, medium, high risk)
- Generate a 5 page PDF report with executive summary (report content in Swedish)
- Publish a reproducible GitHub repository

### Target audience
- Controllers and economists in the public sector
- Bank analysts
- Public administration consultants
- Policy and statistics analysts

---

## 3. Technical Architecture

### Tech Stack
| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Dashboard | Streamlit |
| Data processing | pandas, numpy |
| Visualization | plotly |
| API calls | requests, httpx |
| Statistics | scipy.stats, scikit-learn |
| PDF report | reportlab or weasyprint |
| Version control | Git + GitHub |

### Folder Structure
```
kommun-risk-dashboard/
├── .cursor/
│   └── rules
├── data/
│   ├── raw/
│   ├── processed/
│   └── cache/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── data_fetcher.py
│   ├── data_cleaner.py
│   ├── index_builder.py
│   ├── clustering.py
│   ├── validators.py
│   └── report_gen.py
├── app/
│   ├── main.py
│   ├── pages/
│   │   ├── 1_riksoversikt.py
│   │   ├── 2_riskdekomposition.py
│   │   └── 3_kommunanalys.py
│   ├── components/
│   │   ├── kpi_cards.py
│   │   ├── sweden_map.py
│   │   ├── charts.py
│   │   └── filters.py
│   └── styles/
│       └── theme.py
├── docs/
│   ├── METHODOLOGY.md
│   ├── TASKS.md
│   └── PRD.md
├── tests/
│   └── test_index.py
├── report/
│   └── kri_rapport.pdf
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 4. Data Variables

### Core variables (5, mandatory)
| # | Variable | Weight | Direction | Source |
|---|----------|--------|-----------|-------|
| 1 | Debt per capita (long term liabilities) | 0.25 | High = high risk | SCB BalansKnN |
| 2 | Unemployment (registered) | 0.25 | High = high risk | Arbetsformedlingen / Kolada |
| 3 | Dependency ratio | 0.20 | High = high risk | SCB Population by age |
| 4 | Population growth (5yr rolling) | 0.15 | Negative = high risk | SCB Population |
| 5 | Tax base strength (% of national avg) | 0.15 | Low = high risk | SCB SkatteKraft |

### Supplementary variables (3, for deep analysis)
| # | Variable | Source |
|---|----------|-------|
| 6 | Annual financial result (kr/inhabitant) | SCB ResultKn |
| 7 | Municipal tax rate (%) | SCB Komskatter |
| 8 | Equity ratio (calculated) | SCB BalansKnN |

---

## 5. Design Specification

### Overall design principle
**Nordic Banking Analytics.** Think Riksbanken, Handelsbanken Private Banking, or SCB publications. Clean, structured, professional. Not academic, not startup.

### Color Palette
| Usage | Hex |
|-------|-----|
| Primary (dark blue) | #1B2A4A |
| Secondary (steel blue) | #4A6FA5 |
| Accent (gold) | #C4A35A |
| Low risk | #2E7D5B |
| Medium risk | #D4A03C |
| High risk | #B94A48 |
| Background | #F7F8FA |
| Text primary | #1A1A2E |
| Text secondary | #6B7280 |
| Grid lines | #E5E7EB |

### Typography
| Element | Font | Size |
|---------|------|------|
| H1 | Source Sans Pro Bold | 28px |
| H2 | Source Sans Pro SemiBold | 22px |
| Body | Source Sans Pro Regular | 16px |
| KPI numbers | Source Sans Pro Bold | 36px |
| Footnotes | Source Sans Pro Light | 12px |

### Chart design rules
- White background (#FFFFFF) with subtle gridlines (#E5E7EB)
- Axis labels in dark gray (#6B7280)
- Risk clusters use the defined risk colors (green, amber, red)
- Distribution charts show all 290 municipalities with risk zone background coloring
- No gradients, no 3D, no shadows on charts
- Hover tooltips with municipality name and values
- **CRITICAL: All chart text (axis titles, legends, tooltips, annotations) must be Swedish**

---

## 6. Page Structure

### Page 1: Riksoversikt (National Overview)
**UI title:** "Riksöversikt"

Contents:
- KPI cards (top row): Average KRI score, Number of high risk municipalities, Median debt per capita, National population change
- Sweden choropleth map colored by risk class
- Top 15 highest risk table
- Bottom 15 lowest risk table
- **Distribution histogram:** All 290 municipalities' KRI scores with colored risk zones

### Page 2: Riskdekomposition (Risk Decomposition)
**UI title:** "Riskdekomposition"

Contents:
- Horizontal bar chart showing each variable's contribution to total KRI for a selected municipality
- Radar chart comparing selected municipality vs national average
- Multi municipality comparison (grouped bars)
- Time trend of KRI for selected municipalities

### Page 3: Kommunanalys (Municipality Deep Dive)
**UI title:** "Kommunanalys"

Contents:
- Searchable municipality dropdown
- KRI score, rank, risk class display
- 15 year trend line chart with national average reference
- Peer municipality comparison table (10 most similar)
- Full indicator table for all years (downloadable as CSV)
- Data quality flags panel

---

## 7. Deliverables

| # | Deliverable | Format |
|---|------------|--------|
| 1 | Streamlit dashboard (3 pages) | Python / Streamlit |
| 2 | PDF report (5 pages, Swedish content) | PDF |
| 3 | GitHub repo with reproducible pipeline | Git |
| 4 | Methodology document | Markdown |
| 5 | README with installation instructions | Markdown |

---

## 8. Acceptance Criteria

### Functional
- [ ] All 290 municipalities displayed with KRI scores
- [ ] Data covers 2010 to 2024
- [ ] All 5 core variables integrated
- [ ] Risk classification (low/medium/high) functional
- [ ] Distribution chart present and functional
- [ ] Municipality deep dive with trend data works
- [ ] PDF report generates

### Non functional
- [ ] Dashboard loads within 5 seconds
- [ ] All user facing text in Swedish (zero English in UI)
- [ ] Desktop responsive layout
- [ ] Data quality flags visible
- [ ] Cached data for fast access

---

## 9. Language Rules

**Code layer (English):**
- Variable names: `debt_per_capita`, `unemployment_rate`, `dependency_ratio`
- Function names: `fetch_balance_sheet()`, `compute_kri()`, `render_map()`
- File names: `data_fetcher.py`, `index_builder.py`
- Comments and docstrings: English
- Git commit messages: English

**User facing layer (Swedish only, no exceptions):**
- All Streamlit page titles
- All chart axis labels (e.g., "Skuld per capita (kr)", "Arbetslöshet (%)")
- All chart legends (e.g., "Låg risk", "Medel risk", "Hög risk")
- All tooltips
- All table headers (e.g., "Kommun", "KRI Poäng", "Rang", "Riskklass")
- All KPI card titles
- All sidebar labels and filters
- All button labels
- PDF report content
- Error messages shown to user

**Label mapping (stored in config.py):**
```python
SWEDISH_LABELS = {
    "debt_per_capita": "Skuld per capita",
    "unemployment": "Arbetslöshet",
    "dependency_ratio": "Försörjningskvot",
    "population_growth": "Befolkningstillväxt",
    "tax_base": "Skattekraft",
    "kri_score": "KRI Poäng",
    "rank": "Rang",
    "risk_class": "Riskklass",
    "low_risk": "Låg risk",
    "medium_risk": "Medel risk",
    "high_risk": "Hög risk",
    "municipality": "Kommun",
    "year": "År",
    "national_average": "Rikssnitt",
    "population": "Befolkning",
    "annual_result": "Årets resultat",
    "tax_rate": "Kommunalskattesats",
    "equity_ratio": "Soliditet",
}
```

---

## 10. Context Files

All tasks in TASKS.md reference:
- `docs/PRD.md` (this document)
- `docs/METHODOLOGY.md` (methodology and data specification)
- `docs/TASKS.md` (all tasks with prompts)
- `docs/KRI_Dataset_Identification.md` (original dataset analysis)