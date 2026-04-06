# KRI Dataset Identification: Complete Variable and Source Mapping

## Purpose
This document maps every variable needed for the Kommunal Risk Index (KRI), identifies the exact dataset in SCB and/or Kolada, confirms the available time range, flags data quality issues, and provides mitigation strategies.

---

## Data Source Overview

### Primary Source: SCB Statistikdatabasen
- **API endpoint:** `https://api.scb.se/OV0104/v1/doris/sv/ssd/`
- **License:** CC0 (free, no login, no attribution required)
- **Format:** JSON via PxWeb REST API
- **Coverage:** All 290 Swedish municipalities
- **Documentation:** https://www.scb.se/vara-tjanster/oppna-data/api-for-statistikdatabasen/

### Secondary Source: Kolada
- **API endpoint:** `https://api.kolada.se/v2/`
- **License:** Free, open, no contract required
- **Format:** JSON REST API
- **Coverage:** All 290 municipalities, ~6,500 pre calculated KPIs
- **Documentation:** https://github.com/Hypergene/kolada
- **Key advantage:** Many ratios already computed per capita

### Supplementary Source: Riksbanken
- **API endpoint:** `https://api.riksbank.se/swea/v1/`
- **Use:** Macro context indicators (repo rate, inflation) for contextual overlays only

---

## Complete API Reference Table

| # | Variable | Source | API Path / Table | Years Available | All 290? |
|---|----------|--------|------------------|----------------|----------|
| 1 | Debt (balance sheet) | SCB | OE/OE0107/OE0107G/BalansKnN | 1998 to 2025 | Yes |
| 2 | Unemployment | Arbetsformedlingen / Kolada | Kolada API or AF open data | 2006 to 2025 | Yes |
| 3 | Dependency ratio | SCB | BE/BE0101/BE0101A/BefolkningNy | 1968 to 2024 | Yes |
| 4 | Population growth | SCB | Same as #3 | 1968 to 2024 | Yes |
| 5 | Tax base strength | SCB | OE/OE0101/SkatteKraft | 1995 to 2026 | Yes |
| 6 | Annual result | SCB | OE/OE0107/OE0107G/ResultKn | 1998 to 2024 | Yes |
| 7 | Municipal tax rate | SCB | OE/OE0101/Komskatter | 2000 to 2026 | Yes |
| 8 | Equity ratio | Derived from #1 | Balance sheet calculation | 1998 to 2025 | Yes |
| 9 | Education level | SCB | UF/UF0506/UF0506B/UtbBefRegionR | 2008 to 2024 | Yes |
| 10 | Equalization transfers | SCB | OE/OE0115/KomEkUtj | 2005 to 2025 | Yes |
| 11 | Repo rate (context) | Riksbanken | Riksbank API | 1994 to 2025 | N/A |
| 12 | CPI inflation (context) | SCB | PR/PR0101/PR0101A/KPItotM | 1980 to 2025 | N/A |

---

## Timeline Feasibility Matrix

| Variable | 20yr (2005 to 2024) | 15yr (2010 to 2024) | Notes |
|----------|---------------------|---------------------|-------|
| Tax base | YES (1995+) | YES | Clean, no issues |
| Population/Growth | YES (1968+) | YES | Minor boundary issues |
| Dependency ratio | YES (1968+) | YES | Same source as population |
| Unemployment | PARTIAL | YES | AF data OK from ~2006; RAMS/BAS has break at 2018 |
| Municipal debt | YES (1998+) | YES | Use new table series |
| Equalization | NO (2005+) | YES (2010+) | System started 2005 |
| Annual result | YES (1998+) | YES | |
| Education | NO (2008+) | YES (2010+) | |
| Tax rate | YES (2000+) | YES | |

**Verdict:** The 15 year window (2010 to 2024) is the optimal choice. All core and supplementary variables have complete coverage.

---

## Data Quality Issues and Mitigation

### Issue 1: Municipal boundary changes
**Affected:** Knivsta/Uppsala (2003), Heby county switch (2007), Lidingo/Vaxholm (2011)
**Impact:** Population and per capita figures not directly comparable across the change.
**Mitigation:** Start affected municipalities' series from the year after the change. Only 5 to 6 municipalities affected.

### Issue 2: RAMS to BAS employment statistics break
**Impact:** Register based employment stats changed methodology in 2019, creating discontinuity.
**Mitigation:** Use Arbetsformedlingen data, which has a continuous series from 2006+.

### Issue 3: Preliminary vs final data
**Impact:** Most recent year's financial data (2024/2025) is preliminary, may be revised.
**Mitigation:** Flag clearly in dashboard. Use second most recent final year for main ranking; show preliminary as supplementary.

### Issue 4: Region Gotland special case
**Impact:** Gotland has both municipal and regional responsibilities. SCB estimates 65% as municipal.
**Mitigation:** Include with footnote/flag. Optionally show separately.

### Issue 5: Nominal vs real values
**Impact:** SEK values over 15 years not comparable due to inflation.
**Mitigation:** For tax base, use "andel av riksmedelvärdet" (already relative). For debt, per capita normalization plus z scoring mitigates this.

### Issue 6: 2025 population disclosure protection
**Impact:** SCB introduced rounding/noise to small population groups starting 2025.
**Mitigation:** Use 2024 as last clean year. Perturbations are tiny for dependency ratio calculations.

### Issue 7: Missing data points
**Impact:** Some smaller municipalities may have gaps in older financial data.
**Mitigation:** Linear interpolation for isolated gaps. Exclude from ranking if >3 consecutive years missing. Document all exclusions.

---

## Kolada API Strategy

### How to find KPIs
```
GET http://api.kolada.se/v2/kpi?title=<search_term>
```

### Recommended discovery queries
| Search term | Expected KPIs |
|-------------|---------------|
| `soliditet` | Equity ratio |
| `skuldsättning` | Debt indicators |
| `nettokostnad` | Net cost indicators |
| `årets resultat` | Annual financial result |
| `skattekraft` | Tax base |
| `arbetslöshet` | Unemployment |
| `försörjningskvot` | Dependency ratio |
| `befolkning` | Population indicators |

### Data fetch pattern
```
GET http://api.kolada.se/v2/data/kpi/<KPI_ID>/municipality/<MUNI_ID>/year/<YEAR>
```

Multiple KPIs, municipalities, and years can be comma separated in one call. Max 5,000 records per response; use `next_page` for pagination.

---

## Recommended Risk Index Formula

```
KRI(i,t) =
    0.25 * z(debt_per_capita(i,t))
  + 0.25 * z(unemployment(i,t))
  + 0.20 * z(dependency_ratio(i,t))
  + 0.15 * z(neg_population_growth(i,t))
  + 0.15 * z(neg_tax_base_relative(i,t))
```

Classification:
- Low risk: KRI below 25th percentile
- Medium risk: KRI between 25th and 75th percentile
- High risk: KRI above 75th percentile