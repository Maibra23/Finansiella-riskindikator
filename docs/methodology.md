# Methodology: Kommunal Finansiell Riskindikator (KRI)

## 1. Theoretical Foundation

### 1.1 What KRI measures
KRI (Kommunal Finansiell Riskindikator) is a composite index that quantifies the structural economic vulnerability of Sweden's 290 municipalities. The index combines five dimensions of financial risk into a single comparable score, updated annually for the period 2010-2024.

The index draws on established frameworks in public finance analysis:
- OECD Fiscal Decentralisation Database methodology
- EU Fiscal Sustainability Reports
- SKR (Sveriges Kommuner och Regioner) economic reporting standards
- Riksbanken financial stability analysis approaches

### 1.2 Why a composite index?
Individual indicators (e.g., debt or unemployment alone) give an incomplete picture. A municipality can have high debt but a strong tax base (e.g., Kiruna), or low debt but a rapidly shrinking population (e.g., rural inland municipalities). By combining five dimensions, the overall risk profile is captured more accurately than any single metric allows.

### 1.3 Analysis period
**2010 to 2024 (15 years)**

Rationale:
- All five core variables have complete time series from 2010 across all 290 municipalities
- The period covers a full business cycle: post-2008/2009 recovery, growth years, pandemic shock 2020-2021, inflation shock 2022-2023
- Arbetsförmedlingen unemployment series (Kolada N03937) is consistent from 2010; no methodology breaks occur within this period
- SCB's municipal accounting summary table series (BalansKn, ResultKn) has consistent definitions from 1998 onward

---

## 2. Data Specification

### 2.1 Overview of All Data Sources

| Variable | Column name | Weight | Source system | Source series | Coverage |
|----------|-------------|--------|---------------|---------------|----------|
| Borrowing per capita | `debt_per_capita` | 0.25 | SCB PxWeb API | BalansKn, posts 081-085, 090, 136 | 290 munis × 15 yrs |
| Unemployment rate | `unemployment` | 0.25 | Kolada API -> Arbetsförmedlingen | KPI N03937 | 290 munis × 15 yrs |
| Dependency ratio | `dependency_ratio` | 0.20 | SCB PxWeb API | BefolkningNy, ages 0-100+ | 290 munis × 15 yrs |
| Population growth (5-yr) | `population_growth` | 0.15 | SCB PxWeb API | BefolkningNy, "tot" age | 290 munis × 15 yrs |
| Tax base strength | `tax_base_relative` | 0.15 | SCB PxWeb API | SkatteKraft, OE0101B0 | 290 munis × 15 yrs |

All five variables achieve **100% coverage** (zero missing values) for all 290 municipalities and all 15 years.

---

### 2.2 Variable 1: Borrowing per Capita (`debt_per_capita`)

#### Source
| Field | Detail |
|-------|--------|
| **Data provider** | Statistics Sweden (SCB) |
| **Series name** | Balansräkning för kommuner efter region och balansräkningsposter, tkr, löpande priser |
| **SCB table ID** | BalansKn (archived series, data through 2024; the continued series is `BalansKnN` under OE0107A, data through 2025) |
| **SCB subject area** | OE, Offentlig ekonomi |
| **API base URL** | `https://api.scb.se/OV0104/v1/doris/sv/ssd/OE/OE0107/OE0107G/BalansKn` |
| **Web browser URL** | `https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__OE__OE0107__OE0107G/BalansKn/` |
| **License** | Open data, free to use (SCB open license) |

#### What "debt" means
`debt_per_capita` is the municipality's **total borrowing (låneskuld)**: every interest-bearing loan, long- or short-term, per inhabitant. It is built from seven balance sheet posts, listed in `config.BORROWING_POSTS`:

| Post | Label | Note |
|------|-------|------|
| `081` | Långfristiga lån i banker och kreditinstitut, svenska kronor | |
| `082` | Långfristiga lån i banker och kreditinstitut, utländsk valuta | |
| `083` | Långfristiga skulder till koncernföretag | |
| `084` | Kontokredit, långfristig del, övriga långfristiga skulder | |
| `085` | Långfristig leasingskuld | |
| `136` | Långfristiga obligations- och förlagslån | Separate post from 2020; earlier years count as 0 because bonds sat in 081/084 |
| `090` | Kortfristiga skulder till kreditinstitut och kunder | Short-term borrowing, including loans due within twelve months |

Why not simply post `089` (Långfristiga skulder)? The SCB series shows two breaks in 089 over 2010-2024:

1. **Post 087 enters 089 in 2013.** 087 is *Långfristig skuld för avgifter samt offentliga bidrag*: connection fees and investment grants booked as deferred income. It is not borrowing, and it is reported only from 2013 (7.6 bn SEK nationally in 2013, 40.8 bn in 2024). Including it would shift municipalities with large grant-funded investments up the ranking from 2013 onward. Bjurholm is the clearest case: in 2024, about a third of its 089 was 087.
2. **Maturity reclassification.** From 2016 SCB separates the part of long-term loans due within twelve months (post 134), which is booked as short-term debt and leaves 089. A municipality whose loans happen to mature soon would look less indebted. Including post 090 makes the measure independent of maturity.

Total borrowing removes both breaks. It equals Kolada's KPI **N03145** (*Summa lån kommun exkl. vidareutlåning*) plus onlending (posts 088 and 135) plus bonds (post 136); this is checked for every municipality-year Kolada publishes (2019-2024) by `scripts/validate_against_kolada.py`.

**Onlending is not subtracted.** Kolada's N03145 subtracts loans the municipality passes on to its own companies (post 088). That would be the ideal concept, but SCB's 088 is reported inconsistently between municipalities and years (Section 5.1), so a net measure would import reporting noise. The index therefore uses gross borrowing and treats onlending as an interpretation caveat.

#### API query (exact, reproducible)
```json
POST https://api.scb.se/OV0104/v1/doris/sv/ssd/OE/OE0107/OE0107G/BalansKn
{
  "query": [
    {"code": "Region",          "selection": {"filter": "all",  "values": ["*"]}},
    {"code": "Balansraknposter","selection": {"filter": "item", "values": ["081","082","083","084","085","136","090","089","088","135"]}},
    {"code": "ContentsCode",    "selection": {"filter": "item", "values": ["OE0107E5"]}},
    {"code": "Tid",             "selection": {"filter": "item", "values": ["2010","2011","2012","2013","2014","2015","2016","2017","2018","2019","2020","2021","2022","2023","2024"]}}
  ],
  "response": {"format": "json"}
}
```
Posts 089, 088 and 135 are fetched for validation and documentation only. `ContentsCode = OE0107E5` is tkr, current prices.

`DataCleaner.clean_balance_sheet` matches posts by code and raises an error if a borrowing post is missing, or if a value is missing in a year after SCB introduced the post. It never falls back to other posts. See Section 7.4 for the correction history.

#### Transformation
```
debt_per_capita (SEK) = (sum of BORROWING_POSTS, tkr × 1000) / total_population
```
- Population denominator comes from Variable 4 (BefolkningNy, "tot" age group)
- Gotland (code 0980) is not adjusted: SCB reports Region Gotland's municipal part in the municipal tables and its regional part in the regional tables (Section 5.1)

#### Observed data range (2010-2024, all 290 municipalities)
| Statistic | Value |
|-----------|-------|
| Minimum | -28 SEK/capita (Partille, 2020; small negative balances are published by SCB). 109 municipality-years report exactly 0 |
| Maximum | 148,496 SEK/capita (Östersund, 2024) |
| Mean | 24,165 SEK/capita |
| Median | 17,751 SEK/capita |

Municipal borrowing has risen steeply over the period: the 2024 cross-sectional mean is 44,604 SEK/capita. Zero values are reported by SCB and are kept as is (see Section 5.1).

#### Fact-check benchmarks
| Check | Expected | Observed | Status |
|---|---|---|---|
| Stockholm (0180), 2023 | 80,000 SEK/capita (SCB BalansKn, borrowing posts) | **80,000** | OK |
| Sum of all 290 municipalities, 2021 | 485.8 billion SEK (SCB "Riket" row, borrowing posts) | **485.8 billion** | OK (automated in `tests/test_debt_data.py`) |
| Every municipality-year 2019-2024 vs Kolada N03145 + onlending + bonds | identical | **1,720 / 1,720** within 0.1% | OK (`scripts/validate_against_kolada.py`) |
| Post 089 per capita vs Kolada N03046, 2010-2024 | identical | **4,349 / 4,349** within 0.1% | OK |

---

### 2.3 Variable 2: Unemployment Rate (`unemployment`)

#### Source
| Field | Detail |
|-------|--------|
| **Data provider** | Arbetsförmedlingen (Swedish Public Employment Service) |
| **Distribution channel** | Kolada API (RKA, Rådet för kommunal analys) |
| **Kolada KPI ID** | **N03937** |
| **KPI full title** | Öppet arbetslösa av befolkningen, 18-65 år, andel (%) |
| **KPI description** | Openly registered unemployed persons aged 18-65, as a percentage of total population aged 18-65. Annual average of monthly figures. |
| **Kolada API base URL** | `https://api.kolada.se/v3/` (v2 was retired and returns HTTP 410) |
| **KPI metadata URL** | `https://api.kolada.se/v3/kpi/N03937` |
| **License** | Open data, free use (RKA/Kolada open license) |

#### API query (exact, reproducible)
```
GET https://api.kolada.se/v3/data/kpi/N03937/year/2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024
```

Kolada returns paginated JSON (max 5,000 records per page). All municipalities are returned in a single call. The pipeline follows `next_url` links to collect all records.

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
  "next_url": null
}
```
- `gender = "T"` selects the total (both sexes combined)
- `municipality` is the 4-digit SCB municipality code

#### Definition detail
- **Numerator:** Number of persons aged 18-65 registered as openly unemployed with Arbetsförmedlingen, monthly average over the calendar year
- **Denominator:** Total population aged 18-65 in the municipality (from SCB population register)
- **Scope:** Openly unemployed only, does NOT include persons in labour market programmes (åtgärder). This is a narrower definition than the AKU (Labour Force Survey) measure.

#### Why N03937, not other KPIs
During implementation, the following Kolada unemployment KPIs were evaluated and rejected:

| KPI | Title | Years available | Reason rejected |
|-----|-------|-----------------|-----------------|
| N00945 | (unrelated, parental leave KPI) | 2010-2015 | Wrong variable entirely |
| N00708 | Arbetslöshet, inrikes födda 20-64 | 2013-2014 only | Insufficient coverage |
| N03935 | Arbetslösa 18-24 år, andel (%) | 2010-2011, 2018-2019 | Insufficient coverage; youth-only |
| N03936 | Arbetslöshet 18-24, årsmedelvärde | 2010-2011 only | Insufficient coverage; youth-only |
| **N03937** | **Öppet arbetslösa 18-65 år, andel (%)** | **2010-2024, all 290** | **Selected** |

#### Why not SCB RAMS/BAS?
SCB's register-based labour market statistics (RAMS) was replaced by BAS in 2019. This creates a structural break making pre-2019 and post-2019 data not directly comparable. Arbetsförmedlingen series N03937 uses a consistent definition throughout 2010-2024.

#### Observed data range (2010-2024, all 290 municipalities)
| Statistic | Value |
|-----------|-------|
| Minimum | 0.94% |
| Maximum | 7.50% |
| Mean | 3.07% |
| Median | 2.97% |

#### Fact-check benchmarks
| Municipality | Year | Expected (%) | Source |
|---|---|---|---|
| Stockholm (0180) | 2023 | 2-4% (Arbetsförmedlingen regional statistics) | Verified: **2.91%** OK |
| Danderyd (0162) | 2023 | < 2% (affluent suburb, full employment) | Verified: **1.53%** OK |
| National rate (Kolada, Riket) | 2023 | 2.54% | Population-weighted mean of the 290 municipalities: **2.52%** OK |
| Unweighted mean of 290 municipalities | 2023 | below the national rate, because small municipalities have lower unemployment | **2.20%** OK |

**Note on national mean vs. AKU:** The AKU (Labour Force Survey) publishes a broader unemployment rate of approximately 8-9% for 2023. This is not comparable to N03937. The AKU uses ILO definition (includes inactive job-seekers, persons in programmes, etc.) and covers all ages 15-74. N03937 is restricted to those actively registered as openly unemployed aged 18-65, producing a structurally lower figure. For relative municipal comparison within the same metric, this is valid.

---

### 2.4 Variable 3: Dependency Ratio (`dependency_ratio`)

#### Source
| Field | Detail |
|-------|--------|
| **Data provider** | Statistics Sweden (SCB) |
| **Series name** | Folkmängden efter region, civilstånd, ålder och kön |
| **SCB table ID** | BefolkningNy |
| **SCB subject area** | BE, Befolkning |
| **API base URL** | `https://api.scb.se/OV0104/v1/doris/sv/ssd/BE/BE0101/BE0101A/BefolkningNy` |
| **Web browser URL** | `https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__BE__BE0101__BE0101A/BefolkningNy/` |
| **Available period** | 1968 to 2024 |
| **License** | Open data, free to use |

#### API query strategy (batched, exact)
SCB enforces a 150,000-cell limit per request. With ~312 region codes × 15 years × 1 content code = 4,680 cells per age, a maximum of ~32 ages per request is safe. The pipeline uses batch_size = 30.

**Each batch request (example, ages 0-29):**
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
Total batches: 4 (ages 0-29, 30-59, 60-89, 90-100+). Results concatenated into a single DataFrame.

**Note:** `Civilstand` (marital status) and `Kon` (sex) are intentionally excluded from the query. This returns population summed across all marital statuses and both sexes for each single-year age, which is what is needed for dependency ratio. Including them would multiply the cell count by ~8 and exceed the SCB limit.

#### Variable codes
| Code | Label |
|------|-------|
| ContentsCode = `BE0101N1` | Folkmängd (population count) |
| Alder | Single-year ages "0", "1", ..., "99", "100+" |

#### Calculation
```
young   = sum(population, ages 0-19)
working = sum(population, ages 20-64)
old     = sum(population, ages 65-100+)

dependency_ratio = (young + old) / working
```

- A value of 0.857 means: for every 100 working-age persons, there are 85.7 dependents (children + elderly)
- Only valid municipality codes (4-digit, present in config.MUNICIPALITIES) are retained

#### Observed data range (2010-2024, all 290 municipalities)
| Statistic | Value |
|-----------|-------|
| Minimum | 0.508 (urban high-working-age municipality) |
| Maximum | 1.241 (small ageing rural municipality) |
| Mean | 0.857 |
| Median | 0.860 |

#### Fact-check benchmarks
- National dependency ratio in Sweden (Statistics Sweden): approximately 0.80-0.90 for 2015-2023 OK
- Urban municipalities (Stockholm, Göteborg) tend toward 0.55-0.65 (younger population skew) OK
- Small inland municipalities (Dorotea, Bjurholm) tend toward 1.0-1.3 (ageing demographic) OK

---

### 2.5 Variable 4: Population Growth, 5-year rolling (`population_growth`)

#### Source
| Field | Detail |
|-------|--------|
| **Data provider** | Statistics Sweden (SCB) |
| **Series name** | Same as Variable 3, BefolkningNy |
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

#### Observed data range (2010-2024, all 290 municipalities)
| Statistic | Value |
|-----------|-------|
| Minimum | -10.76% (severe depopulation) |
| Maximum | +21.16% (strong growth municipality) |
| Mean | +2.02% |
| Median | +1.88% |

#### Fact-check benchmarks
- Dorotea (2425, remote inland municipality), 2023: **-8.92%** 5-year decline OK (consistent with known depopulation trend)
- Stockholm (0180), 2023: **+2.78%** OK (moderate growth; slower than pre-pandemic)
- Swedish national population grew ~5% between 2019 and 2024 (net immigration + natural increase), individual municipality dispersion around this is expected OK

---

### 2.6 Variable 5: Tax Base Strength (`tax_base_relative`)

#### Source
| Field | Detail |
|-------|--------|
| **Data provider** | Statistics Sweden (SCB) |
| **Series name** | Skatteunderlag och skattekraft efter region och tabellinnehåll |
| **SCB table ID** | SkatteKraft |
| **SCB subject area** | OE, Offentlig ekonomi |
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

**Important time lag:** The tax base for year T is based on incomes declared in year T-1 and reported to municipalities for T+1 budget planning purposes. In practice, "skattekraft 2024" reflects approximately 2022 incomes. This is a systemic property of Swedish municipal finance and affects all municipalities equally.

#### Observed data range (2010-2024, all 290 municipalities)
| Statistic | Value |
|-----------|-------|
| Minimum | 72% (significantly below national average) |
| Maximum | 191% (nearly double national average) |
| Mean | 93.1% (slightly below 100 due to population-weighting) |
| Median | 90% |

#### Fact-check benchmarks
| Municipality | Year | Expected (%) | Verified |
|---|---|---|---|
| Danderyd (0162) | 2023 | > 150% (highest in Sweden historically) | **184%** OK |
| Stockholm (0180) | 2023 | ~125-135% | **131%** OK |
| National median | 2023 | ~88-92% (majority below 100 due to skewed distribution) | **89%** OK |

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
| **Interpretation** | Very high rate (> 22-23%) may indicate the municipality has approached its practical taxing capacity |

**Note:** The original table path `Komskatter` is deprecated. Current active path is `Kommunalskatter2000`.

---

### 2.9 Supplementary Variable 8: Equity Ratio (Soliditet)

| Field | Detail |
|-------|--------|
| **Purpose** | Deep-dive analysis; supplementary context |
| **Calculation** | Eget kapital vid årets slut (post 075) / Tillgångar (post 070) × 100 |
| **Source** | SCB BalansKn, posts 075 and 070. Identical to Kolada N03106 *Soliditet kommun* for all 869 municipality-years checked (2012, 2018, 2024). Post 090 is short-term borrowing, not equity. |
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
- **Rate limiting:** No hard limit; be polite, pipeline uses 0.5s delay between requests
- **Region filter for all municipalities:** `{"code": "Region", "selection": {"filter": "all", "values": ["*"]}}`

**Deprecated filter (do not use):** `{"filter": "vs:RegionKommun07", "values": []}`, returns HTTP 400

#### Kolada API
- **Base URL:** `https://api.kolada.se/v3/` (v2 was retired and returns HTTP 410)
- **Method:** HTTP GET
- **Response format:** JSON with `values` array and `next_url` pagination
- **Page size:** 5,000 records per page; follow `next_url` for subsequent pages
- **Authentication:** None required (open API)
- **KPI metadata:** `GET /v3/kpi/<KPI_ID>`
- **Data fetch:** `GET /v3/data/kpi/<KPI_ID>/year/<Y1>,<Y2>,...`
- **Gender field:** Use `"gender": "T"` for total (both sexes combined)

---

## 3. Model Specification

### 3.1 KRI formula

```
KRI(i,t) = w1 × z(debt_per_capita(i,t))
          + w2 × z(unemployment(i,t))
          + w3 × z(dependency_ratio(i,t))
          + w4 × z(-population_growth(i,t))
          + w5 × z(-tax_base_relative(i,t))
```

Where:
- `i` = municipality index (1-290)
- `t` = year (2010-2024)
- `z(x)` = cross-sectional z-score: `(x - mean_t) / std_t`, where mean and std are computed across all 290 municipalities within year t
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
z(x_i,t) = (x_i,t - mean(x_t)) / std(x_t)
```

- Mean and standard deviation are computed across all 290 municipalities **within** the same year
- This makes rankings relative (a municipality is "high risk" relative to its peers that year)
- The index is NOT comparable in absolute terms across years, only rankings are interpretable across time

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

### 3.5 Weight sensitivity

The weights in §3.2 are argued from public-finance theory rather than estimated from data. This is the standard and fair criticism of any composite indicator, and the dashboard answers it with a measurement rather than an argument, following the OECD/JRC *Handbook on Constructing Composite Indicators*: treat the weights as an uncertain input and propagate that uncertainty to the output.

#### Method

Each weight is drawn uniformly from `[w - δ, w + δ]` with **δ = 0.05**, and the vector is renormalised to sum to 1. The renormalisation is what makes the draw honest: weights must still sum to one, so raising the debt weight necessarily lowers something else, which is exactly the trade-off a critic is pointing at. Draws where renormalisation pushes a weight beyond δ are rejected (≈16% of draws), so the claim *no weight ever moves more than five percentage points* holds exactly rather than approximately.

The index is recomputed **N = 1000** times. Quartile cut points are recomputed *inside each draw*: holding them fixed at the published p25/p75 would measure score movement only, and the question is class movement. This reproduces exactly what `index_builder.classify()` would have done had those been the real weights.

A uniform distribution is used rather than a Dirichlet because it can be explained in a caption, and because a reader who disagrees with δ can reason about what a different δ would imply. The generator is seeded from `config.SENSITIVITY["seed"]`, so the published band is reproducible, a band that shifted between pipeline runs would undermine trust in the whole dashboard.

For each municipality and year the analysis records the 5th, 50th and 95th percentile of rank, the share of draws in which the municipality keeps its **published** risk class (`class_stability`), and the most frequent class across draws (`modal_class`). A municipality is labelled **robust** when `class_stability ≥ 0.90` and **gränsfall** (boundary case) otherwise. *Gränsfall* means the municipality sits near a boundary between two risk classes, not that its classification is wrong.

#### Results (2024, n = 290)

| Measure | Value |
|---|---|
| Robust (class holds in ≥90% of draws) | 235 / 290 (81%) |
| Gränsfall (boundary-fragile) | 55 / 290 (19%) |
| **Modal class differs from published class** | **2 / 290** |
| Median 90% rank interval | 24 places |

The third row is the substantive finding: across 290 municipalities, the class that wins the vote differs from the published class only twice, and both sit exactly on a quartile boundary: Kristinehamn at rank 73 (the last Hög) and Gnesta at rank 218 (the first Låg). **The sensitivity analysis corroborates the index rather than undermining it.**

Fragility concentrates where theory predicts. The Medel class has the widest median band (30.5 places, against 18 for Hög and 17 for Låg) because a mid-table municipality has two boundaries to fall across, while the extremes are pinned by the data rather than by the weights. Kiruna is the clearest individual case: it has the second-highest borrowing in Sweden and is published at rank 205 (Medel), but with a plausible range of 160-242 and a class that holds in only 70% of draws. Its debt pulls it up while its low unemployment and strong tax base pull it down, so the balance between those weights decides its class.

#### Sensitivity to the choice of δ

δ = 0.05 is itself a judgement call, so the result is reported at three values:

| δ | Robust | Gränsfall | Modal ≠ published | Median band |
|---|---|---|---|---|
| 0.03 | 254 / 290 | 36 | 2 | 14 places |
| **0.05** (used) | **235 / 290** | **55** | **2** | **24 places** |
| 0.10 | 198 / 290 | 92 | 3 | 49 places |

The number of boundary cases grows with δ, as it must. The conclusion does not: the published class remains the most frequent class for at least 287 of 290 municipalities at all three values.

#### Rejected alternative: PCA weights

The obvious data-driven alternative is to let principal component analysis determine the weights. It was tested on all fifteen years and rejected on three grounds.

**1. PC1 loads negatively on debt.** The first principal component's loading on `z_debt` is close to zero in 2010 (+0.01) and negative in every year from 2011, reaching -0.32 by 2024; unemployment also turns negative from 2020. An index built on PC1 would rank Sweden's most indebted municipalities among its safest. Concretely (2024): the 29 most indebted municipalities sit at the 69th risk percentile under the current weights and at the **20th** under PCA. Eskilstuna, borrowing 120,772 SEK per inhabitant, is rank 6 (Hög risk) today and falls to the 21st risk percentile, well inside low risk, under PCA.

The reason is visible in the correlation matrix: `z_debt` correlates negatively with dependency (-0.26), population decline (-0.25) and tax base (-0.10) in 2024. Growing, affluent suburbs borrow to build infrastructure; shrinking rural municipalities carry little debt but weak demographics. **PC1 is not a risk factor, it is an urban-growth versus rural-decline axis.**

**2. No dominant component.** PC1 carries only 40-44% of variance in every year (42.0% in 2024, with PC2 at 24.0%); two components pass the Kaiser criterion in all fifteen years. PCA-based weighting is defensible when one component clearly dominates (conventionally ≳70%). Compressing a genuinely two-dimensional structure onto one axis would discard 58% of the variance as noise.

**3. No comparability across time.** PCA weights are re-estimated per year and move enormously over the period: the debt weight between 0.006 (2010) and 0.160 (2023), the unemployment weight between 0.198 (2010) and 0.009 (2023). A municipality's score would then change because the weights moved, not because its finances did, which destroys the 2010-2024 trend analysis that is the dashboard's core value.

A sign-constrained repair was also tested. Non-negative PC1 (‖w‖₂ = 1, w ≥ 0, projected power iteration) assigns **zero weight to debt in fourteen of fifteen years** (0.01 in 2010), and zero or near-zero weight (at most 0.013) to unemployment from 2020 onward. Constraining PCA to be theory-consistent makes it delete the two variables the index exists to measure.

One legitimate observation does come out of the PCA: dependency, population growth and tax base intercorrelate at 0.40-0.60 and partly measure a single construct, demographic and tax capacity, which together carries 0.50 of the weight against debt's 0.25. A defensible structural revision would group the indicators into theoretical pillars, not let an eigenvector choose the weights.

#### Scope and limitations

The band measures sensitivity to **one** subjective choice. It does not make the index objective; it makes the index's dependence on the weighting visible and measurable, which is a different and more defensible claim. Specifically excluded:

- **Data uncertainty.** Measurement error in SCB debt figures and interpolated series is not modelled.
- **Indicator-set uncertainty.** Adding or removing a variable would move results substantially more than reweighting the current five.
- **Dependence between weights.** Draws are independent. Renormalisation captures the sum-to-one constraint but not a prior belief that, say, debt should always outweigh population.

No published `kri_score`, `rank` or `risk_class` is altered by this analysis. It is stored in a separate artefact (`data/processed/kri_sensitivity.parquet`) and joined at display time; deleting that file restores the dashboard exactly as it was before the layer existed.

#### Reproduction

```bash
python scripts/run_sensitivity.py
```

Parameters live in `src/config.py` under `SENSITIVITY`. Implementation: `src/sensitivity.py`. Tests: `tests/test_sensitivity.py`.

---

## 4. Evaluation and Validation

### 4.1 Sanity checks (verified against real data)

| Check | Expected | Verified |
|-------|----------|---------|
| Danderyd (0162): tax base | > 150% (historically highest in Sweden) | **184% (2023)** OK |
| Danderyd (0162): unemployment | < 2% | **1.53% (2023)** OK |
| Stockholm (0180): borrowing/capita | 80,000 SEK (SCB BalansKn, borrowing posts) | **80,000 SEK (2023)** OK |
| National borrowing | 485.8 billion SEK (SCB Riket row, 2021) | **485.8 billion SEK** OK |
| Borrowing vs Kolada N03145 + onlending + bonds | identical, 2019-2024 | **1,720 / 1,720** OK |
| Stockholm (0180): unemployment | 2-4% | **2.91% (2023)** OK |
| Dorotea (2425): pop. growth | Strongly negative | **-8.92% (2023)** OK |
| National dep. ratio mean | ~0.75-0.90 | **0.857** OK |
| National unemployment rate | 2.54% (Kolada N03937, Riket, 2023) | **2.52%** population-weighted (unweighted mean of 290: 2.20%) OK |

### 4.2 Temporal stability
- KRI rankings should be relatively stable between adjacent years (correlation > 0.85 expected)
- Large rank jumps (> 50 positions) should be investigated and documented
- The pandemic (2020-2021) caused genuine unemployment spikes in Stockholm belt, Strömstad, Göteborg: these are verified real events, not data errors

### 4.3 Data audit results (automated verification)
A full automated audit was run on `data/processed/kri_base_data.parquet`:
- **0 failures** across 48 checks
- **4 warnings**, all real features of the data: high-debt/high-tax-base co-occurrence (56 municipality-years), single-year jumps in debt (89 jumps > 3 SD, mostly large borrowing years in 2023-2024 when the global SD understates later, larger levels), unemployment (COVID-2020 spike) and dependency ratio (small-municipality ageing)
- Zero NaN values in all 5 core variables across all 4,350 rows (290 municipalities × 15 years)
- No duplicate (municipality, year) pairs
- All values within expected real-world ranges

---

## 5. Bias, Limitations, and Interpretation Warnings

### 5.1 Known biases

**Size bias:** Municipalities with fewer than 5,000 inhabitants show more volatile single-year indicators. A factory closure can cause a +3% unemployment spike in one year. Mitigation: 5-year rolling average for population growth. Debt and tax base are less affected. Residual volatility is documented.

**Time lag in tax base:** Tax base for year T reflects incomes from approximately T-2. Rapid economic shocks (e.g., a major employer's sudden departure) appear in the tax base data with a 2-year delay.

**Registration bias in unemployment (N03937):** Persons who are unemployed but not registered with Arbetsförmedlingen are not counted. This particularly affects municipalities with large commuter flows or high self-employment rates. The bias is consistent across municipalities and time, preserving validity for relative comparison.

**Gotland special case:** Region Gotland is both a municipality and a region. SCB already separates the two: the municipal tables (BalansKn, code 0980) hold the municipal part, and the regional table (BalansKnLTing) holds the regional part. In 2023 the municipal part was 65% of the combined total assets (4,462 of 6,865 mnkr) and of combined long-term debt. Kolada's official municipal figure for Gotland (N03046, 10,621 SEK/capita in 2023) equals SCB's 0980 value unadjusted. Earlier versions multiplied Gotland's debt by 0.65 on top of this split, understating it by 35%; the pipeline now uses SCB's municipal figure as published, and Gotland stays flagged only as a comparability note.

**Onlending to municipal companies (posts 088 and 135):** Many municipalities borrow on behalf of their own companies (housing, energy, water) and lend the money onward. These loans are part of the municipality's borrowing, although the companies service them. Nationally, onlending was 41% of long-term liabilities in 2021 (176 of 425 billion SEK). The ideal debt concept would subtract it, as Kolada's N03145 does, but SCB's onlending post is reported inconsistently:

- Stockholm reported no onlending (088 = 0) until 2019 and 11.6 bn SEK in 2023, yet lent 33-97 bn SEK to its own companies throughout via a group cash pool, booked as short-term receivables (post 052). In 2024 it tagged 67.5 bn as onlending with no matching change in its borrowing. A net measure would show Stockholm's debt falling from 62,779 to 4,788 SEK/capita in one year.
- Eskilstuna reported 088 = 0 in 2015 while holding 2.8 bn SEK of long-term receivables from its companies (post 034); Malmö reported at most 0.2 bn of onlending in 2011-2015 against 1.9-8.1 bn of such receivables.
- Across municipalities, onlending (088) and receivables from own companies (034) correlate only 0.48 in 2011 and 0.59 in 2024.

The index therefore uses gross borrowing. Subtracting onlending as reported would change the ranking substantially (rank correlation with the published index 0.90-0.94 over 2011-2024, 31-47 class changes per year), and much of that change would be reporting noise. Read the debt contribution of municipalities with large municipal-company groups, such as the metropolitan municipalities, with this in mind.

**Zero and near-zero borrowing:** SCB reports zero borrowing for 109 municipality-years (37 municipalities; 58 of the cases fall in 2010-2015) and below 1,000 SEK/capita for 358. Including short-term borrowing (post 090) removed 47 false zeros that post 089 alone produced, for municipalities whose only loans were short-term. The remaining zeros are genuine: those municipalities have no loans in the municipal entity, although their companies may borrow. Two small negative values (Katrineholm 2015, Partille 2020) are kept as published.

**High-debt / high-tax-base co-occurrence:** Growth municipalities (e.g., Nykvarn) and municipalities with large one-off investments (e.g., Kiruna's city relocation) borrow heavily to fund infrastructure while simultaneously having high per-capita incomes. This produces a counter-intuitive combination of high debt and high tax base. The KRI formula correctly captures both dimensions, but the risk profile of these municipalities is structurally different from distressed rural municipalities with high debt.

### 5.2 Model limitations

- Weights (0.25/0.25/0.20/0.15/0.15) are normatively set based on economic reasoning, not empirically derived from default rates or credit events
- The index measures structural vulnerability, not political capacity to manage challenges
- Z-score normalization is purely relative: the index always identifies "high risk" municipalities even if all municipalities improve in absolute terms. Use trend analysis for absolute assessment.
- The 5-year population growth lag means 2010-2014 values are computed from 2005-2009 baseline data. This is correct methodology but should be noted when interpreting early-period results.

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
Every municipality is checked for complete data across all 5 core variables for all 15 years (2010-2024). As of the last pipeline run, all 290 municipalities have zero missing values.

### 6.2 Strategies (applied if future data gaps arise)

| Situation | Strategy |
|-----------|----------|
| Single missing year (1-2 years) | Linear interpolation between adjacent years |
| Missing at start of series (2010-2011) | Forward extrapolation from first available year (limit: 2 years) |
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
| N00945 | (parental leave KPI, mislabelled in early docs) | 2010-2015 | **Rejected**: wrong variable |
| N00708 | Arbetslöshet, inrikes födda 20-64 år | 2013-2014 only | **Rejected**: 2 years only |
| N03935 | Arbetslösa av befolkningen, 18-24 år | 2010-2011, 2018-2019 | **Rejected**: youth-only, non-continuous |
| N03936 | Arbetslöshet 18-24 år, årsmedelvärde | 2010-2011 only | **Rejected**: youth-only, 2 years |
| N01961 | Invånare 20-64 år, andel (%) | 2010-2011 only | **Rejected**: not unemployment; used as proxy candidate for dependency ratio before SCB solution found |
| **N03937** | **Öppet arbetslösa 18-65 år, andel (%)** | **2010-2024 (all 15 yrs)** | **Selected** |

### 7.2 Dependency Ratio Data Source Change

Originally planned: compute dependency ratio from Kolada KPI N01961 (working-age population share). This KPI only had data for 2010-2011, making it unusable.

**Resolution:** Fetch single-year age populations directly from SCB BefolkningNy using batched API requests (ages 0-100+ in batches of 30). This provides complete 2010-2024 data and is more accurate than Kolada's pre-aggregated figure. The SCB source data is the underlying source Kolada itself uses.

### 7.3 SCB API Path Corrections

| Original path (from documentation) | Correct active path | Error |
|-------------------------------------|---------------------|-------|
| `BalansKnN` (OE0107G) | `BalansKn` (OE0107G, archived, data through 2024) | HTTP 404 at the time. SCB has since published a continued `BalansKnN` under OE0107A with data through 2025; the pipeline still reads the archived table |
| `Komskatter` | `Kommunalskatter2000` | HTTP 404 (deprecated) |
| Region filter: `vs:RegionKommun07` | `filter: "all", values: ["*"]` | HTTP 400 |
| Kolada `https://api.kolada.se/v2/` | `https://api.kolada.se/v3/` | HTTP 410 (v2 retired); v3 returns identical values, paginated with `next_url` |
| ResultKn post `070` | ResultKn post `120` | Wrong variable (070 = nettokostnad, 120 = årets resultat) |

### 7.4 Debt Variable Correction (October 2026)

**Problem:** Earlier versions fetched three BalansKn posts (`050`, `089`, `100`) and tried to keep `089` by matching the label "Långfristiga skulder". SCB returns post *codes*, not labels, so the filter matched nothing and the fallback summed all three posts. In addition, the code comment described `050` as total assets; according to SCB's table metadata `050` is *Diverse kortfristiga fordringar* (total assets is `070`), and `100` is the balance sheet total. The resulting "debt" was mostly the size of each balance sheet: the national sum for 2021 was 1,862 billion SEK against SCB's published 425 billion of long-term debt.

**Fix:** Only posts `089` and `088` are fetched; the cleaner filters on code `089` and raises an error if it is missing. `tests/test_debt_data.py` checks the national total against SCB's published figure, that the municipal sum equals SCB's "Riket" row, and that the processed per-capita values reconstruct the national total.

**Impact (2024):** median debt fell from 150,226 to 37,382 SEK/capita. The KRI ranking was broadly preserved (Spearman rank correlation old vs new 0.966) because balance sheet size per capita is correlated with debt, but 32 of 290 municipalities changed risk class. Stockholm moved from rank 126 (Medel) to 251 (Låg); Kiruna from 67 (Hög) to 196 (Medel).

**Second step, debt as total borrowing (October 2026):** a review of the post 089 series against Kolada and SCB's own post structure found three remaining validity problems, all fixed:

1. *Definition.* Post 089 includes post 087 (deferred connection fees and grants), which is not borrowing and enters only from 2013, and it excludes loans reclassified as short-term from 2016. Debt is now total borrowing (posts 081-085, 136, 090; Section 2.2), equal to Kolada N03145 plus onlending and bonds for every municipality-year Kolada publishes.
2. *Gotland.* The 0.65 factor rescaled a figure SCB had already split between municipality and region (Section 5.1). It was removed.
3. *Onlending.* Subtracting onlending was evaluated and rejected because SCB's 088 is reported inconsistently (Section 5.1).

Impact against the post 089 version: Spearman rank correlation 0.988-0.996 per year, 10-20 class changes per year. Bjurholm's debt fell from 135,220 to 91,875 SEK/capita (a third of its 089 was grants), Östersund's rose from 124,377 to 148,496 and it moved from rank 83 (Medel) to 50 (Hög). Gotland's rose from 11,891 to 14,065 without changing its rank (247).

The same review moved the unemployment fetch from Kolada's retired v2 API to v3 (identical values) and added `scripts/validate_against_kolada.py`, which checks unemployment, borrowing and post 089 against Kolada for every municipality-year. All numbers in this document were regenerated from the corrected data.

### 7.5 Final Data Quality Summary

| Variable | Column | Coverage | Zero missing | Source |
|----------|--------|----------|--------------|--------|
| Borrowing per capita | `debt_per_capita` | 100% | OK | SCB BalansKn, posts 081-085, 090, 136 |
| Unemployment rate | `unemployment` | 100% | OK | Kolada N03937 |
| Dependency ratio | `dependency_ratio` | 100% | OK | SCB BefolkningNy, ages 0-100+ |
| Population growth (5-yr) | `population_growth` | 100% | OK | SCB BefolkningNy, "tot" |
| Tax base relative | `tax_base_relative` | 100% | OK | SCB SkatteKraft, OE0101B0 |

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
| `data/cache/balance_sheet.parquet` | SCB BalansKn, posts 081-085, 090, 136 (borrowing) and 088, 089, 135 (reference), all regions, 2010-2024 | 43,650 |
| `data/cache/population.parquet` | SCB BefolkningNy, total population, all municipalities, 2005-2024 | 49,920 |
| `data/cache/tax_base.parquet` | SCB SkatteKraft, OE0101B0, all municipalities, 2010-2024 | 4,680 |
| `data/cache/income_statement.parquet` | SCB ResultKn, post 120, all municipalities, 2010-2024 | 4,365 |
| `data/cache/tax_rate.parquet` | SCB Kommunalskatter2000, OE0101D2, all municipalities, 2010-2024 | 4,680 |
| `data/cache/population_by_age.parquet` | SCB BefolkningNy, ages 0-100+, all municipalities, 2010-2024 | 472,680 |
| `data/cache/kolada_unemployment.parquet` | Kolada N03937 (API v3), all municipalities, 2010-2024 | 54,840 |

### 8.4 Versioning
- All raw API responses saved in `data/raw/` with timestamp suffixes
- Parquet files are reproducible: re-running `--no-cache` produces byte-identical output (API data does not change for historical years)
- `requirements.txt` pins all package versions for full environment reproducibility

---

## 9. KRI Computation: Detailed Mechanics and Design Rationale

This section documents the full four-step computation pipeline implemented in `src/index_builder.py`. It explains the purpose of each step, the mathematical operations involved, and why each design decision was made. All numerical examples use real data from `data/processed/kri_results.parquet` for the year 2024.

---

### 9.1 Step 1: Cross-Sectional Z-Score Normalization

#### The problem normalization solves

The five input variables are measured in completely different units:

| Variable | Unit | 2024 cross-sectional mean | 2024 cross-sectional std |
|----------|------|---------------------------|--------------------------|
| `debt_per_capita` | SEK per person | 44,604 SEK | 31,426 SEK |
| `unemployment` | Percent (%) | 2.53% | 0.70% |
| `dependency_ratio` | Ratio (dimensionless) | 0.91 | 0.12 |
| `population_growth` | Percent (%) | 0.33% | 3.99% |
| `tax_base_relative` | % of national avg | 91.73% | 13.23% |

Without normalization, direct addition is meaningless. Adding 44,604 SEK debt to a 2.53% unemployment rate produces a number dominated entirely by the debt variable: not because debt is more important, but simply because it is expressed in a larger-magnitude unit. Normalization removes the unit entirely and expresses each observation in standard deviations from the cross-sectional mean.

#### The formula

```
z(x_i,t) = (x_i,t - mean(x_t)) / std(x_t)
```

Where:
- `x_i,t` = the raw value for municipality `i` in year `t`
- `mean(x_t)` = the arithmetic mean across all 290 municipalities in year `t`
- `std(x_t)` = the sample standard deviation (ddof=1) across all 290 municipalities in year `t`
- Missing values are excluded from the computation of mean and std

The result has three properties:
1. **Mean = 0**: The average municipality always has a z-score of exactly 0
2. **Standard deviation = 1**: One unit of z-score = one standard deviation of dispersion across municipalities
3. **Comparability**: A z-score of +2.0 means the same thing regardless of which variable it applies to, the municipality is 2 standard deviations above the cross-sectional mean

#### Why cross-sectional (within a year), not longitudinal (across years)?

The alternative would be to compute the mean and std across all years combined. This is rejected for two reasons:

1. **Structural trends inflate longitudinal comparisons.** Municipal debt has risen substantially in nominal terms since 2010. A longitudinal normalization would make 2024 municipalities appear high-risk relative to 2010 simply because of inflation and long-term investment cycles, not structural vulnerability.

2. **The index measures relative standing, not absolute level.** The relevant question is: "Is this municipality more vulnerable than its peers *this year*?" Cross-sectional normalization answers this directly.

#### Verified properties (2024)

| Variable | Z-score mean (2024) | Z-score std (2024) |
|----------|---------------------|---------------------|
| `z_debt` | -0.0000 | 1.0000 |
| `z_unemployment` | 0.0000 | 1.0000 |
| `z_dependency` | 0.0000 | 1.0000 |
| `z_population` | -0.0000 | 1.0000 |
| `z_tax_base` | -0.0000 | 1.0000 |

These are validated automatically each time `KRIBuilder.build()` runs.

---

### 9.2 Step 2: Direction Correction

#### The problem direction correction solves

After normalization, a z-score of +2.0 means "this municipality is 2 standard deviations above the mean." But whether that is good or bad depends on the variable:

| Variable | High raw value -> | Interpretation |
|----------|-----------------|----------------|
| `debt_per_capita` | High debt | **Higher risk**, keep sign |
| `unemployment` | High unemployment | **Higher risk**, keep sign |
| `dependency_ratio` | High ratio | **Higher risk**, keep sign |
| `population_growth` | Growing population | **Lower risk**, invert sign |
| `tax_base_relative` | Strong tax base | **Lower risk**, invert sign |

Without direction correction, high population growth would *increase* the KRI score, making a thriving growing municipality appear more risky than a depopulating one. This is the opposite of the intended interpretation.

#### The correction

```python
# Variables where high = low risk: multiply z-score by -1
if not VARIABLE_DIRECTION[key]:
    z_score = z_score * -1
```

After inversion:
- A municipality with **high population growth** gets a **negative** z-score contribution (reduces KRI = reduces apparent risk)
- A municipality with **declining population** gets a **positive** z-score contribution (increases KRI = increases apparent risk)
- A municipality with a **strong tax base** (high % of national average) gets a **negative** contribution
- A municipality with a **weak tax base** gets a **positive** contribution

This ensures the KRI formula is monotone: **higher KRI = higher structural risk**, without exception.

#### Concrete example: Knivsta (0330) in 2024

Knivsta is a fast-growing commuter municipality north of Uppsala.

| Variable | Raw value | Direction | Z-score (before correction) | Z-score (after correction) |
|----------|-----------|-----------|------------------------------|----------------------------|
| `debt_per_capita` | 74,646 SEK | High = risk | +0.956 | +0.956 |
| `unemployment` | 2.06% | High = risk | -0.674 | -0.674 |
| `dependency_ratio` | 0.746 | High = risk | -1.379 | -1.379 |
| `population_growth` | +12.52% | **High = low risk** | +3.057 | **-3.057** (fast growth is far above the mean; inversion turns it into a risk-reducing score) |
| `tax_base_relative` | 109.0% | **High = low risk** | +1.305 | **-1.305** (strong tax base is above the mean; inversion turns it into a risk-reducing score) |

Knivsta's fast growth and above-average tax base strongly reduce its KRI score. Its rank is 279 out of 290 (one of the lowest-risk municipalities), despite carrying above-average debt.

#### Concrete example: Dorotea (2425) in 2024

Dorotea is a remote inland municipality with severe depopulation.

| Variable | Raw value | Direction | Z-score (before correction) | Z-score (after correction) |
|----------|-----------|-----------|------------------------------|----------------------------|
| `debt_per_capita` | 42,695 SEK | High = risk | -0.061 | -0.061 |
| `unemployment` | 2.37% | High = risk | -0.222 | -0.222 |
| `dependency_ratio` | 1.142 | High = risk | +2.030 | +2.030 |
| `population_growth` | -10.07% | **High = low risk** | -2.610 | **+2.610** (decline is far below the mean; inversion turns it into a risk-raising score) |
| `tax_base_relative` | 83.0% | **High = low risk** | -0.660 | **+0.660** (weak tax base is below the mean; inversion turns it into a risk-raising score) |

Dorotea's debt and unemployment are close to the national average, so its risk comes almost entirely from demography and tax base: three direction-corrected z-scores are strongly positive. The result: KRI = +0.826, rank 12 (Hög risk) in 2024.

---

### 9.3 Step 3: Weighted Summation

#### Purpose of weighting

After normalization and direction correction, all five z-scores are on the same scale and all point in the same direction (higher = higher risk). They could be averaged equally, giving each variable a weight of 0.20. The KRI instead uses unequal weights that reflect the relative importance of each risk dimension in public finance theory.

#### Weights and rationale

| Variable | Weight | Financial rationale |
|----------|--------|---------------------|
| `debt_per_capita` | **0.25** | Borrowing is the most direct measure of solvency pressure. High debt directly constrains future budget flexibility and signals past structural deficits. It is the single strongest short-term insolvency signal in municipal finance. |
| `unemployment` | **0.25** | Unemployment simultaneously erodes the municipal tax base (fewer employed residents = less income tax revenue) and increases demand for social services (welfare payments, placement programs). The double impact justifies equal weighting with debt. |
| `dependency_ratio` | **0.20** | A high share of dependents (children + elderly) relative to the working-age population creates long-term structural cost pressure. It operates more slowly than debt or unemployment but has a more persistent effect on expenditure patterns. |
| `population_growth` | **0.15** | Population trajectory determines long-term fiscal capacity. A declining population signals future revenue contraction. Weighted lower because it operates on a very long time horizon and is partially captured by the dependency ratio. |
| `tax_base_relative` | **0.15** | The tax base measures the municipality's revenue capacity relative to peers. Weighted lower because it is partially correlated with unemployment and population variables (poor municipalities tend to have low tax bases), reducing its marginal information contribution. |
| **Total** | **1.00** | The weights sum exactly to 1.0 (verified by assertion on module load). |

#### The formula

```
contribution_k = weight_k × z_corrected_k

KRI(i,t) = sum(contribution_k for all k in {debt, unemployment, dependency, population, tax_base})
         = 0.25 × z_debt + 0.25 × z_unemployment + 0.20 × z_dependency
           + 0.15 × z_population_corrected + 0.15 × z_tax_base_corrected
```

Each `contribution_k` column is stored in the output dataset, enabling decomposition analysis (which variable drives each municipality's risk score).

#### Full worked example: Stockholm (0180) in 2024

Stockholm has a mixed risk profile: above-average debt and unemployment, but an exceptionally strong tax base and young demographic.

| Variable | Raw | Z-score | Direction correction | Contribution |
|----------|-----|---------|---------------------|--------------|
| debt_per_capita | 88,917 SEK | +1.410 | kept | 0.25 × 1.410 = **+0.353** |
| unemployment | 3.46% | +1.324 | kept | 0.25 × 1.324 = **+0.331** |
| dependency_ratio | 0.595 | -2.681 | kept | 0.20 × (-2.681) = **-0.536** |
| population_growth | +2.21% | - | inverted: -0.470 | 0.15 × (-0.470) = **-0.071** |
| tax_base_relative | 131.0% | - | inverted: -2.968 | 0.15 × (-2.968) = **-0.445** |
| **KRI total** | | | | **-0.3685** |

**Interpretation:** Debt (+0.353) and unemployment (+0.331) push Stockholm's KRI up; its borrowing of 88,917 SEK per capita is about 1.4 standard deviations above the 2024 mean (rank 33 of 290 on debt). The very young population (dependency ratio 0.595 vs national mean 0.91) and very strong tax base (131% vs 91.7%) generate larger negative contributions, giving a KRI of -0.369 (rank 234 of 290, Låg). Much of Stockholm's borrowing finances its own companies through a group cash pool, which SCB's onlending post does not capture consistently (see Section 5.1).

#### Full worked example: Malmö (1280) in 2024

Malmö has a different combination, high unemployment is the dominant driver.

| Variable | Raw | Z-score | Direction correction | Contribution |
|----------|-----|---------|---------------------|--------------|
| debt_per_capita | 49,842 SEK | +0.167 | kept | 0.25 × 0.167 = **+0.042** |
| unemployment | 5.49% | +4.225 | kept | 0.25 × 4.225 = **+1.056** |
| dependency_ratio | 0.614 | -2.519 | kept | 0.20 × (-2.519) = **-0.504** |
| population_growth | +6.24% | - | inverted: -1.482 | 0.15 × (-1.482) = **-0.222** |
| tax_base_relative | 88.0% | - | inverted: +0.282 | 0.15 × 0.282 = **+0.042** |
| **KRI total** | | | | **+0.414** |

**Interpretation:** Malmö's unemployment rate of 5.49% is 4.2 standard deviations above the 2024 national mean: the unemployment contribution alone (+1.056) is larger than Dorotea's entire KRI score (+0.826). The young population and strong population growth partially compensate, but not enough: Malmö ranks 51st highest risk (Hög class) driven almost entirely by unemployment.

#### Comparison: Kiruna (2584) in 2024, high debt offset by other strengths

Kiruna has the second-highest borrowing per capita in Sweden in 2024 (131,686 SEK, after Östersund), linked to the relocation of the city centre caused by mining subsidence. None of it is onlent to municipal companies (post 088 = 0).

| Variable | Raw | Z-score | Direction correction | Contribution |
|----------|-----|---------|---------------------|--------------|
| debt_per_capita | 131,686 SEK | +2.771 | kept | 0.25 × 2.771 = **+0.693** |
| unemployment | 1.22% | -1.864 | kept | 0.25 × (-1.864) = **-0.466** |
| dependency_ratio | 0.743 | -1.406 | kept | 0.20 × (-1.406) = **-0.281** |
| population_growth | -1.93% | - | inverted: +0.567 | 0.15 × 0.567 = **+0.085** |
| tax_base_relative | 114.0% | - | inverted: -1.683 | 0.15 × (-1.683) = **-0.253** |
| **KRI total** | | | | **-0.222** |

**Interpretation:** Debt is by far Kiruna's largest risk contribution (+0.693), but low unemployment, a relatively young working-age population and a strong tax base outweigh it, giving a KRI of -0.222 (rank 205, Medel). The debt reflects the city relocation rather than operating deficits, illustrating that KRI captures structural *patterns* but is not a substitute for qualitative context.

---

### 9.4 Step 4: Risk Classification and Ranking

#### The classification method

After computing KRI scores for all 290 municipalities within each year, municipalities are classified into three risk categories using **quantile-based thresholds computed within each year**:

```
p25 = 25th percentile of KRI scores within year t
p75 = 75th percentile of KRI scores within year t

risk_class = "Låg"   if KRI < p25   (approximately 72-73 municipalities)
risk_class = "Hög"   if KRI > p75   (approximately 72-73 municipalities)
risk_class = "Medel" otherwise       (approximately 144-146 municipalities)
```

#### 2024 classification boundaries

| Threshold | Value |
|-----------|-------|
| 25th percentile (Låg/Medel boundary) | -0.2777 |
| Median | +0.0185 |
| 75th percentile (Medel/Hög boundary) | +0.2959 |
| Minimum (lowest risk) | -1.4559 (Danderyd) |
| Maximum (highest risk) | +1.2432 (Filipstad) |

A municipality with KRI = -0.28 is classified Låg. A municipality with KRI = -0.27 is classified Medel. The boundary is sharp by design.

#### 2024 classification distribution

| Risk class | Count | Share |
|------------|-------|-------|
| Låg (low) | 73 | 25.2% |
| Medel (medium) | 144 | 49.7% |
| Hög (high) | 73 | 25.2% |

The distribution is by construction approximately 25/50/25 each year. This is a deliberate property of quantile-based classification: it guarantees stable class sizes regardless of whether municipalities improve or worsen in absolute terms.

#### Why quantile-based, not fixed thresholds?

**Alternative considered:** Fixed thresholds (e.g., Hög if KRI > 0.5, Låg if KRI < -0.5). This was rejected because:
- Z-score distributions shift year to year as economic conditions change
- A fixed threshold of +0.5 might classify 40% as Hög in a bad year and 10% in a good year, producing misleading cross-year comparisons
- Quantile thresholds ensure a stable proportion of municipalities in each class, making the classification a relative statement: "this municipality is in the top quartile of risk *relative to peers this year*"

**Alternative considered:** K-means clustering (k=3). This was evaluated (implemented in `src/clustering.py`) but produces unstable cluster boundaries year to year. In 2020 (COVID shock), k-means would have split the high-risk cluster differently than in 2019, making trend analysis unreliable. Quantile classification is more robust.

#### Ranking

```
rank = 1    -> highest KRI score (highest risk)
rank = 290  -> lowest KRI score (lowest risk)
```

Ties are broken using `method='min'` (tied municipalities receive the same lowest rank number).

The rank is computed fresh within each year. A municipality can be rank 15 in 2020 and rank 45 in 2022: this means its risk *relative to peers* improved, even if its absolute KRI score remained similar.

#### Comparative classification: nine municipalities in 2024

| Municipality | KRI score | Rank | Class | Primary driver |
|---|---|---|---|---|
| Danderyd (0162) | -1.4559 | 290 | **Låg** | Extremely strong tax base (191% of national avg) |
| Knivsta (0330) | -0.8598 | 279 | **Låg** | Very fast population growth (+12.5%) |
| Gotland (0980) | -0.4261 | 247 | **Låg** | Low debt per capita (14,065 SEK), low unemployment |
| Stockholm (0180) | -0.3685 | 234 | **Låg** | Young population and strong tax base outweigh above-average debt and unemployment |
| Kiruna (2584) | -0.2220 | 205 | **Medel** | Second-highest debt per capita (131,686 SEK), offset by low unemployment and strong tax base |
| Borlänge (2081) | +0.0232 | 143 | **Medel** | Above-average unemployment, offset by low debt |
| Malmö (1280) | +0.4140 | 51 | **Hög** | Unemployment 5.49%, 4.2 std above national mean |
| Landskrona (1282) | +0.4678 | 43 | **Hög** | Unemployment 4.67% (3.1 std above mean) |
| Dorotea (2425) | +0.8258 | 12 | **Hög** | Severe depopulation (-10.1%), very high dependency ratio |

#### What classification does NOT mean

- A Hög classification does not mean the municipality is insolvent or in financial crisis
- A Låg classification does not mean the municipality is without financial challenges
- The classification is relative: in a year where all municipalities are under stress, the Låg class still contains 25% of municipalities
- Year-over-year class changes reflect changes in *relative standing*, not necessarily absolute deterioration

---

### 9.5 Temporal Stability of the Index

A key quality criterion for a composite index is temporal stability: rankings should not fluctuate randomly year to year. The KRI satisfies this criterion.

**Year-over-year correlation of KRI scores (2010-2024):**

| Period | Correlation |
|--------|-------------|
| 2010 -> 2011 | 0.975 |
| 2011 -> 2012 | 0.979 |
| 2012 -> 2013 | 0.961 |
| 2013 -> 2014 | 0.977 |
| 2014 -> 2015 | 0.980 |
| 2015 -> 2016 | 0.985 |
| 2016 -> 2017 | 0.970 |
| 2017 -> 2018 | 0.969 |
| 2018 -> 2019 | 0.968 |
| 2019 -> 2020 | 0.966 |
| 2020 -> 2021 | 0.969 |
| 2021 -> 2022 | 0.968 |
| 2022 -> 2023 | 0.963 |
| 2023 -> 2024 | 0.972 |
| **Range** | **0.961 - 0.985** |

All year-over-year correlations exceed 0.95, well above the 0.85 threshold defined in the validation specification. This confirms that the index captures structural properties (which change slowly) rather than cyclical noise (which changes rapidly).

The lowest correlation (0.961, in 2012->2013) reflects genuine structural shifts in some municipalities, not index instability.

---

### 9.6 Output Dataset Structure

The full KRI results are saved to `data/processed/kri_results.parquet` with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `municipality_code` | str | 4-digit SCB municipality code |
| `municipality_name` | str | Swedish municipality name |
| `year` | int | Year (2010-2024) |
| `kri_score` | float | Composite KRI score (higher = higher risk) |
| `z_debt` | float | Direction-corrected z-score: debt per capita |
| `z_unemployment` | float | Direction-corrected z-score: unemployment |
| `z_dependency` | float | Direction-corrected z-score: dependency ratio |
| `z_population` | float | Direction-corrected z-score: population growth (inverted) |
| `z_tax_base` | float | Direction-corrected z-score: tax base relative (inverted) |
| `contribution_debt` | float | `0.25 × z_debt` |
| `contribution_unemployment` | float | `0.25 × z_unemployment` |
| `contribution_dependency` | float | `0.20 × z_dependency` |
| `contribution_population` | float | `0.15 × z_population` |
| `contribution_tax_base` | float | `0.15 × z_tax_base` |
| `risk_class` | str | `"Låg"`, `"Medel"`, or `"Hög"` |
| `rank` | int | 1 (highest risk) to 290 (lowest risk) within each year |
| `debt_per_capita` | float | Raw input: total borrowing per capita (SEK) |
| `unemployment` | float | Raw input: unemployment rate (%) |
| `dependency_ratio` | float | Raw input: dependency ratio (dimensionless) |
| `population_growth` | float | Raw input: 5-year population growth (%) |
| `tax_base_relative` | float | Raw input: tax base as % of national average |

**Dataset dimensions:** 4,350 rows (290 municipalities × 15 years), 21 columns, 0 NaN values.

**Implementation reference:** `src/index_builder.py`, class `KRIBuilder`.

---

## 10. Dashboard Implementation

### 10.1 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Application framework | Streamlit | Multi-page web app, widgets, caching |
| Visualization | Apache ECharts (via `streamlit-echarts`) | All interactive charts |
| Map data | GeoJSON centroids (`data/geo/kommuner.geojson`) | Sweden municipality positions |
| Data storage | Parquet (pandas) | Processed pipeline outputs |
| Styling | Custom CSS injected via `st.markdown()` | Design system, fonts, colors |

### 10.2 Design System

All visual constants are defined centrally in `app/styles/theme.py`:

**Color palette:**
- Primary navy: `#0B1F3F`
- Accent gold: `#C4A35A`
- Risk Low (Låg): `#2E7D32` (green)
- Risk Medium (Medel): `#F57F17` (amber)
- Risk High (Hög): `#C62828` (red)
- Background: `#F7F8FA`

**Typography:** Source Sans Pro (headings), IBM Plex Mono (numeric KPI values)

**ECharts helpers** (all charts must use these to ensure consistent styling):
- `get_echarts_base_options()`: grid, animation, background, responsive
- `get_tooltip_style()`: dark navy tooltip with gold border
- `get_axis_style(axis_type)`: axis line, tick, and label styling

### 10.3 Page Architecture

| File | Page |
|------|------|
| `app/main.py` | Entry point and landing page; loads `kri_results.parquet` and shares year and risk filters through session state |
| `app/pages/riksoversikt.py` | National overview: KPI cards, Folium choropleth, KRI distribution, top and bottom 15 with uncertainty intervals |
| `app/pages/riskdekomposition.py` | Contribution of each factor for one municipality, radar against the national average, comparison with up to five peers |
| `app/pages/kommunanalys.py` | Single-municipality deep dive: KPIs, trend, similar municipalities, CSV and PDF export |
| `app/pages/kallor.py` | Data sources, API details, weight-sensitivity method and the rejected PCA alternative |

Components, chart builders and design tokens are documented in `docs/ux-ui-design-system.md`, which is the maintained reference for the UI.

### 10.4 Language Policy

All user-facing strings are in Swedish. Swedish display names are stored in `SWEDISH_LABELS` in `src/config.py` and referenced throughout `app/`. No English text is rendered in the UI. Technical identifiers (column names, variable names, function names) remain in English.
