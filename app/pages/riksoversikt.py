"""
Page 1: Riksöversikt — national overview of KRI scores for all 290 municipalities.

Charts use streamlit-echarts (Apache ECharts). All user-facing text is in Swedish.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

from app.components.charts import build_distribution_histogram, build_raw_indicator_histogram
from app.components.sweden_choropleth import render_choropleth
from app.styles.theme import (
    apply_streamlit_theme,
    format_swedish_int,
    render_card_header,
    render_kpi_card,
    render_page_header,
)
from src.config import MUNICIPALITIES, SWEDISH_LABELS

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
apply_streamlit_theme()

# Sidebar (runs when this page is opened directly; mirrors app/main.py)
pages_dir = PROJECT_ROOT / "app" / "pages"
st.sidebar.markdown(
    """
    <div class="sidebar-brand">
        <div class="brand-mark">KRI Kontrollpanel</div>
        <div class="brand-title">Kommunal Risk</div>
        <div class="brand-sub">Finansiell sårbarhet · SE</div>
    </div>
    <div class="nav-section">Navigation</div>
    """,
    unsafe_allow_html=True,
)
st.sidebar.page_link("main.py", label="Startsida")
nav_items = [
    ("riksoversikt.py", "Riksöversikt"),
    ("riskdekomposition.py", "Riskdekomposition"),
    ("kommunanalys.py", "Kommunanalys"),
]
for fname, title in nav_items:
    if (pages_dir / fname).exists():
        st.sidebar.page_link(f"pages/{fname}", label=title)
st.sidebar.caption("Metod & källor, kommer snart")
st.sidebar.markdown("<br/>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Laddar data…")
def _load() -> pd.DataFrame:
    p = PROJECT_ROOT / "data" / "processed" / "kri_results.parquet"
    df = pd.read_parquet(p)
    df["year"] = df["year"].astype(int)
    return df


if "kri_df" in st.session_state:
    kri_df: pd.DataFrame = st.session_state["kri_df"]
else:
    kri_df = _load()

available_years = sorted(kri_df["year"].unique().tolist())
default_year = st.session_state.get("selected_year", max(available_years))

# ── Year chips ──────────────────────────────────────────────────
st.sidebar.markdown(
    f'<div class="sidebar-control"><div class="control-label">{SWEDISH_LABELS["select_year"]}</div></div>',
    unsafe_allow_html=True,
)
_year_raw = st.sidebar.pills(
    SWEDISH_LABELS["select_year"],
    options=available_years,
    default=default_year,
    label_visibility="collapsed",
    key="rv_year_pills",
)
selected_year: int = int(_year_raw) if _year_raw is not None else default_year

# ── Risk filter: colored dot legend + multi-select pills ────────
st.sidebar.markdown(
    f"""
    <div class="sidebar-control">
        <div class="control-label">{SWEDISH_LABELS["filter_risk_class"]}</div>
        <div class="riskklass-legend">
            <div class="riskklass-rad">
                <span class="riskklass-punkt" style="background:#2E7D5B"></span>Låg risk
            </div>
            <div class="riskklass-rad">
                <span class="riskklass-punkt" style="background:#D4A03C"></span>Medel risk
            </div>
            <div class="riskklass-rad">
                <span class="riskklass-punkt" style="background:#B94A48"></span>Hög risk
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
_default_risks = st.session_state.get("selected_risks", [])
_risks_raw = st.sidebar.pills(
    SWEDISH_LABELS["filter_risk_class"],
    options=["Hög", "Medel", "Låg"],
    selection_mode="multi",
    default=_default_risks if _default_risks else None,
    label_visibility="collapsed",
    key="rv_risk_pills",
)
selected_risks: list[str] = list(_risks_raw) if _risks_raw else []

st.sidebar.markdown(
    """
    <div class="sidebar-footer">
        <strong>KÄLLA:</strong> SCB, Arbetsförmedlingen<br/>
        Senast uppdaterad 2024-12-31
    </div>
    """,
    unsafe_allow_html=True,
)

st.session_state["selected_year"] = selected_year
st.session_state["selected_risks"] = selected_risks
st.session_state["kri_df"] = kri_df

year_df = kri_df[kri_df["year"] == selected_year].copy()

# Filter by selected risk classes; empty list = show all
if selected_risks:
    filtered_df = year_df[year_df["risk_class"].isin(selected_risks)].copy()
else:
    filtered_df = year_df.copy()

prev_year = selected_year - 1
prev_df = kri_df[kri_df["year"] == prev_year] if prev_year in kri_df["year"].values else pd.DataFrame()


def _fmt_decimal(val: float, nd: int = 2) -> str:
    """Format float with Swedish decimal comma; avoids '-0,00' from signed zero."""
    v = round(float(val), nd)
    if abs(v) < 10 ** (-nd):
        v = 0.0
    s = f"{v:,.{nd}f}"
    if nd > 0:
        s = s.replace(",", "X").replace(".", ",").replace("X", "\u202f")
    else:
        s = s.replace(",", "\u202f")
    return s


def _fmt_int_space(n: float) -> str:
    """Integer with Swedish thousands grouping (delegates to theme helper)."""
    return format_swedish_int(n)


def _delta_kri_median() -> tuple[str, str]:
    if prev_df.empty:
        return ("", "flat")
    cur = float(filtered_df["kri_score"].median()) if len(filtered_df) else 0.0
    prv = float(prev_df["kri_score"].median())
    d = cur - prv
    if abs(d) < 0.005:
        return ("Oförändrat mot föregående år", "flat")
    sign = "+" if d > 0 else ""
    txt = f"{sign}{_fmt_decimal(d, 2)} mot {prev_year}"
    direction = "up" if d > 0 else "down"
    return (txt, direction)


def _delta_high_risk() -> tuple[str, str]:
    if prev_df.empty:
        return ("", "flat")
    cur = int((filtered_df["risk_class"] == "Hög").sum())
    prv = int((prev_df["risk_class"] == "Hög").sum())
    d = cur - prv
    if d == 0:
        return ("Oförändrat mot föregående år", "flat")
    sign = "+" if d > 0 else ""
    txt = f"{sign}{d} mot {prev_year}"
    direction = "up" if d > 0 else "down"
    return (txt, direction)


def _delta_median_debt_pct() -> tuple[str, str]:
    if prev_df.empty or filtered_df.empty:
        return ("", "flat")
    cur = float(filtered_df["debt_per_capita"].median())
    prv = float(prev_df["debt_per_capita"].median())
    if prv == 0:
        return ("", "flat")
    pct = (cur - prv) / prv * 100.0
    if abs(pct) < 1e-6:
        return ("Oförändrat mot föregående år", "flat")
    sign = "+" if pct > 0 else ""
    txt = f"{sign}{_fmt_decimal(pct, 1)} % mot {prev_year}"
    direction = "up" if pct > 0 else "down"
    return (txt, direction)


def _delta_pop_mean() -> tuple[str, str]:
    if prev_df.empty or filtered_df.empty:
        return ("", "flat")
    cur = float(filtered_df["population_growth"].mean())
    prv = float(prev_df["population_growth"].mean())
    d = cur - prv
    if abs(d) < 0.005:
        return ("Oförändrat mot föregående år", "flat")
    sign = "+" if d > 0 else ""
    txt = f"{sign}{_fmt_decimal(d, 2)} pe mot {prev_year}"
    direction = "up" if d > 0 else "down"
    return (txt, direction)


# ---------------------------------------------------------------------------
# Section A — Page header
# ---------------------------------------------------------------------------

st.markdown(
    render_page_header(
        eyebrow="Sida 01 · Nationell översikt",
        title="Riksöversikt",
        subtitle="Strukturell ekonomisk sårbarhet i Sveriges 290 kommuner",
        year=str(selected_year),
    ),
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Section B — KPI row
# ---------------------------------------------------------------------------

median_kri_val = float(filtered_df["kri_score"].median()) if len(filtered_df) else 0.0
high_risk_count = int((filtered_df["risk_class"] == "Hög").sum())
median_debt = float(filtered_df["debt_per_capita"].median()) if len(filtered_df) else 0.0
pop_change = float(filtered_df["population_growth"].mean()) if len(filtered_df) else 0.0

d1, dir1 = _delta_kri_median()
d2, dir2 = _delta_high_risk()
d3, dir3 = _delta_median_debt_pct()
d4, dir4 = _delta_pop_mean()

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    st.markdown(
        render_kpi_card(
            label="Median KRI",
            value=_fmt_decimal(median_kri_val, 2),
            unit=" std",
            delta=d1 or "Saknas",
            delta_direction=dir1,
            variant="primary",
        ),
        unsafe_allow_html=True,
    )
with kpi_col2:
    st.markdown(
        render_kpi_card(
            label=SWEDISH_LABELS["high_risk_count"],
            value=str(high_risk_count),
            unit=f" / {len(filtered_df)}",
            delta=d2 or "Saknas",
            delta_direction=dir2,
            variant="danger",
        ),
        unsafe_allow_html=True,
    )
with kpi_col3:
    st.markdown(
        render_kpi_card(
            label=SWEDISH_LABELS["median_debt"],
            value=_fmt_int_space(median_debt),
            unit=" kr",
            delta=d3 or "Saknas",
            delta_direction=dir3,
            variant="accent",
        ),
        unsafe_allow_html=True,
    )
with kpi_col4:
    st.markdown(
        render_kpi_card(
            label=SWEDISH_LABELS["population_change"],
            value=f"{'+' if pop_change > 0 else ''}{_fmt_decimal(pop_change, 2)}",
            unit=" %",
            delta=d4 or "Saknas",
            delta_direction=dir4,
            variant="success",
        ),
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section C — Map + distribution
# ---------------------------------------------------------------------------

scores = filtered_df["kri_score"].astype(float).tolist()
median_kri = float(filtered_df["kri_score"].median()) if len(filtered_df) else 0.0
if not scores:
    scores = year_df["kri_score"].astype(float).tolist()
    median_kri = float(year_df["kri_score"].median())

map_col, dist_col = st.columns([1.55, 1.0], gap="medium")

_risk_key = "alla" if not selected_risks else "-".join(sorted(selected_risks))

with map_col:
    with st.container(border=True):
        st.markdown(
            render_card_header(
                "Geografisk fördelning",
                "Kommunpolygoner färgade efter KRI (290 kommuner)",
                "Koropletkarta",
            ),
            unsafe_allow_html=True,
        )
        render_choropleth(filtered_df, selected_year, height=440)
    with st.expander("Om kartan", expanded=False):
        st.caption(
            "**Geografisk fördelning** visar varje kommuns geografiska polygon fylld med en färg "
            "som återger KRI-poängen: **grön** = låg risk, **gul** = medel, **röd** = hög. "
            "Färgskalan sträcker sig från −2,5 (lägst risk) till +2,5 (högst risk) och visas som "
            "legend längst ner i kartan. Hovra över en kommun för detaljerad information om "
            "KRI-poäng, rang, skuld per capita, arbetslöshet, befolkningstillväxt och skattekraft. "
            "Kartan kan panoreras och zoomas. Riskfiltret i sidopanelen påverkar vilka kommuner "
            "som inkluderas i beräkningarna ovan, men kartan visar alltid det valda årets data."
        )

with dist_col:
    with st.container(border=True):
        _dist_view = st.segmented_control(
            "Vy",
            options=["KRI (normaliserad)", "Skuld per capita (rådata)"],
            default="KRI (normaliserad)",
            label_visibility="collapsed",
            key=f"dist_view_{selected_year}",
        )
        _show_raw = _dist_view == "Skuld per capita (rådata)"
        st.markdown(
            render_card_header(
                "KRI-fördelning" if not _show_raw else "Skuld per capita (rådata)",
                ("Fördelning av z-poäng över 290 kommuner" if not _show_raw
                 else "Fördelning av råvärden före normalisering"),
                "Histogram",
            ),
            unsafe_allow_html=True,
        )
        if _show_raw:
            raw_vals = year_df["debt_per_capita"].astype(float).tolist()
            raw_opt = build_raw_indicator_histogram(raw_vals, "Skuld per capita", "kr")
            st_echarts(options=raw_opt, height="400px", key=f"raw_hist_{selected_year}_{_risk_key}")
        else:
            hist_opt = build_distribution_histogram(scores, median_kri)
            st_echarts(options=hist_opt, height="400px", key=f"dist_{selected_year}_{_risk_key}")
    with st.expander("Om fördelningsgrafen", expanded=False):
        st.caption(
            "**Normaliserad KRI** visar det sammansatta riskindexet som viktat z-poänggenomsnitt "
            "av fem indikatorer (skuld, arbetslöshet, försörjningskvot, befolkningstillväxt, "
            "skattekraft). Värden nära 0 är genomsnittliga; negativa värden indikerar lägre risk "
            "än rikssnittet och positiva indikerar högre. Gröna staplar = låg risk (KRI < −0,67), "
            "gula = medel, röda = hög (KRI > +0,67). Den streckade linjen visar medianen. "
            "**Rådata (skuld)** visar skuld per capita i kronor *innan* z-poängsnormalisering, "
            "vilket illustrerar hur indexet omvandlar absoluta värden till jämförbara poäng."
        )

# ---------------------------------------------------------------------------
# Section D — Tables
# ---------------------------------------------------------------------------

top15_high = filtered_df.nsmallest(15, "rank").sort_values("rank")
top15_low = filtered_df.nlargest(15, "rank").sort_values("rank", ascending=False)


def _risk_pill_class(rc: str) -> str:
    return {"Hög": "hog", "Medel": "medel", "Låg": "lag"}.get(rc, "medel")


def _table_html(df: pd.DataFrame) -> str:
    rows = []
    for _, row in df.iterrows():
        rc = str(row["risk_class"])
        pill = _risk_pill_class(rc)
        kri = _fmt_decimal(float(row["kri_score"]), 2)
        rank = str(int(row["rank"])).zfill(2)
        code = str(row["municipality_code"]).zfill(4)
        name = MUNICIPALITIES.get(code, str(row.get("municipality_name", "")))
        rows.append(
            f"<tr><td class='rank-cell'>{rank}</td>"
            f"<td class='kommun-name'>{name}</td>"
            f"<td class='num'>{kri}</td>"
            f"<td><span class='risk-pill {pill}'>{rc}</span></td></tr>"
        )
    return (
        "<table class='kri-table'><thead><tr>"
        "<th>Rang</th><th>Kommun</th><th class='num'>KRI Poäng</th><th>Riskklass</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


with st.expander("Om rankningstabellerna", expanded=False):
    st.caption(
        "**Topp 15 högst risk** visar de 15 kommuner med lägst rang (rang 1 = mest sårbar) för "
        "valt år. **Topp 15 lägst risk** visar de 15 mest robusta kommunerna. KRI Poäng är det "
        "sammansatta z-poängindexet: ju högre värde, desto större strukturell sårbarhet. "
        "Riskklassen baseras på kvartilar: kommuner under 25:e percentilen klassas som Låg risk, "
        "kommuner över 75:e percentilen som Hög risk."
    )

tbl1, tbl2 = st.columns(2, gap="medium")

with tbl1:
    with st.container(border=True):
        st.markdown(
            render_card_header(
                SWEDISH_LABELS["top_highest_risk"],
                f"Mest sårbara kommuner {selected_year}",
                "Rankning",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(_table_html(top15_high), unsafe_allow_html=True)

with tbl2:
    with st.container(border=True):
        st.markdown(
            render_card_header(
                SWEDISH_LABELS["top_lowest_risk"],
                f"Mest robusta kommuner {selected_year}",
                "Rankning",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(_table_html(top15_low), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section E — Footer
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="footer-note">'
    "<div>Källa: SCB Statistikdatabasen · Arbetsförmedlingen · Kolada</div>"
    "<div><code>KRI v1.0</code> · Metod: viktad z-poäng kompositindex · N=290</div>"
    "</div>",
    unsafe_allow_html=True,
)
