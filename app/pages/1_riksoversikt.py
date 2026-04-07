"""
app/pages/1_riksoversikt.py
---------------------------
Page 1: Riksöversikt — national overview of KRI scores for all 290 municipalities.

Layout
------
ROW 1  Title + subtitle + selected year
ROW 2  KPI cards (4 columns)
ROW 3  Sweden map (60 %) + Distribution histogram (40 %)
ROW 4  Top-15 highest risk table + Top-15 lowest risk table

All user-facing text is in Swedish.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import urllib.request

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.styles.theme import (
    COLORS,
    apply_streamlit_theme,
    get_plotly_template,
    get_risk_color,
    render_kpi_card,
    render_sidebar_header,
    render_data_source_footer,
)
from src.config import SWEDISH_LABELS, START_YEAR, END_YEAR, MUNICIPALITIES

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
apply_streamlit_theme()
render_sidebar_header(subtitle="Riksöversikt")

# ---------------------------------------------------------------------------
# Data — reuse cached copy from session_state if available, otherwise load.
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

# ---------------------------------------------------------------------------
# Sidebar controls (mirrors main.py; independent when page opened directly)
# ---------------------------------------------------------------------------
available_years = sorted(kri_df["year"].unique().tolist())
default_year = st.session_state.get("selected_year", max(available_years))

selected_year: int = st.sidebar.slider(
    SWEDISH_LABELS["select_year"],
    min_value=min(available_years),
    max_value=max(available_years),
    value=default_year,
    step=1,
    format="%d",
)

risk_options = ["Alla", "Hög", "Medel", "Låg"]
default_risk = st.session_state.get("selected_risk", "Alla")
selected_risk: str = st.sidebar.selectbox(
    SWEDISH_LABELS["filter_risk_class"],
    options=risk_options,
    index=risk_options.index(default_risk) if default_risk in risk_options else 0,
)

render_data_source_footer()

# Filter data for the selected year
year_df = kri_df[kri_df["year"] == selected_year].copy()

if selected_risk != "Alla":
    filtered_df = year_df[year_df["risk_class"] == selected_risk].copy()
else:
    filtered_df = year_df.copy()

# Previous year for deltas
prev_year = selected_year - 1
prev_df = kri_df[kri_df["year"] == prev_year] if prev_year in kri_df["year"].values else pd.DataFrame()

# ---------------------------------------------------------------------------
# Helper: compute delta vs previous year
# ---------------------------------------------------------------------------

def _delta(col: str, agg="mean") -> float | None:
    if prev_df.empty:
        return None
    cur = year_df[col].agg(agg)
    prv = prev_df[col].agg(agg)
    return round(float(cur - prv), 2)


# ---------------------------------------------------------------------------
# ROW 1 — Title
# ---------------------------------------------------------------------------

st.markdown(
    f"""
    <div style='margin-bottom:0.2rem;'>
        <h1>Riksöversikt</h1>
        <p style='font-size:16px; color:{COLORS["text_secondary"]}; margin-top:-0.4rem;'>
            Strukturell ekonomisk sårbarhet i Sveriges 290 kommuner
            &nbsp;|&nbsp;
            <strong style='color:{COLORS["primary"]};'>År {selected_year}</strong>
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# ROW 2 — KPI Cards
# ---------------------------------------------------------------------------

avg_kri = round(float(year_df["kri_score"].mean()), 3)
high_risk_count = int((year_df["risk_class"] == "Hög").sum())
median_debt = round(float(year_df["debt_per_capita"].median()), 0)

# National population change: sum population growth across municipalities weighted equally
pop_change = round(float(year_df["population_growth"].mean()), 2)

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    render_kpi_card(
        title=SWEDISH_LABELS["average_kri"],
        value=avg_kri,
        delta=_delta("kri_score", "mean"),
        delta_inverted=True,
        help_text="Genomsnittligt KRI-poäng för alla 290 kommuner det valda året",
    )

with kpi_col2:
    render_kpi_card(
        title=SWEDISH_LABELS["high_risk_count"],
        value=high_risk_count,
        delta=_delta("risk_class", lambda s: (s == "Hög").sum()) if not prev_df.empty else None,
        delta_inverted=True,
        help_text="Antal kommuner klassificerade som högrisk (över 75:e percentilen)",
    )

with kpi_col3:
    render_kpi_card(
        title=SWEDISH_LABELS["median_debt"],
        value=median_debt,
        suffix=" kr",
        delta=_delta("debt_per_capita", "median"),
        delta_inverted=True,
        help_text="Medianskuld per capita (långfristiga skulder) bland alla kommuner",
    )

with kpi_col4:
    render_kpi_card(
        title=SWEDISH_LABELS["population_change"],
        value=pop_change,
        suffix=" %",
        delta=_delta("population_growth", "mean"),
        delta_inverted=False,
        help_text="Genomsnittlig 5-årig befolkningstillväxt bland alla kommuner",
    )

st.markdown("<div style='margin-top:1.4rem;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# GeoJSON loader (cached)
# ---------------------------------------------------------------------------

GEOJSON_LOCAL = PROJECT_ROOT / "data" / "geo" / "kommuner.geojson"
GEOJSON_URL = (
    "https://raw.githubusercontent.com/okfse/sweden-geojson/master/swedish_municipalities.geojson"
)


@st.cache_data(show_spinner="Laddar kartdata…")
def load_geojson() -> dict | None:
    """Try local file first, then remote URL, then return None for fallback."""
    if GEOJSON_LOCAL.exists():
        with open(GEOJSON_LOCAL, encoding="utf-8") as fh:
            return json.load(fh)
    try:
        with urllib.request.urlopen(GEOJSON_URL, timeout=10) as resp:
            data = json.load(resp)
        GEOJSON_LOCAL.parent.mkdir(parents=True, exist_ok=True)
        with open(GEOJSON_LOCAL, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return data
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ROW 3 — Map + Distribution chart
# ---------------------------------------------------------------------------

map_col, dist_col = st.columns([6, 4], gap="large")

# ---- Map ----------------------------------------------------------------

with map_col:
    st.markdown(
        f"<h2 style='margin-bottom:0.4rem;'>Riskkarta {selected_year}</h2>",
        unsafe_allow_html=True,
    )

    geojson = load_geojson()

    risk_order = {"Hög": 2, "Medel": 1, "Låg": 0}
    year_df["risk_numeric"] = year_df["risk_class"].map(risk_order)

    if geojson is not None:
        # Detect the feature property that holds municipality code
        sample_props = geojson["features"][0]["properties"] if geojson["features"] else {}
        code_key = next(
            (k for k in sample_props if "kommunkod" in k.lower() or k.lower() in ("id", "code", "municipalitycode")),
            list(sample_props.keys())[0] if sample_props else "id",
        )

        # Build merge key; GeoJSON codes may be strings without leading zeros
        year_df["geo_code"] = year_df["municipality_code"].astype(str)

        hover_text = (
            "<b>%{customdata[0]}</b><br>"
            "KRI Poäng: %{customdata[1]:.3f}<br>"
            "Rang: %{customdata[2]} av 290<br>"
            "Riskklass: %{customdata[3]}<br>"
            "Skuld per capita: %{customdata[4]:,.0f} kr<br>"
            "Arbetslöshet: %{customdata[5]:.1f} %"
            "<extra></extra>"
        )

        fig_map = px.choropleth_mapbox(
            year_df,
            geojson=geojson,
            locations="geo_code",
            featureidkey=f"properties.{code_key}",
            color="risk_class",
            color_discrete_map={
                "Låg": COLORS["low_risk"],
                "Medel": COLORS["medium_risk"],
                "Hög": COLORS["high_risk"],
            },
            category_orders={"risk_class": ["Låg", "Medel", "Hög"]},
            mapbox_style="white-bg",
            center={"lat": 63.5, "lon": 17.0},
            zoom=3.8,
            opacity=0.8,
            custom_data=[
                "municipality_name", "kri_score", "rank",
                "risk_class", "debt_per_capita", "unemployment",
            ],
            labels={"risk_class": "Riskklass"},
        )
        fig_map.update_traces(hovertemplate=hover_text)
        fig_map.update_layout(
            **get_plotly_template()["layout"],
            height=540,
            margin={"l": 0, "r": 0, "t": 0, "b": 0},
            legend=dict(
                title="Riskklass",
                orientation="v",
                x=0.01, y=0.98,
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor=COLORS["border"],
                borderwidth=1,
            ),
            modebar_remove=["logo"],
        )
        st.plotly_chart(fig_map, use_container_width=True)

    else:
        # Fallback: scatter plot with approximate municipality centroids
        # Use a simplified lat/lon mapping for major municipalities
        st.info(
            "Kartdata kunde inte laddas. Visar alternativ punktkarta. "
            "Kontrollera internetanslutningen för att läsa in fullständig karta."
        )

        # Build a simple scatter fallback coloured by risk class
        fig_scatter = px.scatter(
            year_df.sort_values("rank"),
            x="tax_base_relative",
            y="kri_score",
            color="risk_class",
            color_discrete_map={
                "Låg": COLORS["low_risk"],
                "Medel": COLORS["medium_risk"],
                "Hög": COLORS["high_risk"],
            },
            hover_name="municipality_name",
            hover_data={
                "kri_score": ":.3f",
                "rank": True,
                "debt_per_capita": ":,.0f",
                "unemployment": ":.1f",
                "risk_class": True,
                "tax_base_relative": ":.1f",
            },
            labels={
                "kri_score": "KRI Poäng",
                "tax_base_relative": "Skattekraft (% av rikssnitt)",
                "risk_class": "Riskklass",
                "rank": "Rang",
                "debt_per_capita": "Skuld per capita (kr)",
                "unemployment": "Arbetslöshet (%)",
            },
            title=f"KRI Poäng mot Skattekraft — {selected_year}",
        )
        fig_scatter.update_layout(
            **get_plotly_template()["layout"],
            height=500,
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

# ---- Distribution histogram ----------------------------------------------

with dist_col:
    st.markdown(
        f"<h2 style='margin-bottom:0.4rem;'>Fördelning KRI Poäng</h2>",
        unsafe_allow_html=True,
    )

    q25 = float(year_df["kri_score"].quantile(0.25))
    q75 = float(year_df["kri_score"].quantile(0.75))
    median_kri = float(year_df["kri_score"].median())
    kri_min = float(year_df["kri_score"].min())
    kri_max = float(year_df["kri_score"].max())

    fig_hist = go.Figure()

    # Risk zone background shapes
    fig_hist.add_shape(
        type="rect", xref="x", yref="paper",
        x0=kri_min - 0.1, x1=q25, y0=0, y1=1,
        fillcolor=COLORS["high_risk"], opacity=0.08, line_width=0,
    )
    fig_hist.add_shape(
        type="rect", xref="x", yref="paper",
        x0=q25, x1=q75, y0=0, y1=1,
        fillcolor=COLORS["medium_risk"], opacity=0.08, line_width=0,
    )
    fig_hist.add_shape(
        type="rect", xref="x", yref="paper",
        x0=q75, x1=kri_max + 0.1, y0=0, y1=1,
        fillcolor=COLORS["low_risk"], opacity=0.08, line_width=0,
    )

    # Histogram bars coloured by risk class
    for rc, colour in [("Hög", COLORS["high_risk"]), ("Medel", COLORS["medium_risk"]), ("Låg", COLORS["low_risk"])]:
        subset = year_df[year_df["risk_class"] == rc]["kri_score"]
        fig_hist.add_trace(go.Histogram(
            x=subset,
            name=rc,
            marker_color=colour,
            opacity=0.85,
            nbinsx=25,
            hovertemplate=f"<b>{rc} risk</b><br>KRI Poäng: %{{x:.2f}}<br>Antal: %{{y}}<extra></extra>",
        ))

    # Median line
    fig_hist.add_shape(
        type="line", xref="x", yref="paper",
        x0=median_kri, x1=median_kri, y0=0, y1=1,
        line=dict(color=COLORS["primary"], width=2, dash="dash"),
    )
    fig_hist.add_annotation(
        x=median_kri, yref="paper", y=0.97,
        text=f"Median: {median_kri:.2f}",
        showarrow=False,
        font=dict(size=11, color=COLORS["primary"]),
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor=COLORS["border"],
        borderwidth=1,
        xanchor="left",
    )

    fig_hist.update_layout(
        **get_plotly_template()["layout"],
        barmode="overlay",
        height=500,
        xaxis_title="KRI Poäng",
        yaxis_title="Antal kommuner",
        legend=dict(
            title="Riskklass",
            orientation="v",
            x=0.98, xanchor="right", y=0.98,
        ),
        margin={"l": 50, "r": 20, "t": 30, "b": 50},
    )

    # Risk zone labels
    fig_hist.add_annotation(
        x=(kri_min + q25) / 2, yref="paper", y=0.92,
        text="Hög", showarrow=False,
        font=dict(size=11, color=COLORS["high_risk"], weight="bold"),
    )
    fig_hist.add_annotation(
        x=(q25 + q75) / 2, yref="paper", y=0.92,
        text="Medel", showarrow=False,
        font=dict(size=11, color=COLORS["medium_risk"], weight="bold"),
    )
    fig_hist.add_annotation(
        x=(q75 + kri_max) / 2, yref="paper", y=0.92,
        text="Låg", showarrow=False,
        font=dict(size=11, color=COLORS["low_risk"], weight="bold"),
    )

    st.plotly_chart(fig_hist, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ROW 4 — Top-15 highest and lowest risk tables
# ---------------------------------------------------------------------------

def _format_table(df_in: pd.DataFrame) -> pd.DataFrame:
    """Return a display-ready DataFrame with Swedish column headers."""
    cols = {
        "rank": "Rang",
        "municipality_name": "Kommun",
        "kri_score": "KRI Poäng",
        "risk_class": "Riskklass",
        "debt_per_capita": "Skuld/capita (kr)",
        "unemployment": "Arbetslöshet (%)",
    }
    out = df_in[list(cols.keys())].rename(columns=cols).copy()
    out["KRI Poäng"] = out["KRI Poäng"].round(3)
    out["Skuld/capita (kr)"] = out["Skuld/capita (kr)"].apply(lambda v: f"{v:,.0f}".replace(",", "\u202f"))
    out["Arbetslöshet (%)"] = out["Arbetslöshet (%)"].round(1)
    out = out.reset_index(drop=True)
    return out


top15_high = year_df.nsmallest(15, "rank").sort_values("rank")
top15_low = year_df.nlargest(15, "rank").sort_values("rank", ascending=False)

tbl_col1, tbl_col2 = st.columns(2, gap="large")

with tbl_col1:
    st.markdown(
        f"<h2>{SWEDISH_LABELS['top_highest_risk']}</h2>",
        unsafe_allow_html=True,
    )
    st.dataframe(
        _format_table(top15_high),
        use_container_width=True,
        hide_index=True,
    )

with tbl_col2:
    st.markdown(
        f"<h2>{SWEDISH_LABELS['top_lowest_risk']}</h2>",
        unsafe_allow_html=True,
    )
    st.dataframe(
        _format_table(top15_low),
        use_container_width=True,
        hide_index=True,
    )

# ---------------------------------------------------------------------------
# Footer note
# ---------------------------------------------------------------------------
st.markdown(
    f"<p style='font-size:12px; color:{COLORS['text_secondary']}; margin-top:1rem;'>"
    f"{SWEDISH_LABELS['data_source']} &nbsp;|&nbsp; Period: {START_YEAR}–{END_YEAR} &nbsp;|&nbsp; "
    f"Riskklass baseras på 25:e och 75:e percentilen per år."
    f"</p>",
    unsafe_allow_html=True,
)
