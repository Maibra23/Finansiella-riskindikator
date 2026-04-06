# Methodology: Kommunal Finansiell Riskindikator (KRI)

## 1. Theoretical Foundation

### 1.1 What KRI measures
KRI (Kommunal Riskindikator) is a composite index that quantifies the structural economic vulnerability of Sweden's 290 municipalities. The index combines five dimensions of financial risk into a single comparable score.

The index draws on established frameworks in public finance analysis:
- OECD Fiscal Decentralisation Database methodology
- EU Fiscal Sustainability Reports
- SKR (Sveriges Kommuner och Regioner) economic reporting standards
- Riksbanken financial stability analysis approaches

### 1.2 Why a composite index?
Individual indicators (e.g., debt or unemployment alone) give an incomplete picture. A municipality can have high debt but strong tax base (e.g., Stockholm), or low debt but shrinking population (e.g., rural municipalities in northern Sweden). By combining multiple dimensions, the overall risk profile is captured more accurately.

### 1.3 Analysis period
**2010 to 2024 (15 years)**

Rationale:
- All five core variables have complete time series from 2010
- The period covers a full business cycle: post 2008/2009 recovery, growth years, pandemic 2020/2021, inflation shock 2022/2023
- Arbetsformedlingen unemployment data is reliable from approximately 2006, but we avoid the RAMS/BAS methodological break in 2018/2019 by using Arbetsformedlingen rather than SCB register data
- SCB's new accounting summary table series has consistent definitions across the entire period

---

## 2. Data Specification

### 2.1 Complete API Reference and Data Sources

#### VARIABLE 1: Long term debt per capita

| Field | Detail |
|-------|--------|
| **Description** | Municipality's long term liabilities divided by population. Primary indicator of fiscal burden. |
| **Source** | SCB Statistikdatabasen |
| **Table name** | Balansrakning for kommuner efter region och balansrakningsposter, tkr, lopande priser |
| **Table ID** | BalansKnN |
| **API path** | `START/OE/OE0107/OE0107G/BalansKnN` |
| **API base URL** | `https://api.scb.se/OV0104/v1/doris/sv/ssd/OE/OE0107/OE0107G/BalansKnN` |
| **Web page** | https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__OE__OE0107__OE0107G/BalansKnN/ |
| **Balance post to extract** | Langfristiga skulder (long term liabilities) |
| **Available period** | 1998 to 2025 |
| **Used period** | 2010 to 2024 |
| **Unit** | Tkr (thousands of SEK), current prices |
| **Geographic level** | All 290 municipalities |
| **Update frequency** | Annual (preliminary in March, final in Aug/Sep) |
| **Calculation** | (Long term liabilities in tkr * 1000) / Population = debt per capita in kr |
| **Direction** | High debt per capita = High risk |

**Population data for per capita calculation:**
- Source: SCB Population statistics
- API path: `START/BE/BE0101/BE0101A/BefolkningNy`
- Available: 1968 to 2024, all 290 municipalities

#### VARIABLE 2: Unemployment

| Field | Detail |
|-------|--------|
| **Description** | Share of openly unemployed persons as percentage of population aged 16 to 64. Proxy for tax base weakness and social costs. |
| **Source** | Arbetsformedlingen (Swedish Public Employment Service), NOT SCB |
| **Data portal** | https://arbetsformedlingen.se/statistik/statistik-och-analyser |
| **Alternative via Kolada** | `http://api.kolada.se/v2/kpi?title=arbetslöshet` |
| **Available period** | 2006 to 2025 |
| **Used period** | 2010 to 2024 |
| **Unit** | Percent (%) |
| **Geographic level** | All 290 municipalities |
| **Definition** | Registered openly unemployed as share of population 16 to 64 |
| **Direction** | High unemployment = High risk |

**Why not SCB RAMS/BAS?**
SCB's register based labor market statistics (RAMS) was replaced by BAS in 2019. The definition change creates a time series break that makes it impossible to compare data before and after 2019 without adjustment. Arbetsformedlingen data has a consistent definition across the full period.

**Limitation:** Registered unemployment captures only those registered with the employment service. This excludes people who are unemployed but not registered. However, this bias is consistent across municipalities and time, making it valid as a relative comparison measure.

#### VARIABLE 3: Dependency ratio

| Field | Detail |
|-------|--------|
| **Description** | Ratio of non working age population (0 to 19 + 65+) to working age population (20 to 64). Measures demographic pressure on the welfare system. |
| **Source** | SCB Statistikdatabasen |
| **Table** | Folkmangden efter region, civilstand, alder och kon |
| **API path** | `START/BE/BE0101/BE0101A/BefolkningNy` |
| **API base URL** | `https://api.scb.se/OV0104/v1/doris/sv/ssd/BE/BE0101/BE0101A/BefolkningNy` |
| **Available period** | 1968 to 2024 |
| **Used period** | 2010 to 2024 |
| **Unit** | Ratio (decimal, e.g., 0.75 means 75 dependents per 100 working age) |
| **Geographic level** | All 290 municipalities |
| **Calculation** | (Population 0 to 19 + Population 65+) / Population 20 to 64 |
| **Direction** | High dependency ratio = High risk |

**Data quality:** This data source is the most reliable in the entire project. Complete coverage for all municipalities, long time series, no methodology changes.

#### VARIABLE 4: Population growth

| Field | Detail |
|-------|--------|
| **Description** | Percentage population change over a 5 year period. Declining population means shrinking tax base and rising per capita costs for fixed infrastructure. |
| **Source** | SCB Statistikdatabasen (same table as variable 3) |
| **API path** | Same as variable 3 |
| **Available period** | 1968 to 2024 |
| **Used period** | 2010 to 2024 (requires data back to 2005 for 5yr calculation) |
| **Unit** | Percent (%) |
| **Calculation** | ((Pop_t / Pop_{t minus 5}) minus 1) * 100 |
| **Direction** | Negative growth (population decline) = High risk |

**Rationale for 5 year rolling average:** Single year population changes are volatile in small municipalities. A 5 year average smooths out temporary fluctuations and captures structural trends.

#### VARIABLE 5: Tax base strength

| Field | Detail |
|-------|--------|
| **Description** | Municipality's taxable income per inhabitant as a share of the national average. Measures relative revenue generating capacity. |
| **Source** | SCB Statistikdatabasen |
| **Table** | Skatteunderlag och skattekraft |
| **Table ID** | SkatteKraft |
| **API path** | `START/OE/OE0101/SkatteKraft` |
| **API base URL** | `https://api.scb.se/OV0104/v1/doris/sv/ssd/OE/OE0101/SkatteKraft` |
| **Web page** | https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__OE__OE0101/SkatteKraft/ |
| **Variable to use** | Andel av riksmedelvärdet, procent (share of national average, percent) |
| **Available period** | 1995 to 2026 |
| **Used period** | 2010 to 2024 |
| **Unit** | Percent of national average |
| **Geographic level** | All 290 municipalities |
| **Direction** | Low tax base (below 100%) = High risk |
| **Time lag note** | Tax base for year t is based on incomes from year t minus 2. So "tax base 2024" reflects 2022 incomes. |

**Advantage:** The "share of national average" variable is already normalized relative to the national mean, eliminating the need for inflation adjustment.

#### SUPPLEMENTARY VARIABLE 6: Annual financial result

| Field | Detail |
|-------|--------|
| **Source** | SCB Statistikdatabasen |
| **Table** | Resultatrakning for kommuner |
| **API path** | `START/OE/OE0107/OE0107G/ResultKn` |
| **Available period** | 1998 to 2024 |
| **Unit** | Kr per inhabitant |
| **Direction** | Negative result = increased risk (used for deep analysis, not in core KRI) |

#### SUPPLEMENTARY VARIABLE 7: Municipal tax rate

| Field | Detail |
|-------|--------|
| **Source** | SCB Statistikdatabasen |
| **API path** | `START/OE/OE0101/Komskatter` |
| **Available period** | 2000 to 2026 |
| **Unit** | Percent (%) |
| **Interpretation** | Very high tax rate may indicate the municipality has exhausted its taxing capacity |

#### SUPPLEMENTARY VARIABLE 8: Equity ratio (Soliditet)

| Field | Detail |
|-------|--------|
| **Source** | Calculated from SCB balance sheet (BalansKnN) |
| **Calculation** | Equity / Total assets * 100 |
| **Unit** | Percent (%) |
| **Direction** | Low equity ratio = high leverage = increased risk |

#### KOLADA API (alternative/supplementary source)

| Field | Detail |
|-------|--------|
| **API base URL** | `https://api.kolada.se/v2/` |
| **KPI search** | `GET /v2/kpi?title=<search_term>` |
| **Data fetch** | `GET /v2/data/kpi/<KPI_ID>/municipality/<MUNI_CODE>/year/<YEAR>` |
| **Municipality list** | `GET /v2/municipality` |
| **Format** | JSON |
| **License** | Free use, no contract required |
| **Max results per call** | 5000 records (paginate via next_page) |
| **Relevant search terms** | soliditet, skuldsättning, årets resultat, skattekraft, arbetslöshet, försörjningskvot, befolkningsförändring |

**How SCB PxWeb API works:**
- Send POST request to the table URL with a JSON query body
- Query body specifies which variables, regions, and years to fetch
- Empty values array for Region = all municipalities
- Response is in JSON stat format
- Example query body:
```json
{
  "query": [
    {"code": "Region", "selection": {"filter": "vs:RegionKommun07", "values": []}},
    {"code": "Tid", "selection": {"filter": "item", "values": ["2010","2011","2024"]}}
  ],
  "response": {"format": "json"}
}
```

---

## 3. Model Specification

### 3.1 KRI formula

```
KRI(i,t) = w1 * z(debt_per_capita(i,t))
          + w2 * z(unemployment(i,t))
          + w3 * z(dependency_ratio(i,t))
          + w4 * z(neg_population_growth(i,t))
          + w5 * z(neg_tax_base_rel(i,t))
```

Where:
- `i` = municipality (1 to 290)
- `t` = year (2010 to 2024)
- `z()` = z score normalization: (value minus mean) / standard deviation
- z scores are computed cross sectionally for each year (all municipalities compared within the same year)
- `neg_` prefix means the variable is inverted (multiplied by minus 1) before normalization

### 3.2 Weights

| Variable | Weight | Rationale |
|----------|--------|-----------|
| Debt per capita | 0.25 | Direct financial obligation, strongest short term risk signal |
| Unemployment | 0.25 | Immediate tax base erosion and social cost driver |
| Dependency ratio | 0.20 | Structural long term pressure, less volatile |
| Population growth | 0.15 | Long term trajectory indicator |
| Tax base strength | 0.15 | Revenue capacity proxy, partially captured by other variables |
| **Total** | **1.00** | |

### 3.3 Normalization method

**Z score normalization** (standardization):
```
z(x_i) = (x_i minus mean) / std
```
Where mean and std are computed across all 290 municipalities within the same year.

**Why z scores?**
- Makes all variables comparable regardless of original unit
- Preserves relative distances between municipalities
- Standard method in composite indices (cf. UNDP HDI, EU Regional Competitiveness Index)

**Direction correction:**
- Variables where high value = high risk: used directly (debt, unemployment, dependency ratio)
- Variables where high value = low risk: multiplied by minus 1 before normalization (population growth, tax base)

### 3.4 Classification method

**Quantile based thresholds (computed per year):**
- Low risk: KRI below 25th percentile (approximately 72 municipalities)
- Medium risk: KRI between 25th and 75th percentile (approximately 146 municipalities)
- High risk: KRI above 75th percentile (approximately 72 municipalities)

**Rationale:** Quantile based classification is robust to outliers and produces a stable distribution regardless of year. The alternative (k means) can produce unstable clusters between years.

---

## 4. Evaluation and Validation

### 4.1 Sanity checks
- Danderyd and Lidingo should consistently rank as low risk (high tax base, low unemployment)
- Rural municipalities in northern inland Sweden (e.g., Dorotea, Bjurholm, Asele) should rank as high risk
- Stockholm should fall in low to medium risk (high debt but strong tax base)

### 4.2 Temporal stability
- KRI rankings should be relatively stable between adjacent years
- Large rank jumps (>50 positions) for individual municipalities should be investigated and documented
- The pandemic (2020/2021) is expected to cause temporary spikes, especially in unemployment

### 4.3 Correlation analysis
- Compute correlation matrix across all five variables
- Verify no variable has correlation > 0.85 with another (which would indicate redundancy)
- If high correlation found: consider merging or reducing weight

---

## 5. Bias, Limitations, and Interpretation Warnings

### 5.1 Known biases

**Size bias:** Small municipalities (under 5,000 inhabitants) have more volatile indicators. A single factory closure can cause large unemployment spikes. Mitigation: 5 year rolling average for population growth. Residual bias is documented.

**Time lag in tax base:** Tax base figures are based on incomes from two years prior. Rapid economic changes appear with a delay.

**Registration bias in unemployment:** Arbetsformedlingen data captures only registered unemployed. Municipalities with high informal economy or commuter populations may look different in reality.

**Gotland special case:** Region Gotland has both municipal and regional responsibilities. SCB estimates 65% relates to municipal activities. Balance sheet and income statement comparisons with other municipalities should be made with caution.

### 5.2 Limitations

**Model limitations:**
- Weights (0.25/0.25/0.20/0.15/0.15) are normatively set, not empirically derived. Different weights produce different rankings.
- The index captures structural vulnerability but not a municipality's actual political capacity to manage challenges.
- Z score normalization means the index always identifies "high risk" municipalities even if all municipalities improve. It is a relative measure.

**Data limitations:**
- Financial data for 2024 may be preliminary and subject to revision
- Municipal boundary changes (Knivsta 2003, Heby 2007, Lidingo/Vaxholm 2011) affect comparability marginally
- Nominal values (current prices) are used for debt; no inflation adjustment is applied (but per capita normalization partially offsets this)

### 5.3 Interpretation warnings

**KRI should be interpreted as:**
- A relative ranking tool for comparison between municipalities
- An indication of structural vulnerability, not a forecast of bankruptcy or crisis
- A complement to qualitative analysis, not a replacement

**KRI should NOT be interpreted as:**
- An absolute probability of economic crisis
- A recommendation to avoid investing in high risk municipalities
- A measure of municipal service quality or quality of life

---

## 6. Handling Incomplete Data

### 6.1 Identification
Every municipality is checked for complete data across all 5 core variables for all 15 years (2010 to 2024). A municipality is flagged if it is missing data for at least one variable in at least one year.

### 6.2 Strategies

| Situation | Strategy |
|-----------|----------|
| Single missing year (1 to 2 years) | Linear interpolation between adjacent years |
| Missing data at start of series (2010 to 2011) | Forward extrapolation from first available year |
| Missing data at end of series | Backward extrapolation from last available year |
| More than 3 consecutive missing years | Municipality excluded from ranking that year, flagged in UI |
| Variable entirely missing for a municipality | Municipality included but with fewer variables; weights redistributed proportionally |

### 6.3 Dashboard documentation
- Municipalities with interpolated data are marked with an asterisk (*) in tables
- An info panel shows the count of municipalities with complete vs interpolated data per year
- Users can filter to show only municipalities with complete data

---

## 7. Reproducibility

### 7.1 Data
- All raw data saved in `data/raw/` with timestamps
- API calls logged with exact URL and timestamp
- Cached data is versioned

### 7.2 Code
- All transformations documented in Python scripts
- requirements.txt freezes all package versions
- README contains step by step instructions to reproduce

### 7.3 Results
- Final KRI scores exported as CSV
- PDF report generated automatically from the same data pipeline