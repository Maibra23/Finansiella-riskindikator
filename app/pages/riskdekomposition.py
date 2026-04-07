"""
Page 2: Riskdekomposition — per-municipality risk driver analysis.

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

from app.components.charts import (
    build_grouped_bars_comparison,
    build_horizontal_contribution_bar,
    build_line_trend,
    build_radar,
)
from app.styles.theme import (
    apply_streamlit_theme,
    render_card_header,
    render_page_header,
)
from src.config import MUNICIPALITIES, SWEDISH_LABELS

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
apply_streamlit_theme()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
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
nav_items = [
    ("01", "riksoversikt.py", "Riksöversikt"),
    ("02", "riskdekomposition.py", "Riskdekomposition"),
    ("03", "kommunanalys.py", "Kommunanalys"),
    ("04", None, "Metod & källor"),
]
for num, fname, title in nav_items:
    if fname and (pages_dir / fname).exists():
        st.sidebar.page_link(f"pages/{fname}", label=f"{num}  {title}")
    else:
        st.sidebar.caption(f"{num}  {title}, kommer snart")
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

# Sidebar year
st.sidebar.markdown(
    f'<div class="sidebar-control"><div class="control-label">{SWEDISH_LABELS["select_year"]}</div></div>',
    unsafe_allow_html=True,
)
_year_raw = st.sidebar.pills(
    SWEDISH_LABELS["select_year"],
    options=available_years,
    default=default_year,
    label_visibility="collapsed",
    key="rd_year_pills",
)
selected_year: int = int(_year_raw) if _year_raw is not None else default_year
st.session_state["selected_year"] = selected_year

# ---------------------------------------------------------------------------
# Swedish label maps
# ---------------------------------------------------------------------------

CONTRIB_LABELS: dict[str, str] = {
    "contribution_debt": "Skuld per capita",
    "contribution_unemployment": "Arbetslöshet",
    "contribution_dependency": "Försörjningskvot",
    "contribution_population": "Befolkningstillväxt",
    "contribution_tax_base": "Skattekraft",
}

Z_SCORE_LABELS: dict[str, str] = {
    "z_debt": "Skuld",
    "z_unemployment": "Arbetslöshet",
    "z_dependency": "Försörjning",
    "z_population": "Befolkning",
    "z_tax_base": "Skattekraft",
}

CONTRIB_COLS = list(CONTRIB_LABELS.keys())
Z_COLS = list(Z_SCORE_LABELS.keys())

# ---------------------------------------------------------------------------
# Helper: build sorted municipality list for current year
# ---------------------------------------------------------------------------

year_df = kri_df[kri_df["year"] == selected_year].copy()
year_df = year_df.sort_values("rank")

muni_options = [
    str(row["municipality_name"])
    for _, row in year_df.iterrows()
]
muni_codes = [
    str(row["municipality_code"]).zfill(4)
    for _, row in year_df.iterrows()
]
code_to_name = {c: n for c, n in zip(muni_codes, muni_options)}
name_to_code = {n: c for c, n in zip(muni_codes, muni_options)}

# Default: highest-risk municipality
default_muni = muni_options[0] if muni_options else None

# ---------------------------------------------------------------------------
# ROW 1: Title + municipality dropdown
# ---------------------------------------------------------------------------

st.markdown(render_page_header(
    eyebrow="Analysverktyg",
    title=SWEDISH_LABELS["risk_decomposition"],
    subtitle="Identifiera vilka faktorer som driver risken i en enskild kommun.",
    year=str(selected_year),
), unsafe_allow_html=True)

col_left, col_right = st.columns([2, 1])
with col_left:
    selected_name = st.selectbox(
        "Välj kommun",
        options=muni_options,
        index=0,
        key="rd_muni_select",
    )

selected_code = name_to_code.get(selected_name, muni_codes[0] if muni_codes else "0180")
sel_row = year_df[year_df["municipality_code"] == selected_code]

if sel_row.empty:
    st.warning("Ingen data tillgänglig för vald kommun och år.")
    st.stop()

sel_row = sel_row.iloc[0]

with col_right:
    risk = str(sel_row["risk_class"])
    kri_val = float(sel_row["kri_score"])
    rank_val = int(sel_row["rank"])
    risk_colors = {"Låg": "#2E7D5B", "Medel": "#D4A03C", "Hög": "#B94A48"}
    color = risk_colors.get(risk, "#6B7280")
    st.markdown(
        f"""
        <div style="background:#FFFFFF;border:1px solid #EEF0F3;border-radius:8px;
                    padding:16px 20px;margin-top:28px;border-left:4px solid {color};">
            <div style="font-size:11px;color:#6B7280;text-transform:uppercase;
                        letter-spacing:1px;font-weight:600;margin-bottom:6px;">
                KRI {selected_year}
            </div>
            <div style="font-size:28px;font-weight:700;color:#1A1A2E;
                        font-family:'IBM Plex Mono',monospace;line-height:1;">
                {kri_val:.2f}
            </div>
            <div style="margin-top:8px;display:flex;gap:12px;align-items:center;">
                <span style="background:{color};color:#fff;border-radius:4px;
                             padding:2px 10px;font-size:12px;font-weight:600;">
                    {risk}
                </span>
                <span style="color:#6B7280;font-size:13px;">
                    Rang {rank_val} av 290
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ROW 2: Contribution bar + Radar chart
# ---------------------------------------------------------------------------

st.markdown(render_card_header(
    title="Riskbidrag per faktor",
    subtitle="Varje faktors bidrag till det totala KRI-värdet",
    tag="Dekomposition",
), unsafe_allow_html=True)

col_bar, col_radar = st.columns(2)

with col_bar:
    contributions: dict[str, float] = {
        CONTRIB_LABELS[col]: float(sel_row[col])
        for col in CONTRIB_COLS
    }
    bar_opts = build_horizontal_contribution_bar(contributions)
    st_echarts(bar_opts, height="320px", key=f"rd_contrib_bar_{selected_code}_{selected_year}")

with col_radar:
    national_avg = year_df[Z_COLS].mean()
    municipality_vals = [float(sel_row[col]) for col in Z_COLS]
    national_vals = [float(national_avg[col]) for col in Z_COLS]
    indicators = [Z_SCORE_LABELS[col] for col in Z_COLS]

    radar_opts = build_radar(municipality_vals, national_vals, indicators)
    st_echarts(radar_opts, height="320px", key=f"rd_radar_{selected_code}_{selected_year}")

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ROW 3: Multi-municipality comparison
# ---------------------------------------------------------------------------

st.markdown(render_card_header(
    title="Jämför kommuner",
    subtitle="Välj 2–5 kommuner för att jämföra riskbidrag sida vid sida",
    tag="Jämförelse",
), unsafe_allow_html=True)

default_compare = [selected_name] + [
    n for n in muni_options[1:5] if n != selected_name
][:3]

compare_names = st.multiselect(
    "Jämför kommuner",
    options=muni_options,
    default=default_compare[:4],
    max_selections=5,
    key="rd_compare_select",
    label_visibility="collapsed",
)

if len(compare_names) >= 2:
    compare_codes = [name_to_code[n] for n in compare_names if n in name_to_code]
    compare_df = year_df[year_df["municipality_code"].isin(compare_codes)].copy()
    compare_df["display_name"] = compare_df["municipality_code"].map(
        lambda c: code_to_name.get(str(c).zfill(4), c)
    )

    muni_display = compare_df["display_name"].tolist()
    components_data: dict[str, list[float]] = {}
    for col, label in CONTRIB_LABELS.items():
        components_data[label] = [
            float(compare_df[compare_df["display_name"] == n][col].iloc[0])
            if not compare_df[compare_df["display_name"] == n].empty else 0.0
            for n in muni_display
        ]

    grouped_opts = build_grouped_bars_comparison(muni_display, components_data)
    st_echarts(grouped_opts, height="360px", key=f"rd_grouped_{selected_year}")
else:
    st.info("Välj minst 2 kommuner för att aktivera jämförelsen.")

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ROW 4: KRI trend over time
# ---------------------------------------------------------------------------

st.markdown(render_card_header(
    title="KRI-trend 2010–2024",
    subtitle="Historisk utveckling av KRI-poäng för valda kommuner",
    tag="Tidserie",
), unsafe_allow_html=True)

# Use the comparison selection if >= 1, else just selected municipality
trend_names = compare_names if compare_names else [selected_name]
trend_codes = [name_to_code[n] for n in trend_names if n in name_to_code]

all_years = sorted(kri_df["year"].unique().tolist())
series_dict: dict[str, list[float]] = {}

for code in trend_codes:
    name = code_to_name.get(code, code)
    vals = []
    for yr in all_years:
        row = kri_df[(kri_df["municipality_code"] == code) & (kri_df["year"] == yr)]
        vals.append(float(row["kri_score"].iloc[0]) if not row.empty else float("nan"))
    series_dict[name] = vals

# Add national average
rikssnitt = []
for yr in all_years:
    yr_data = kri_df[kri_df["year"] == yr]["kri_score"]
    rikssnitt.append(float(yr_data.mean()) if not yr_data.empty else float("nan"))
series_dict["Rikssnitt"] = rikssnitt

trend_opts = build_line_trend(all_years, series_dict)
st_echarts(trend_opts, height="380px", key=f"rd_trend_{selected_year}")

# ---------------------------------------------------------------------------
# Footer attribution
# ---------------------------------------------------------------------------
st.markdown(
    "<div style='margin-top:32px;padding-top:16px;border-top:1px solid #EEF0F3;"
    "font-size:11px;color:#9CA3AF;'>Källa: SCB, Arbetsförmedlingen/Kolada</div>",
    unsafe_allow_html=True,
)
