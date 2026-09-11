# Kommunal Finansiell Riskindikator (KRI)

**Vilka svenska kommuner är strukturellt ekonomiskt sårbara — och varför?**

An interactive Streamlit dashboard ranking all 290 Swedish municipalities on a composite
financial vulnerability index, 2010–2024. 4 350 observations, no missing values.

---

## What this answers

A municipality's finances are usually judged one number at a time — debt per inhabitant,
the unemployment rate, the tax base. Each of those, read alone, gives the wrong answer.
KRI combines five structural indicators into one comparable score so municipalities can be
ranked against each other, and decomposed to show *what* drives each one's risk.

The dashboard is built around four questions.

### 1. Is high debt the same as high risk? No.

**Stockholm carries 400 849 kr of debt per inhabitant — the third-highest in Sweden — and
ranks 126 of 290 (Medel risk). Eskilstuna carries 302 307 kr, a quarter less, and ranks
8th (Hög risk).** Debt alone inverts the answer.

The decomposition shows why:

| Contribution to KRI | Stockholm | Eskilstuna |
|---|---|---|
| Debt | **+0.79** | +0.46 |
| Unemployment | +0.33 | **+0.57** |
| Dependency ratio | −0.54 | −0.17 |
| Tax base | −0.45 | +0.06 |
| **KRI total** | **+0.07** (rank 126) | **+0.92** (rank 8) |

Stockholm borrows heavily, but against a young population (dependency ratio 0.60 vs 0.91
nationally) and a tax base at 131 % of the national average. Eskilstuna borrows less,
against 4.1 % unemployment and a tax base at 86 %. The first is leverage on a growing
asset; the second is a structural gap. Kiruna makes the point hardest: **the highest debt
in Sweden at 523 513 kr per inhabitant, yet rank 67** — 1.2 % unemployment and a 114 % tax
base absorb it.

### 2. What actually drives a municipality's risk?

Not what the weights suggest. Debt carries the joint-largest weight (0.25) but contributes
**the least to the spread between municipalities — 12 % of variance** — because high debt
occurs at both ends: in growing city suburbs and in shrinking rural municipalities.
Unemployment (26 %) and tax base (22 %) do the real separating.

**Högsby is rank 1, the most vulnerable municipality in Sweden — and its debt is
unremarkable** (227 932 kr, below several low-risk municipalities). It ranks first on a
five-year population decline of −10.1 %, a dependency ratio of 1.04, and a tax base at
75 % of the national average. The **Riskdekomposition** page shows this breakdown for any
municipality.

### 3. Is this structural or cyclical?

Structural. Rank correlation between consecutive years is **0.97**, and still **0.63**
between 2010 and 2024. **27 municipalities have been classified Hög risk every single year
since 2010.** Positions do move — Malmö went from rank 232 to 41, Jokkmokk from 61 to 246 —
but slowly, and for reasons visible in the trend charts.

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
| Robust (keeps its class in ≥90 % of draws) | 241 |
| Gränsfall (near a class boundary) | 49 |
| **Published class is also the most frequent class** | **289 / 290** |

The index is corroborated, not overturned. But it does find genuinely fragile cases:
**Kiruna is published at rank 67 yet could plausibly sit anywhere from 29 to 137**, holding
the Hög label in only 52 % of draws. It is labelled *gränsfall* rather than presented as a
fact. Eskilstuna, by contrast, never leaves rank 4–13.

PCA weighting was tested and rejected — PC1 loads negatively on debt in all fifteen years,
which would rank the most indebted municipalities as the safest. Full argument, plus the
δ = 0.03 / 0.10 robustness check, in [docs/methodology.md §3.5](docs/methodology.md).

---

## The index

```
KRI(i,t) = Σ wk × zk(i,t)
```

Each variable becomes a cross-sectional z-score per year, direction-corrected so higher
always means higher risk, then weighted:

| Variable | Weight | Direction | Source |
|---|---|---|---|
| Debt per capita | 0.25 | High = high risk | SCB, BalansKn |
| Unemployment | 0.25 | High = high risk | Kolada N03937 (Arbetsförmedlingen) |
| Dependency ratio | 0.20 | High = high risk | SCB, BefolkningNy |
| Population growth (5 yr) | 0.15 | Negative = high risk | SCB, BefolkningNy |
| Tax base (% of national avg) | 0.15 | Low = high risk | SCB, SkatteKraft |

**Classification:** per-year quartiles — Låg below p25, Hög above p75, Medel between.
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
pytest                              # 102 tests
```

**Streamlit Cloud:** point a new app at this repo with main file `app/main.py` and Python
3.11. No secrets or environment variables required.

---

## Pages

| Page | What it's for |
|---|---|
| **Riksöversikt** | National picture — choropleth, KRI distribution, top/bottom 15 with uncertainty intervals |
| **Riskdekomposition** | Which of the five factors drives one municipality's score, and comparison against up to five peers |
| **Kommunanalys** | Single-municipality deep dive — KPIs, 2010–2024 trend, similar municipalities, CSV/PDF export |
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

MIT License — see [LICENSE](LICENSE).

*Källa: SCB, Arbetsförmedlingen/Kolada · KRI v1.0 · 2010–2024*
