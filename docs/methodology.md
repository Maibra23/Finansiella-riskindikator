# Methodology: Kommunal Finansiell Riskindikator (KRI)

## 1. Theoretical Foundation

### 1.1 What KRI measures
KRI (Kommunal Finansiell Riskindikator) is a composite index that quantifies the structural economic vulnerability of Sweden's 290 municipalities. The index combines five dimensions of financial risk into a single comparable score, updated annually for the period 2010–2024.

The index draws on established frameworks in public finance analysis:
- OECD Fiscal Decentralisation Database methodology
- EU Fiscal Sustainability Reports
- SKR (Sveriges Kommuner och Regioner) economic reporting standards
- Riksbanken financial stability analysis approaches

### 1.2 Why a composite index?
Individual indicators (e.g., debt or unemployment alone) give an incomplete picture. A municipality can have high debt but a strong tax base (e.g., Stockholm), or low debt but a rapidly shrinking population (e.g., rural inland municipalities). By combining five dimensions, the overall risk profile is captured more accurately than any single metric allows.

### 1.3 Analysis period
**2010 to 2024 (15 years)**

Rationale:
- All five core variables have complete time series from 2010 across all 290 municipalities
- The period covers a full business cycle: post-2008/2009 recovery, growth years, pandemic shock 2020–2021, inflation shock 2022–2023
- Arbetsförmedlingen unemployment series (Kolada N03937) is consistent from 2010; no methodology breaks occur within this period
- SCB's municipal accounting summary table series (BalansKn, ResultKn) has consistent definitions from 1998 onward

---

## 2. Data Specification

### 2.1 Overview of All Data Sources

| Variable | Column name | Weight | Source system | Source series | Coverage |
|----------|-------------|--------|---------------|---------------|----------|
| Long-term debt per capita | `debt_per_capita` | 0.25 | SCB PxWeb API | BalansKn, post 089 | 290 munis × 15 yrs |
| Unemployment rate | `unemployment` | 0.25 | Kolada API → Arbetsförmedlingen | KPI N03937 | 290 munis × 15 yrs |
| Dependency ratio | `dependency_ratio` | 0.20 | SCB PxWeb API | BefolkningNy, ages 0–100+ | 290 munis × 15 yrs |
| Population growth (5-yr) | `population_growth` | 0.15 | SCB PxWeb API | BefolkningNy, "tot" age | 290 munis × 15 yrs |
| Tax base strength | `tax_base_relative` | 0.15 | SCB PxWeb API | SkatteKraft, OE0101B0 | 290 munis × 15 yrs |

All five variables achieve **100% coverage** (zero missing values) for all 290 municipalities and all 15 years.

---

### 2.2 Variable 1: Long-term Debt per Capita (`debt_per_capita`)

#### Source
| Field | Detail |
|-------|--------|
| **Data provider** | Statistics Sweden (SCB) |
| **Series name** | Balansräkning för kommuner efter region och balansräkningsposter, tkr, löpande priser |
| **SCB table ID** | BalansKn |
| **SCB subject area** | OE — Offentlig ekonomi |
| **API base URL** | `https://api.scb.se/OV0104/v1/doris/sv/ssd/OE/OE0107/OE0107G/BalansKn` |
| **Web browser URL** | `https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__OE__OE0107__OE0107G/BalansKn/` |
| **License** | Open data, free to use (SCB open license) |

#### API query (exact, reproducible)
```json
POST https://api.scb.se/OV0104/v1/doris/sv/ssd/OE/OE0107/OE0107G/BalansKn
{
  "query": [
    {"code": "Region",          "selection": {"filter": "all",  "values": ["*"]}},
    {"code": "Balansraknposter","selection": {"filter": "item", "values": ["089"]}},
    {"code": "ContentsCode",    "selection": {"filter": "item", "values": ["OE0107E5"]}},
    {"code": "Tid",             "selection": {"filter": "item", "values": ["2010","2011","2012","2013","2014","2015","2016","2017","2018","2019","2020","2021","2022","2023","2024"]}}
  ],
  "response": {"format": "json"}
}
```

#### Variable codes
| Code | Label | Meaning |
|------|-------|---------|
| Balansraknposter = `089` | Långfristiga skulder | Long-term liabilities (the extracted balance post) |
| ContentsCode = `OE0107E5` | Tkr, löpande priser | Thousands of SEK, current prices |

**Note:** The table was previously named `BalansKnN` in older SCB documentation. The current active path is `BalansKn`. The old path returns HTTP 404.

#### Transformation
```
debt_per_capita (SEK) = (long_term_liabilities_tkr × 1000) / total_population
```
- Population denominator comes from Variable 4 (BefolkningNy, "tot" age group)
- Gotland (code 0980): result multiplied by 0.65 (SCB estimate: 65% of Gotland's accounting relates to municipal vs. regional activities)

#### Observed data range (2010–2024, all 290 municipalities)
| Statistic | Value |
|-----------|-------|
| Minimum | 24,530 SEK/capita |
| Maximum | 523,514 SEK/capita (Kiruna, 2024) |
| Mean | 105,327 SEK/capita |
| Median | 90,340 SEK/capita |

#### Fact-check benchmarks
| Municipality | Year | Expected (SEK/capita) | Source |
|---|---|---|---|
| Stockholm (0180) | 2023 | ~350,000–400,000 | SCB Statistikdatabasen |
| Stockholm (0180) | 2023 | **363,491** (observed) | ✓ Within expected range |

---

### 2.3 Variable 2: Unemployment Rate (`unemployment`)

#### Source
| Field | Detail |
|-------|--------|
| **Data provider** | Arbetsförmedlingen (Swedish Public Employment Service) |
| **Distribution channel** | Kolada API (RKA — Rådet för kommunal analys) |
| **Kolada KPI ID** | **N03937** |
| **KPI full title** | Öppet arbetslösa av befolkningen, 18–65 år, andel (%) |
| **KPI description** | Openly registered unemployed persons aged 18–65, as a percentage of total population aged 18–65. Annual average of monthly figures. |
| **Kolada API base URL** | `https://api.kolada.se/v2/` |
| **KPI metadata URL** | `https://api.kolada.se/v2/kpi/N03937` |
| **License** | Open data, free use (RKA/Kolada open license) |

#### API query (exact, reproducible)
```
GET https://api.kolada.se/v2/data/kpi/N03937/year/2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024
```

Kolada returns paginated JSON (max 5,000 records per page). All municipalities are returned in a single call. The pipeline follows `next_page` links to collect all records.

#### Response structure
```json
{
  "values": [
    {
      "kpi": "N03937",
      "municipality": "0180",
      "period": 2023,
      "values": [{"count": 1, "gender": "T", "status": "", "value": 2.91}]
    },
    ...
  ],
  "next_page": null
}
```
- `gender = "T"` selects the total (both sexes combined)
- `municipality` is the 4-digit SCB municipality code

#### Definition detail
- **Numerator:** Number of persons aged 18–65 registered as openly unemployed with Arbetsförmedlingen, monthly average over the calendar year
- **Denominator:** Total population aged 18–65 in the municipality (from SCB population register)
- **Scope:** Openly unemployed only — does NOT include persons in labour market programmes (åtgärder). This is a narrower definition than the AKU (Labour Force Survey) measure.

#### Why N03937, not other KPIs
During implementation, the following Kolada unemployment KPIs were evaluated and rejected:

| KPI | Title | Years available | Reason rejected |
|-----|-------|-----------------|-----------------|
| N00945 | (unrelated — parental leave KPI) | 2010–2015 | Wrong variable entirely |
| N00708 | Arbetslöshet, inrikes födda 20–64 | 2013–2014 only | Insufficient coverage |
| N03935 | Arbetslösa 18–24 år, andel (%) | 2010–2011, 2018–2019 | Insufficient coverage; youth-only |
| N03936 | Arbetslöshet 18–24, årsmedelvärde | 2010–2011 only | Insufficient coverage; youth-only |
| **N03937** | **Öppet arbetslösa 18–65 år, andel (%)** | **2010–2024, all 290** | **Selected** |

#### Why not SCB RAMS/BAS?
SCB's register-based labour market statistics (RAMS) was replaced by BAS in 2019. This creates a structural break making pre-2019 and post-2019 data not directly comparable. Arbetsförmedlingen series N03937 uses a consistent definition throughout 2010–2024.

#### Observed data range (2010–2024, all 290 municipalities)
| Statistic | Value |
|-----------|-------|
| Minimum | 0.94% |
| Maximum | 7.50% |
| Mean | 3.07% |
| Median | 2.97% |

#### Fact-check benchmarks
| Municipality | Year | Expected (%) | Source |
|---|---|---|---|
| Stockholm (0180) | 2023 | 2–4% (Arbetsförmedlingen regional statistics) | Verified: **2.91%** ✓ |
| Danderyd (0162) | 2023 | < 2% (affluent suburb, full employment) | Verified: **1.53%** ✓ |
| National mean | 2023 | ~2–3% (N03937 is narrower than AKU) | Verified: **2.20%** ✓ |

**Note on national mean vs. AKU:** The AKU (Labour Force Survey) publishes a broader unemployment rate of approximately 8–9% for 2023. This is not comparable to N03937. The AKU uses ILO definition (includes inactive job-seekers, persons in programmes, etc.) and covers all ages 15–74. N03937 is restricted to those actively registered as openly unemployed aged 18–65, producing a structurally lower figure. For relative municipal comparison within the same metric, this is valid.

---

### 2.4 Variable 3: Dependency Ratio (`dependency_ratio`)

#### Source
| Field | Detail |
|-------|--------|
| **Data provider** | Statistics Sweden (SCB) |
| **Series name** | Folkmängden efter region, civilstånd, ålder och kön |
| **SCB table ID** | BefolkningNy |
| **SCB subject area** | BE — Befolkning |
| **API base URL** | `https://api.scb.se/OV0104/v1/doris/sv/ssd/BE/BE0101/BE0101A/BefolkningNy` |
| **Web browser URL** | `https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__BE__BE0101__BE0101A/BefolkningNy/` |
| **Available period** | 1968 to 2024 |
| **License** | Open data, free to use |

#### API query strategy (batched, exact)
SCB enforces a 150,000-cell limit per request. With ~312 region codes × 15 years × 1 content code = 4,680 cells per age, a maximum of ~32 ages per request is safe. The pipeline uses batch_size = 30.

**Each batch request (example — ages 0–29):**
```json
POST https://api.scb.se/OV0104/v1/doris/sv/ssd/BE/BE0101/BE0101A/BefolkningNy
{
  "query": [
    {"code": "Region",       "selection": {"filter": "all",  "values": ["*"]}},
    {"code": "Alder",        "selection": {"filter": "item", "values": ["0","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22","23","24","25","26","27","28","29"]}},
    {"code": "ContentsCode", "selection": {"filter": "item", "values": ["BE0101N1"]}},
    {"code": "Tid",          "selection": {"filter": "item", "values": ["2010","2011","2012","2013","2014","2015","2016","2017","2018","2019","2020","2021","2022","2023","2024"]}}
  ],
  "response": {"format": "json"}
}
```
Total batches: 4 (ages 0–29, 30–59, 60–89, 90–100+). Results concatenated into a single DataFrame.

**Note:** `Civilstand` (marital status) and `Kon` (sex) are intentionally excluded from the query. This returns population summed across all marital statuses and both sexes for each single-year age, which is what is needed for dependency ratio. Including them would multiply the cell count by ~8 and exceed the SCB limit.

#### Variable codes
| Code | Label |
|------|-------|
| ContentsCode = `BE0101N1` | Folkmängd (population count) |
| Alder | Single-year ages "0", "1", ..., "99", "100+" |

#### Calculation
```
young   = sum(population, ages 0–19)
working = sum(population, ages 20–64)
old     = sum(population, ages 65–100+)

dependency_ratio = (young + old) / working
```

- A value of 0.857 means: for every 100 working-age persons, there are 85.7 dependents (children + elderly)
- Only valid municipality codes (4-digit, present in config.MUNICIPALITIES) are retained

#### Observed data range (2010–2024, all 290 municipalities)
| Statistic | Value |
|-----------|-------|
| Minimum | 0.508 (urban high-working-age municipality) |
| Maximum | 1.241 (small ageing rural municipality) |
| Mean | 0.857 |
| Median | 0.860 |

#### Fact-check benchmarks
- National dependency ratio in Sweden (Statistics Sweden): approximately 0.80–0.90 for 2015–2023 ✓
- Urban municipalities (Stockholm, Göteborg) tend toward 0.55–0.65 (younger population skew) ✓
- Small inland municipalities (Dorotea, Bjurholm) tend toward 1.0–1.3 (ageing demographic) ✓

---

### 2.5 Variable 4: Population Growth, 5-year rolling (`population_growth`)

#### Source
| Field | Detail |
|-------|--------|
| **Data provider** | Statistics Sweden (SCB) |
| **Series name** | Same as Variable 3 — BefolkningNy |
| **SCB table ID** | BefolkningNy |
| **API base URL** | `https://api.scb.se/OV0104/v1/doris/sv/ssd/BE/BE0101/BE0101A/BefolkningNy` |
| **Available period** | 1968 to 2024 |

#### API query (exact, reproducible)
```json
POST https://api.scb.se/OV0104/v1/doris/sv/ssd/BE/BE0101/BE0101A/BefolkningNy
{
  "query": [
    {"code": "Region",       "selection": {"filter": "all",  "values": ["*"]}},
    {"code": "Civilstand",   "selection": {"filter": "all",  "values": ["*"]}},
    {"code": "Alder",        "selection": {"filter": "item", "values": ["tot"]}},
    {"code": "Kon",          "selection": {"filter": "all",  "values": ["*"]}},
    {"code": "ContentsCode", "selection": {"filter": "item", "values": ["BE0101N1"]}},
    {"code": "Tid",          "selection": {"filter": "item", "values": ["2005","2006","2007","2008","2009","2010","2011","2012","2013","2014","2015","2016","2017","2018","2019","2020","2021","2022","2023","2024"]}}
  ],
  "response": {"format": "json"}
}
```

- `Alder = "tot"` returns total population (all ages summed)
- `Civilstand = all` and `Kon = all` are included; their cross-product is summed in the cleaning step
- Years start from 2005 because a 5-year lag is required to compute growth from 2010 onward

#### Variable codes
| Code | Label |
|------|-------|
| Alder = `tot` | Total population (all ages) |
| ContentsCode = `BE0101N1` | Folkmängd (population count) |

#### Calculation
```
total_population(municipality, year) = sum(value, across all Civilstand × Kon for Alder="tot")

population_growth(i, t) = ((total_pop(i, t) / total_pop(i, t-5)) - 1) × 100
```

- Result is percentage change over 5 years
- 2010 growth = % change from 2005 to 2010; 2024 growth = % change from 2019 to 2024
- Positive = population increased = lower structural risk
- Negative = population declined = higher structural risk (direction inverted before KRI weighting)

#### Rationale for 5-year window
Single-year population changes are volatile, especially in small municipalities (< 5,000 inhabitants) where a single housing development or factory closure can produce a +5% or -5% swing. A 5-year window smooths these fluctuations and reflects structural demographic trends.

#### Observed data range (2010–2024, all 290 municipalities)
| Statistic | Value |
|-----------|-------|
| Minimum | −10.76% (severe depopulation) |
| Maximum | +21.16% (strong growth municipality) |
| Mean | +2.02% |
| Median | +1.88% |

#### Fact-check benchmarks
- Dorotea (2425, remote inland municipality), 2023: **−8.92%** 5-year decline ✓ (consistent with known depopulation trend)
- Stockholm (0180), 2023: **+2.78%** ✓ (moderate growth; slower than pre-pandemic)
- Swedish national population grew ~5% between 2019 and 2024 (net immigration + natural increase) — individual municipality dispersion around this is expected ✓

---

### 2.6 Variable 5: Tax Base Strength (`tax_base_relative`)

#### Source
| Field | Detail |
|-------|--------|
| **Data provider** | Statistics Sweden (SCB) |
| **Series name** | Skatteunderlag och skattekraft efter region och tabellinnehåll |
| **SCB table ID** | SkatteKraft |
| **SCB subject area** | OE — Offentlig ekonomi |
| **API base URL** | `https://api.scb.se/OV0104/v1/doris/sv/ssd/OE/OE0101/SkatteKraft` |
| **Web browser URL** | `https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__OE__OE0101/SkatteKraft/` |
| **Available period** | 1995 to 2026 |
| **License** | Open data, free to use |

#### API query (exact, reproducible)
```json
POST https://api.scb.se/OV0104/v1/doris/sv/ssd/OE/OE0101/SkatteKraft
{
  "query": [
    {"code": "Region",       "selection": {"filter": "all",  "values": ["*"]}},
    {"code": "ContentsCode", "selection": {"filter": "item", "values": ["OE0101B0"]}},
    {"code": "Tid",          "selection": {"filter": "item", "values": ["2010","2011","2012","2013","2014","2015","2016","2017","2018","2019","2020","2021","2022","2023","2024"]}}
  ],
  "response": {"format": "json"}
}
```

#### Variable code
| Code | Label | Meaning |
|------|-------|---------|
| ContentsCode = `OE0101B0` | Andel av riksmedelvärdet, procent | Taxable income per inhabitant as % of the national average |

- 100 = exactly the national average
- 150 = 50% above national average (strong tax base)
- 80 = 20% below national average (weak tax base)

#### Definition
Tax base is calculated from the taxable income reported to Skatteverket (Swedish Tax Agency). SCB publishes the result as each municipality's per-capita taxable income divided by the national average, expressed as a percentage.

**Important time lag:** The tax base for year T is based on incomes declared in year T−1 and reported to municipalities for T+1 budget planning purposes. In practice, "skattekraft 2024" reflects approximately 2022 incomes. This is a systemic property of Swedish municipal finance and affects all municipalities equally.

#### Observed data range (2010–2024, all 290 municipalities)
| Statistic | Value |
|-----------|-------|
| Minimum | 72% (significantly below national average) |
| Maximum | 191% (nearly double national average) |
| Mean | 93.1% (slightly below 100 due to population-weighting) |
| Median | 90% |

#### Fact-check benchmarks
| Municipality | Year | Expected (%) | Verified |
|---|---|---|---|
| Danderyd (0162) | 2023 | > 150% (highest in Sweden historically) | **184%** ✓ |
| Stockholm (0180) | 2023 | ~125–135% | **131%** ✓ |
| National median | 2023 | ~88–92% (majority below 100 due to skewed distribution) | **89%** ✓ |

---

### 2.7 Supplementary Variable 6: Annual Financial Result

| Field | Detail |
|-------|--------|
| **Purpose** | Deep-dive analysis; not in core KRI formula |
| **Data provider** | Statistics Sweden (SCB) |
| **Series name** | Resultaträkning för kommuner |
| **SCB table ID** | ResultKn |
| **API base URL** | `https://api.scb.se/OV0104/v1/doris/sv/ssd/OE/OE0107/OE0107G/ResultKn` |
| **Post extracted** | Code `120` = Årets resultat (annual net result) |
| **ContentsCode** | `OE0107E3` = Tkr, löpande priser |
| **Available period** | 1998 to 2024 |
| **Unit** | Tkr (thousands of SEK), convertible to kr/inhabitant |
| **Direction** | Negative result = higher risk signal |

**Note:** Post code `070` (Verksamhetens nettokostnad) was originally specified but corrected to `120` (Årets resultat) which is the standard "bottom line" result figure used in SKR and municipal finance analysis.

---

### 2.8 Supplementary Variable 7: Municipal Tax Rate

| Field | Detail |
|-------|--------|
| **Purpose** | Deep-dive analysis; supplementary context |
| **Data provider** | Statistics Sweden (SCB) |
| **Series name** | Kommunalskatter |
| **SCB table ID** | Kommunalskatter2000 |
| **API base URL** | `https://api.scb.se/OV0104/v1/doris/sv/ssd/OE/OE0101/Kommunalskatter2000` |
| **ContentsCode** | `OE0101D2` = Skattesats till kommun (municipal rate only, excl. regional/landsting) |
| **Available period** | 2000 to 2026 |
| **Unit** | Percent (%) |
| **Interpretation** | Very high rate (> 22–23%) may indicate the municipality has approached its practical taxing capacity |

**Note:** The original table path `Komskatter` is deprecated. Current active path is `Kommunalskatter2000`.

---

### 2.9 Supplementary Variable 8: Equity Ratio (Soliditet)

| Field | Detail |
|-------|--------|
| **Purpose** | Deep-dive analysis; supplementary context |
| **Calculation** | Eget kapital (post 090) / Summa skulder och eget kapital (post 100) × 100 |
| **Source** | SCB BalansKn, posts 090 and 100 |
| **Unit** | Percent (%) |
| **Direction** | Low equity ratio = high leverage = increased risk signal |

---

### 2.10 Complete API Reference Card

#### SCB PxWeb API
- **Base URL:** `https://api.scb.se/OV0104/v1/doris/sv/ssd/`
- **Method:** HTTP POST with JSON body
- **Response format:** JSON (table format with `columns` and `data` arrays)
- **Cell limit:** 150,000 cells per request
- **Authentication:** None required (open API)
- **Rate limiting:** No hard limit; be polite — pipeline uses 0.5s delay between requests
- **Region filter for all municipalities:** `{"code": "Region", "selection": {"filter": "all", "values": ["*"]}}`

**Deprecated filter (do not use):** `{"filter": "vs:RegionKommun07", "values": []}` — returns HTTP 400

#### Kolada API
- **Base URL:** `https://api.kolada.se/v2/`
- **Method:** HTTP GET
- **Response format:** JSON with `values` array and `next_page` pagination
- **Page size:** 5,000 records per page; follow `next_page` URL for subsequent pages
- **Authentication:** None required (open API)
- **KPI metadata:** `GET /v2/kpi/<KPI_ID>`
- **Data fetch:** `GET /v2/data/kpi/<KPI_ID>/year/<Y1>,<Y2>,...`
- **Gender field:** Use `"gender": "T"` for total (both sexes combined)

---

## 3. Model Specification

### 3.1 KRI formula

```
KRI(i,t) = w1 × z(debt_per_capita(i,t))
          + w2 × z(unemployment(i,t))
          + w3 × z(dependency_ratio(i,t))
          + w4 × z(−population_growth(i,t))
          + w5 × z(−tax_base_relative(i,t))
```

Where:
- `i` = municipality index (1–290)
- `t` = year (2010–2024)
- `z(x)` = cross-sectional z-score: `(x − mean_t) / std_t`, where mean and std are computed across all 290 municipalities within year t
- Negative sign on `population_growth` and `tax_base_relative`: these variables are inverted because higher values indicate lower risk

### 3.2 Weights

| Variable | Weight | Rationale |
|----------|--------|-----------|
| Debt per capita | 0.25 | Direct financial obligation; strongest short-term solvency signal |
| Unemployment | 0.25 | Immediate tax base erosion and rising social costs |
| Dependency ratio | 0.20 | Structural long-term demographic pressure on welfare spending |
| Population growth | 0.15 | Long-term trajectory; declining population signals structural revenue decline |
| Tax base strength | 0.15 | Revenue capacity; partially correlated with other variables |
| **Total** | **1.00** | |

### 3.3 Normalization method

**Z-score (cross-sectional, per year):**
```
z(x_i,t) = (x_i,t − mean(x_t)) / std(x_t)
```

- Mean and standard deviation are computed across all 290 municipalities **within** the same year
- This makes rankings relative (a municipality is "high risk" relative to its peers that year)
- The index is NOT comparable in absolute terms across years — only rankings are interpretable across time

**Why z-scores?**
- Makes all five variables comparable regardless of original unit (SEK, %, ratio)
- Preserves relative distances between municipalities
- Standard method in composite indices: UNDP Human Development Index, EU Regional Competitiveness Index, OECD Better Life Index

### 3.4 Classification method

**Quantile-based thresholds (computed per year):**
- Low risk (Låg): KRI below 25th percentile (~72 municipalities per year)
- Medium risk (Medel): KRI between 25th and 75th percentile (~146 municipalities)
- High risk (Hög): KRI above 75th percentile (~72 municipalities)

**Rationale:** Quantile-based classification is robust to outliers and produces a stable distribution regardless of whether all municipalities improve or worsen in absolute terms. K-means clustering was evaluated as an alternative but produces year-to-year instability in cluster boundaries.

---

## 4. Evaluation and Validation

### 4.1 Sanity checks (verified against real data)

| Check | Expected | Verified |
|-------|----------|---------|
| Danderyd (0162): tax base | > 150% (historically highest in Sweden) | **184% (2023)** ✓ |
| Danderyd (0162): unemployment | < 2% | **1.53% (2023)** ✓ |
| Stockholm (0180): debt/capita | ~350,000–400,000 SEK | **363,491 SEK (2023)** ✓ |
| Stockholm (0180): unemployment | 2–4% | **2.91% (2023)** ✓ |
| Dorotea (2425): pop. growth | Strongly negative | **−8.92% (2023)** ✓ |
| National dep. ratio mean | ~0.75–0.90 | **0.857** ✓ |
| National unemployment mean | ~2.0–3.0% (N03937 definition) | **2.20% (2023)** ✓ |

### 4.2 Temporal stability
- KRI rankings should be relatively stable between adjacent years (correlation > 0.85 expected)
- Large rank jumps (> 50 positions) should be investigated and documented
- The pandemic (2020–2021) caused genuine unemployment spikes in Stockholm belt, Strömstad, Göteborg — these are verified real events, not data errors

### 4.3 Data audit results (automated verification)
A full automated audit was run on `data/processed/kri_base_data.parquet`:
- **0 failures** across 48 checks
- **5 warnings** — all attributable to real economic events (COVID-2020 unemployment spike, Linköping 2024 capital investment, small-municipality demographic ageing)
- Zero NaN values in all 5 core variables across all 4,350 rows (290 municipalities × 15 years)
- No duplicate (municipality, year) pairs
- All values within expected real-world ranges

---

## 5. Bias, Limitations, and Interpretation Warnings

### 5.1 Known biases

**Size bias:** Municipalities with fewer than 5,000 inhabitants show more volatile single-year indicators. A factory closure can cause a +3% unemployment spike in one year. Mitigation: 5-year rolling average for population growth. Debt and tax base are less affected. Residual volatility is documented.

**Time lag in tax base:** Tax base for year T reflects incomes from approximately T−2. Rapid economic shocks (e.g., a major employer's sudden departure) appear in the tax base data with a 2-year delay.

**Registration bias in unemployment (N03937):** Persons who are unemployed but not registered with Arbetsförmedlingen are not counted. This particularly affects municipalities with large commuter flows or high self-employment rates. The bias is consistent across municipalities and time, preserving validity for relative comparison.

**Gotland special case:** Region Gotland carries both municipal and regional accounting. SCB estimates that 65% of the balance sheet relates to municipal activities. The pipeline applies a 0.65 adjustment factor to Gotland's debt figures. This is an estimate, not an exact figure.

**High-debt / high-tax-base co-occurrence:** Growth municipalities in the Stockholm commuter belt (e.g., Värmdö, Nykvarn) borrow heavily to fund infrastructure while simultaneously having high per-capita incomes. This produces a counter-intuitive combination of high debt and high tax base. The KRI formula correctly captures both dimensions, but the risk profile of these municipalities is structurally different from distressed rural municipalities with high debt.

### 5.2 Model limitations

- Weights (0.25/0.25/0.20/0.15/0.15) are normatively set based on economic reasoning, not empirically derived from default rates or credit events
- The index measures structural vulnerability, not political capacity to manage challenges
- Z-score normalization is purely relative: the index always identifies "high risk" municipalities even if all municipalities improve in absolute terms. Use trend analysis for absolute assessment.
- The 5-year population growth lag means 2010–2014 values are computed from 2005–2009 baseline data. This is correct methodology but should be noted when interpreting early-period results.

### 5.3 Interpretation warnings

**KRI should be interpreted as:**
- A relative ranking tool for comparing structural vulnerability between municipalities
- An indication of long-term structural pressure, not short-term cash flow crisis
- A complement to qualitative analysis, budgetary documents, and audit reports

**KRI should NOT be interpreted as:**
- An absolute probability of fiscal crisis or debt default
- A measure of service quality, political competence, or quality of life
- A recommendation regarding investment or lending decisions

---

## 6. Handling Incomplete Data

### 6.1 Identification
Every municipality is checked for complete data across all 5 core variables for all 15 years (2010–2024). As of the last pipeline run, all 290 municipalities have zero missing values.

### 6.2 Strategies (applied if future data gaps arise)

| Situation | Strategy |
|-----------|----------|
| Single missing year (1–2 years) | Linear interpolation between adjacent years |
| Missing at start of series (2010–2011) | Forward extrapolation from first available year (limit: 2 years) |
| Missing at end of series | Backward extrapolation from last available year (limit: 2 years) |
| More than 3 consecutive missing years | Municipality excluded from ranking that year; flagged in UI |
| Variable entirely missing for a municipality | Municipality included with remaining variables; weights redistributed proportionally |

### 6.3 Dashboard documentation
- Municipalities with interpolated data are marked with an asterisk (*) in tables
- An info panel shows the count of municipalities with complete vs. interpolated data per year
- Data quality flags include: Gotland (adjusted accounting), Knivsta (formed 2003, limited pre-2010 history), Heby (county change 2007)

---

## 7. Known Data Issues and Resolutions

### 7.1 Unemployment KPI Selection Process

During development, the following Kolada unemployment KPIs were evaluated:

| KPI | Title | Years with data | Verdict |
|-----|-------|-----------------|---------|
| N00945 | (parental leave KPI — mislabelled in early docs) | 2010–2015 | **Rejected**: wrong variable |
| N00708 | Arbetslöshet, inrikes födda 20–64 år | 2013–2014 only | **Rejected**: 2 years only |
| N03935 | Arbetslösa av befolkningen, 18–24 år | 2010–2011, 2018–2019 | **Rejected**: youth-only, non-continuous |
| N03936 | Arbetslöshet 18–24 år, årsmedelvärde | 2010–2011 only | **Rejected**: youth-only, 2 years |
| N01961 | Invånare 20–64 år, andel (%) | 2010–2011 only | **Rejected**: not unemployment; used as proxy candidate for dependency ratio before SCB solution found |
| **N03937** | **Öppet arbetslösa 18–65 år, andel (%)** | **2010–2024 (all 15 yrs)** | **Selected** |

### 7.2 Dependency Ratio Data Source Change

Originally planned: compute dependency ratio from Kolada KPI N01961 (working-age population share). This KPI only had data for 2010–2011, making it unusable.

**Resolution:** Fetch single-year age populations directly from SCB BefolkningNy using batched API requests (ages 0–100+ in batches of 30). This provides complete 2010–2024 data and is more accurate than Kolada's pre-aggregated figure. The SCB source data is the underlying source Kolada itself uses.

### 7.3 SCB API Path Corrections

| Original path (from documentation) | Correct active path | Error |
|-------------------------------------|---------------------|-------|
| `BalansKnN` | `BalansKn` | HTTP 404 (deprecated) |
| `Komskatter` | `Kommunalskatter2000` | HTTP 404 (deprecated) |
| Region filter: `vs:RegionKommun07` | `filter: "all", values: ["*"]` | HTTP 400 |
| ResultKn post `070` | ResultKn post `120` | Wrong variable (070 = nettokostnad, 120 = årets resultat) |

### 7.4 Final Data Quality Summary

| Variable | Column | Coverage | Zero missing | Source |
|----------|--------|----------|--------------|--------|
| Long-term debt per capita | `debt_per_capita` | 100% | ✓ | SCB BalansKn, post 089 |
| Unemployment rate | `unemployment` | 100% | ✓ | Kolada N03937 |
| Dependency ratio | `dependency_ratio` | 100% | ✓ | SCB BefolkningNy, ages 0–100+ |
| Population growth (5-yr) | `population_growth` | 100% | ✓ | SCB BefolkningNy, "tot" |
| Tax base relative | `tax_base_relative` | 100% | ✓ | SCB SkatteKraft, OE0101B0 |

**Dataset dimensions:** 4,350 rows (290 municipalities × 15 years), 8 columns, 0 NaN values.

---

## 8. Reproducibility

### 8.1 Step-by-step reproduction

To reproduce the dataset from scratch:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Fetch fresh data and rebuild (clears cache first)
python scripts/run_pipeline.py --no-cache --clear-cache

# 3. Verify output
python scripts/verify_pipeline.py

# Expected: ALL CHECKS PASSED
```

### 8.2 Expected output file
```
data/processed/kri_base_data.parquet
  Rows:    4,350
  Columns: municipality_code, municipality_name, year,
           debt_per_capita, unemployment, dependency_ratio,
           population_growth, tax_base_relative
  NaN:     0
```

### 8.3 Cache files produced
| File | Contents | Rows |
|------|----------|------|
| `data/cache/balance_sheet.parquet` | SCB BalansKn, posts 050/089/100, all municipalities, 2010–2024 | 13,095 |
| `data/cache/population.parquet` | SCB BefolkningNy, total population, all municipalities, 2005–2024 | 49,920 |
| `data/cache/tax_base.parquet` | SCB SkatteKraft, OE0101B0, all municipalities, 2010–2024 | 4,680 |
| `data/cache/income_statement.parquet` | SCB ResultKn, post 120, all municipalities, 2010–2024 | 4,365 |
| `data/cache/tax_rate.parquet` | SCB Kommunalskatter2000, OE0101D2, all municipalities, 2010–2024 | 4,680 |
| `data/cache/population_by_age.parquet` | SCB BefolkningNy, ages 0–100+, all municipalities, 2010–2024 | 472,680 |
| `data/cache/kolada_unemployment.parquet` | Kolada N03937, all municipalities, 2010–2024 | 59,130 |

### 8.4 Versioning
- All raw API responses saved in `data/raw/` with timestamp suffixes
- Parquet files are reproducible: re-running `--no-cache` produces byte-identical output (API data does not change for historical years)
- `requirements.txt` pins all package versions for full environment reproducibility
