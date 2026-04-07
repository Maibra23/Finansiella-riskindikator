"""
Page 3: Kommunanalys — deep dive for a single municipality.

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

from app.components.charts import build_line_trend
from app.styles.theme import (
    apply_streamlit_theme,
    render_card_header,
    render_kpi_card,
    render_page_header,
)
from src.clustering import get_peer_municipalities
from src.config import MUNICIPALITIES, SWEDISH_LABELS
from src.validators import get_data_quality_summary, get_municipality_flags

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
    key="ka_year_pills",
)
selected_year: int = int(_year_raw) if _year_raw is not None else default_year
st.session_state["selected_year"] = selected_year

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.markdown(render_page_header(
    eyebrow="Kommunanalys",
    title=SWEDISH_LABELS["municipality_analysis"],
    subtitle="Detaljerad genomgång av en kommuns finansiella riskprofil.",
    year=str(selected_year),
), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ROW 1: Municipality selector
# ---------------------------------------------------------------------------

year_df = kri_df[kri_df["year"] == selected_year].copy()
year_df = year_df.sort_values("municipality_name")

all_names = year_df["municipality_name"].tolist()
all_codes = [str(c).zfill(4) for c in year_df["municipality_code"].tolist()]
name_to_code = {n: c for n, c in zip(all_names, all_codes)}
code_to_name = {c: n for n, c in zip(all_names, all_codes)}

# Use session state to remember selection across pages
prev_selection = st.session_state.get("selected_municipality", all_names[0])
default_idx = all_names.index(prev_selection) if prev_selection in all_names else 0

selected_name: str = st.selectbox(
    SWEDISH_LABELS["select_municipality"],
    options=all_names,
    index=default_idx,
    key="ka_muni_select",
)
st.session_state["selected_municipality"] = selected_name
selected_code = name_to_code.get(selected_name, all_codes[0])

sel_row = year_df[year_df["municipality_code"] == selected_code]
if sel_row.empty:
    st.warning("Ingen data tillgänglig för vald kommun och år.")
    st.stop()
sel_row = sel_row.iloc[0]

risk_colors = {"Låg": "#2E7D5B", "Medel": "#D4A03C", "Hög": "#B94A48"}
risk = str(sel_row["risk_class"])
risk_color = risk_colors.get(risk, "#6B7280")

st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:16px;margin:8px 0 20px 0;">
        <span style="background:{risk_color};color:#fff;border-radius:4px;
                     padding:3px 12px;font-size:13px;font-weight:600;">{risk}</span>
        <span style="color:#6B7280;font-size:14px;">
            KRI {float(sel_row['kri_score']):.2f} &nbsp;·&nbsp;
            Rang {int(sel_row['rank'])} av 290
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# ROW 2: 6 KPI cards
# ---------------------------------------------------------------------------


def _delta_info(
    current_val: float, prev_val: float | None, higher_is_worse: bool = True
) -> tuple[str, str]:
    """Return (delta_str, delta_direction) for render_kpi_card."""
    if prev_val is None or pd.isna(prev_val):
        return "–", "flat"
    diff = current_val - prev_val
    sign = "+" if diff >= 0 else ""
    delta_str = f"{sign}{diff:.2f}"
    if abs(diff) < 1e-6:
        direction = "flat"
    elif diff > 0:
        direction = "down" if higher_is_worse else "up"
    else:
        direction = "up" if higher_is_worse else "down"
    return delta_str, direction


prev_year = selected_year - 1
prev_row_df = kri_df[
    (kri_df["municipality_code"] == selected_code) & (kri_df["year"] == prev_year)
]
prev_row = prev_row_df.iloc[0] if not prev_row_df.empty else None


def _pv(col: str) -> float | None:
    return float(prev_row[col]) if prev_row is not None else None  # type: ignore[index]


kpi_cols = st.columns(6)

kpi_defs: list[tuple[str, str, str, str, str, str]] = [
    (
        "KRI Poäng",
        f"{float(sel_row['kri_score']):.2f}", "",
        *_delta_info(float(sel_row["kri_score"]), _pv("kri_score"), higher_is_worse=True),
        "primary",
    ),
    (
        SWEDISH_LABELS["rank"],
        str(int(sel_row["rank"])), "/ 290",
        *_delta_info(float(sel_row["rank"]), _pv("rank"), higher_is_worse=True),
        "primary",
    ),
    (
        SWEDISH_LABELS["debt_per_capita"],
        f"{float(sel_row['debt_per_capita']):,.0f}".replace(",", "\u202f"),
        SWEDISH_LABELS["kr"],
        *_delta_info(float(sel_row["debt_per_capita"]), _pv("debt_per_capita"), higher_is_worse=True),
        "danger",
    ),
    (
        "Arbetslöshet",
        f"{float(sel_row['unemployment']):.1f}",
        SWEDISH_LABELS["percent"],
        *_delta_info(float(sel_row["unemployment"]), _pv("unemployment"), higher_is_worse=True),
        "danger",
    ),
    (
        "Försörjningskvot",
        f"{float(sel_row['dependency_ratio']):.3f}", "",
        *_delta_info(float(sel_row["dependency_ratio"]), _pv("dependency_ratio"), higher_is_worse=True),
        "primary",
    ),
    (
        f"{SWEDISH_LABELS['tax_base']} (% av rikssnitt)",
        f"{float(sel_row['tax_base_relative']):.1f}",
        SWEDISH_LABELS["percent"],
        *_delta_info(float(sel_row["tax_base_relative"]), _pv("tax_base_relative"), higher_is_worse=False),
        "success",
    ),
]

for col, (label, value, unit, delta_str, delta_dir, variant) in zip(kpi_cols, kpi_defs):
    with col:
        st.markdown(
            render_kpi_card(label, value, unit, delta_str, delta_dir, variant),  # type: ignore[arg-type]
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ROW 3: Trend line chart
# ---------------------------------------------------------------------------

st.markdown(render_card_header(
    title="KRI-trend 2010–2024",
    subtitle=f"Historisk KRI-poäng för {selected_name} jämfört med rikssnittet",
    tag="Tidserie",
), unsafe_allow_html=True)

all_years = sorted(kri_df["year"].unique().tolist())
muni_vals: list[float] = []
rikssnitt_vals: list[float] = []

for yr in all_years:
    yr_df = kri_df[kri_df["year"] == yr]
    muni_yr = yr_df[yr_df["municipality_code"] == selected_code]
    muni_vals.append(float(muni_yr["kri_score"].iloc[0]) if not muni_yr.empty else float("nan"))
    rikssnitt_vals.append(float(yr_df["kri_score"].mean()))

trend_series = {selected_name: muni_vals, "Rikssnitt": rikssnitt_vals}
trend_opts = build_line_trend(all_years, trend_series)
st_echarts(trend_opts, height="360px", key=f"ka_trend_{selected_code}_{selected_year}")

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ROW 4: Peer comparison table
# ---------------------------------------------------------------------------

st.markdown(render_card_header(
    title=SWEDISH_LABELS["similar_municipalities"],
    subtitle="Kommuner med likartad riskprofil baserat på alla fem z-poängvariabler",
    tag="Peer-analys",
), unsafe_allow_html=True)

try:
    peer_df = get_peer_municipalities(selected_code, kri_df, n=10, year=selected_year)
    if not peer_df.empty:
        # Join raw indicator columns from kri_df
        extra_cols = ["municipality_code", "rank", "debt_per_capita", "unemployment",
                      "dependency_ratio", "population_growth", "tax_base_relative"]
        extra = kri_df[kri_df["year"] == selected_year][extra_cols].copy()
        peer_df = peer_df.merge(extra, on="municipality_code", how="left")

        display_peers = peer_df.copy()
        display_peers["Rang"] = display_peers["rank"].astype(int)
        display_peers["KRI"] = display_peers["kri_score"].map("{:.2f}".format)
        display_peers["Riskklass"] = display_peers["risk_class"]
        display_peers["Skuld (kr)"] = display_peers["debt_per_capita"].map(
            lambda x: f"{x:,.0f}".replace(",", "\u202f")
        )
        display_peers["Arbetslöshet (%)"] = display_peers["unemployment"].map("{:.1f}".format)
        display_peers["Försörjning"] = display_peers["dependency_ratio"].map("{:.3f}".format)
        display_peers["Befolkning (%)"] = display_peers["population_growth"].map("{:.1f}".format)
        display_peers["Skattekraft (%)"] = display_peers["tax_base_relative"].map("{:.1f}".format)
        display_peers["Avstånd"] = display_peers["distance"].map("{:.3f}".format)

        show_cols = [
            "Rang", "municipality_name", "Riskklass", "KRI",
            "Skuld (kr)", "Arbetslöshet (%)", "Försörjning",
            "Befolkning (%)", "Skattekraft (%)", "Avstånd",
        ]
        st.dataframe(
            display_peers[show_cols].rename(columns={"municipality_name": "Kommun"}),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Peer-data saknas för vald kombination.")
except Exception as e:
    st.warning(f"Kunde inte beräkna peer-kommuner: {e}")

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ROW 5: Full historical data table + CSV download
# ---------------------------------------------------------------------------

st.markdown(render_card_header(
    title="Underliggande data – alla år",
    subtitle=f"Alla indikatorer för {selected_name}, 2010–2024",
    tag="Rådata",
), unsafe_allow_html=True)

muni_history = kri_df[kri_df["municipality_code"] == selected_code].copy()
muni_history = muni_history.sort_values("year", ascending=False)

display_history = muni_history[[
    "year", "kri_score", "rank", "risk_class",
    "debt_per_capita", "unemployment", "dependency_ratio",
    "population_growth", "tax_base_relative",
]].rename(columns={
    "year": "År",
    "kri_score": "KRI Poäng",
    "rank": "Rang",
    "risk_class": "Riskklass",
    "debt_per_capita": "Skuld per capita (kr)",
    "unemployment": "Arbetslöshet (%)",
    "dependency_ratio": "Försörjningskvot",
    "population_growth": "Befolkningstillväxt (%)",
    "tax_base_relative": "Skattekraft (% av rikssnitt)",
})

st.dataframe(display_history, use_container_width=True, hide_index=True)

csv_data = display_history.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")

dl_col1, dl_col2, dl_col3 = st.columns([2, 2, 6])
with dl_col1:
    st.download_button(
        label=SWEDISH_LABELS["download_data"],
        data=csv_data,
        file_name=f"kri_{selected_code}_{selected_name.replace(' ', '_')}.csv",
        mime="text/csv",
        key="ka_download_csv",
    )
with dl_col2:
    if st.button("📄 Ladda ner rapport (PDF)", key="ka_pdf_btn"):
        with st.spinner("Genererar PDF-rapport…"):
            try:
                from src.report_gen import generate_report
                pdf_bytes = generate_report(kri_df=kri_df, report_year=selected_year)
                st.download_button(
                    label=SWEDISH_LABELS["download_pdf"],
                    data=pdf_bytes,
                    file_name=f"kri_rapport_{selected_year}.pdf",
                    mime="application/pdf",
                    key="ka_download_pdf_actual",
                )
            except Exception as e:
                st.error(f"Kunde inte generera PDF: {e}")

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ROW 6: Data quality panel
# ---------------------------------------------------------------------------

with st.expander(f"📋 {SWEDISH_LABELS['data_quality']}", expanded=False):
    flags = get_municipality_flags(selected_code)
    if flags:
        for flag in flags:
            st.warning(flag)
    else:
        st.success("Inga kända datakvalitetsproblem för denna kommun.")

    # Completeness check for this municipality
    muni_cols = ["debt_per_capita", "unemployment", "dependency_ratio",
                 "population_growth", "tax_base_relative"]
    col_labels = {
        "debt_per_capita": "Skuld per capita",
        "unemployment": "Arbetslöshet",
        "dependency_ratio": "Försörjningskvot",
        "population_growth": "Befolkningstillväxt",
        "tax_base_relative": "Skattekraft",
    }
    missing_count = int(muni_history[muni_cols].isna().sum().sum())
    total_cells = len(muni_history) * len(muni_cols)
    complete_cells = total_cells - missing_count

    c1, c2, c3 = st.columns(3)
    c1.metric("Datapunkter totalt", f"{total_cells}")
    c2.metric("Kompletta", f"{complete_cells}")
    c3.metric("Saknade", f"{missing_count}")

    if missing_count > 0:
        st.markdown("**Saknade värden per variabel:**")
        for col in muni_cols:
            n_miss = int(muni_history[col].isna().sum())
            if n_miss > 0:
                st.markdown(f"- **{col_labels[col]}**: {n_miss} år saknas")

# ---------------------------------------------------------------------------
# Footer attribution
# ---------------------------------------------------------------------------
st.markdown(
    "<div style='margin-top:32px;padding-top:16px;border-top:1px solid #EEF0F3;"
    "font-size:11px;color:#9CA3AF;'>Källa: SCB, Arbetsförmedlingen/Kolada</div>",
    unsafe_allow_html=True,
)
