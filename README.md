# Kommunal Finansiell Riskindikator (KRI)

**Vilka svenska kommuner är strukturellt ekonomiskt sårbara, och varför?**

An interactive Streamlit dashboard ranking all 290 Swedish municipalities on a composite
financial vulnerability index, 2010-2024. 4 350 observations, no missing values.

---

## What this answers

A municipality's finances are usually judged one number at a time: debt per inhabitant,
the unemployment rate, the tax base. Each of those, read alone, gives the wrong answer.
KRI combines five structural indicators into one comparable score so municipalities can be
ranked against each other, and decomposed to show *what* drives each one's risk.

The dashboard is built around four questions.

### 1. Is high debt the same as high risk? No.

**Bjurholm and Nykvarn carry almost the same long-term debt per inhabitant, 135 220 kr and
131 140 kr, the first and fourth highest in Sweden. Bjurholm ranks 2nd of 290 (Hög risk).
Nykvarn ranks 218th (Låg risk).** Debt alone cannot tell them apart.

The decomposition shows why:

| Contribution to KRI | Bjurholm | Nykvarn |
|---|---|---|
| Debt | +0.76 | +0.73 |
| Unemployment | -0.01 | -0.17 |
| Dependency ratio | **+0.26** | -0.21 |
| Population growth | +0.09 | **-0.44** |
| Tax base | +0.14 | -0.21 |
| **KRI total** | **+1.24** (rank 2) | **-0.30** (rank 218) |

Nykvarn borrows against a population that grew 12.1 % in five years and a tax base at
110 % of the national average. Bjurholm borrows against a shrinking, ageing population
(dependency ratio 1.05 vs 0.91 nationally) and a tax base at 79 %. The first is leverage on
a growing asset; the second is a structural gap. The pattern holds across the top of the
debt table: **Sweden's five most indebted municipalities rank 2, 34, 83, 196 and 218 on
risk.**

### 2. What actually drives a municipality's risk?

Not what the weights suggest. Debt and unemployment carry the largest weights (0.25 each),
yet the five factors contribute almost equally to the spread between municipalities
(2024 share of KRI variance):

| Unemployment | Tax base | Dependency | Population growth | Debt |
|---|---|---|---|---|
| 23 % | 22 % | 20 % | 18 % | 17 % |

Debt contributes least because it does not line up with the other risks: high debt occurs
both in growing municipalities like Nykvarn and in shrinking ones like Bjurholm, so it
partly offsets the demographic factors instead of reinforcing them.

**Högsby is rank 1, the most vulnerable municipality in Sweden, without being a debt
outlier** (79 593 kr, 37th highest). It ranks first because all five factors point the same
way, led by a five-year population decline of -10.1 %, a dependency ratio of 1.04 and a tax
base at 75 % of the national average. The **Riskdekomposition** page shows this breakdown
for any municipality.

### 3. Is this structural or cyclical?

Structural. Rank correlation between consecutive years averages **0.97**, and is still
**0.63** between 2010 and 2024. **30 municipalities have been classified Hög risk every
single year since 2010.** Positions do move. Malmö went from rank 243 to 46 and Jokkmokk
from 86 to 255, but slowly, and for reasons visible in the trend charts.

> **Read the classes as relative, not absolute.** Risk classes are per-year quartiles, so
> exactly 25 % of municipalities are Hög risk in every year *by construction*. The share
> cannot tell you whether Sweden as a whole improved; it tells you how municipalities stand
> relative to each other.

### 4. How much of this depends on the weights we chose?

The weights are argued from public-finance theory, not estimated, so the dashboard
measures how much the ranking depends on them: each weight is varied by ±0.05, the index
is recomputed 1 000 times, and every municipality gets a rank interval and a stability
score.

| 2024, n = 290 | |
|---|---|
| Robust (keeps its class in ≥90 % of draws) | 237 |
| Gränsfall (near a class boundary) | 53 |
| **Published class is also the most frequent class** | **286 / 290** |

The index is corroborated, not overturned. The four disagreements all sit within two ranks
of a quartile boundary. The analysis does find genuinely fragile cases: **Nykvarn is
published at rank 218 yet could plausibly sit anywhere from 180 to 253**, holding the Låg
label in only 54 % of draws. It is labelled *gränsfall* rather than presented as a fact.
Bjurholm, by contrast, never leaves rank 1-4.

PCA weighting was tested and rejected: from 2012 onward PC1 loads negatively on debt, which
would rank the most indebted municipalities among the safest. Full argument, plus the
δ = 0.03 / 0.10 robustness check, in [docs/methodology.md §3.5](docs/methodology.md).

> **Data correction (October 2026).** Earlier versions summed three balance sheet posts
> instead of using long-term debt alone, overstating debt roughly fourfold; every figure
> above comes from the corrected data. Debt is now SCB post 089 and is checked by test
> against SCB's published national total. Details in
> [docs/methodology.md §7.4](docs/methodology.md).

---

## The index

```
KRI(i,t) = Σ wk × zk(i,t)
```

Each variable becomes a cross-sectional z-score per year, direction-corrected so higher
always means higher risk, then weighted:

| Variable | Weight | Direction | Source |
|---|---|---|---|
| Long-term debt per capita | 0.25 | High = high risk | SCB, BalansKn (post 089) |
| Unemployment | 0.25 | High = high risk | Kolada N03937 (Arbetsförmedlingen) |
| Dependency ratio | 0.20 | High = high risk | SCB, BefolkningNy |
| Population growth (5 yr) | 0.15 | Negative = high risk | SCB, BefolkningNy |
| Tax base (% of national avg) | 0.15 | Low = high risk | SCB, SkatteKraft |

**Classification:** per-year quartiles: Låg below p25, Hög above p75, Medel between.
Robust to outliers, and stable regardless of whether all municipalities move together.

Full specification, worked examples and limitations: [docs/methodology.md](docs/methodology.md).

---

## Run it

Requires Python 3.11+.

```bash
git clone https://github.com/Maibra23/Kommunal-Finansiell-Riskindikator.git
cd Kommunal-Finansiell-Riskindikator
pip install -r requirements.txt
streamlit run app/main.py
```

Processed data is committed, so the dashboard runs immediately. To rebuild it from the
source APIs:

```bash
python scripts/run_pipeline.py      # fetch -> clean -> build index
python scripts/run_sensitivity.py   # weight-sensitivity band (optional)
python scripts/verify_pipeline.py   # validate the output
pytest                              # 107 tests
```

**Streamlit Cloud:** point a new app at this repo with main file `app/main.py` and Python
3.11. No secrets or environment variables required.

---

## Pages

| Page | What it's for |
|---|---|
| **Riksöversikt** | National picture: choropleth, KRI distribution, top/bottom 15 with uncertainty intervals |
| **Riskdekomposition** | Which of the five factors drives one municipality's score, and comparison against up to five peers |
| **Kommunanalys** | Single-municipality deep dive: KPIs, 2010-2024 trend, similar municipalities, CSV/PDF export |
| **Källor** | Data sources, API details, the weight-sensitivity method and the rejected PCA alternative |

Built with Streamlit and Apache ECharts; the choropleth uses Folium with keyless Esri
basemap tiles.

---

## Data

All data is public and free to use with attribution.

| Source | Covers | Licence |
|---|---|---|
| SCB Statistikdatabasen (PxWeb API) | Debt, population, tax base | SCB open licence |
| Kolada / RKA (KPI N03937) | Unemployment, via Arbetsförmedlingen | CC0 |

Endpoints and request examples are documented in-app on the **Källor** page.

---

MIT License. See [LICENSE](LICENSE).

*Källa: SCB, Arbetsförmedlingen/Kolada · KRI v1.0 · 2010-2024*
