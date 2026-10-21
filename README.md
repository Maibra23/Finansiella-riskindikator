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

**Nykvarn and Eskilstuna borrow almost exactly the same per inhabitant, 121 706 kr and
120 772 kr, the ninth and tenth highest in Sweden. Eskilstuna ranks 6th of 290 (Hög risk).
Nykvarn ranks 245th (Låg risk).** Debt alone cannot tell them apart.

The decomposition shows why:

| Contribution to KRI | Eskilstuna | Nykvarn |
|---|---|---|
| Debt | +0.61 | +0.61 |
| Unemployment | **+0.57** | -0.17 |
| Dependency ratio | -0.17 | -0.21 |
| Population growth | 0.00 | **-0.44** |
| Tax base | +0.06 | -0.21 |
| **KRI total** | **+1.07** (rank 6) | **-0.41** (rank 245) |

Nykvarn borrows against a population that grew 12.1 % in five years and a tax base at
110 % of the national average. Eskilstuna borrows against 4.1 % unemployment and a tax base
at 86 %. The first is leverage on a growing asset; the second is a structural gap. The
pattern holds across the top of the debt table: **Sweden's ten most indebted
municipalities rank anywhere from 6th to 245th on risk.**

### 2. What actually drives a municipality's risk?

Not what the weights suggest. Debt and unemployment carry the largest weights (0.25 each),
yet the five factors contribute almost equally to the spread between municipalities
(2024 share of KRI variance):

| Unemployment | Tax base | Dependency | Population growth | Debt |
|---|---|---|---|---|
| 24 % | 22 % | 18 % | 18 % | 17 % |

Debt contributes least because it does not line up with the other risks: high debt occurs
both in growing municipalities like Nykvarn and in shrinking ones, so it partly offsets the
demographic factors instead of reinforcing them.

**Filipstad is rank 1, the most vulnerable municipality in Sweden, without being a debt
outlier** (71 227 kr, 53rd highest). It ranks first because all five factors point the same
way: a five-year population decline of -8.2 %, a dependency ratio of 1.03, unemployment of
3.4 % and a tax base at 75 % of the national average. The **Riskdekomposition** page shows
this breakdown for any municipality.

### 3. Is this structural or cyclical?

Structural. Rank correlation between consecutive years averages **0.97**, and is still
**0.63** between 2010 and 2024. **28 municipalities have been classified Hög risk every
single year since 2010.** Positions do move. Malmö went from rank 243 to 51 and Jokkmokk
from 78 to 248, but slowly, and for reasons visible in the trend charts.

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
| Robust (keeps its class in ≥90 % of draws) | 235 |
| Gränsfall (near a class boundary) | 55 |
| **Published class is also the most frequent class** | **288 / 290** |

The index is corroborated, not overturned. The two disagreements sit exactly on a quartile
boundary (ranks 73 and 218). The analysis does find genuinely fragile cases: **Kiruna, with
the second-highest debt in Sweden, is published at rank 205 yet could plausibly sit anywhere
from 160 to 242**, holding the Medel label in only 70 % of draws. It is labelled
*gränsfall* rather than presented as a fact. Eskilstuna, by contrast, never leaves rank 3-9.

PCA weighting was tested and rejected: from 2011 onward PC1 loads negatively on debt, which
would rank the most indebted municipalities among the safest. Full argument, plus the
δ = 0.03 / 0.10 robustness check, in [docs/methodology.md §3.5](docs/methodology.md).

> **What "debt" means here.** Debt is the municipality's total borrowing: all long- and
> short-term loans, including bonds (SCB BalansKn). Every value is checked against Kolada's
> published loan figures (`scripts/validate_against_kolada.py`). Earlier versions used a
> balance-sheet sum that overstated debt roughly fourfold; the correction history is in
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
| Borrowing per capita | 0.25 | High = high risk | SCB, BalansKn |
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
python scripts/validate_against_kolada.py  # cross-check against Kolada (network)
pytest                              # 110 tests
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
