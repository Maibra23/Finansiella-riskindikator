"""
app/main.py
-----------
Entry point for the KRI Streamlit dashboard.

Applies the global theme, loads KRI data once (cached), and provides a shared
sidebar used by every page. Run with:

    streamlit run app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from app.components.landing_visuals import render_index_visual_block
from app.styles.theme import (
    apply_streamlit_theme,
    render_landing_credibility,
    render_landing_hero,
    render_landing_nav_card,
    render_landing_nav_section_title,
    render_landing_stat_strip,
    render_landing_steps,
    render_landing_what_is_block,
)
from src.config import SWEDISH_LABELS

# ---------------------------------------------------------------------------
# Page configuration — must be the very first Streamlit call.
# ---------------------------------------------------------------------------
apply_streamlit_theme()

# ---------------------------------------------------------------------------
# Data loading (cached so every page reuses the same object).
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Laddar data…")
def load_kri_data() -> pd.DataFrame:
    """Load the processed KRI results parquet into memory."""
    parquet_path = PROJECT_ROOT / "data" / "processed" / "kri_results.parquet"
    if not parquet_path.exists():
        st.error(
            "Datafilen saknas. Kör datapipelinen (scripts/run_pipeline.py) "
            "för att generera kri_results.parquet."
        )
        st.stop()
    df = pd.read_parquet(parquet_path)
    df["year"] = df["year"].astype(int)
    return df


kri_df = load_kri_data()

# ---------------------------------------------------------------------------
# Sidebar: brand, navigation, filters
# ---------------------------------------------------------------------------

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

pages_dir = PROJECT_ROOT / "app" / "pages"
nav_items = [
    ("01", "1_riksoversikt.py", "Riksöversikt"),
    ("02", "2_riskdekomposition.py", "Riskdekomposition"),
    ("03", "3_kommunanalys.py", "Kommunanalys"),
    ("04", None, "Metod & källor"),
]

for num, fname, title in nav_items:
    if fname and (pages_dir / fname).exists():
        st.sidebar.page_link(f"pages/{fname}", label=f"{num}  {title}")
    else:
        st.sidebar.caption(f"{num}  {title}, kommer snart")

st.sidebar.markdown("<br/>", unsafe_allow_html=True)

available_years = sorted(kri_df["year"].unique().tolist())
default_year = max(available_years)

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
    key="main_year_pills",
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
_risks_raw = st.sidebar.pills(
    SWEDISH_LABELS["filter_risk_class"],
    options=["Hög", "Medel", "Låg"],
    selection_mode="multi",
    default=None,
    label_visibility="collapsed",
    key="main_risk_pills",
)
selected_risks: list[str] = list(_risks_raw) if _risks_raw else []
# Keep single-value alias for backward compatibility with pages that read session state
selected_risk: str = selected_risks[0] if len(selected_risks) == 1 else ("Alla" if not selected_risks else "Multi")

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
st.session_state["selected_risk"] = selected_risk
st.session_state["selected_risks"] = selected_risks
st.session_state["kri_df"] = kri_df

# ---------------------------------------------------------------------------
# Landing page (home)
# ---------------------------------------------------------------------------

def _fmt_decimal(val: float, nd: int = 2) -> str:
    """Format float with Swedish decimal comma; avoids '-0,00' from float signed zero."""
    v = round(float(val), nd)
    if abs(v) < 10 ** (-nd):
        v = 0.0
    s = f"{v:,.{nd}f}"
    if nd > 0:
        s = s.replace(",", "X").replace(".", ",").replace("X", "\u202f")
    else:
        s = s.replace(",", "\u202f")
    return s


_year_slice = kri_df[kri_df["year"] == selected_year]
# Mean KRI across municipalities is ~0 by construction (z-based index), so show span instead.
_kri_s = _year_slice["kri_score"].astype(float)
_kri_min = float(_kri_s.min()) if len(_kri_s) else 0.0
_kri_max = float(_kri_s.max()) if len(_kri_s) else 0.0
_high_risk_n = int((_year_slice["risk_class"] == "Hög").sum()) if len(_year_slice) else 0
_y_min = int(kri_df["year"].min())
_y_max = int(kri_df["year"].max())
_n_kom = int(_year_slice["municipality_code"].nunique()) if len(_year_slice) else 290

st.markdown(
    render_landing_hero(
        eyebrow="Kommunal finansiell analys",
        headline="Kommunal finansiell riskindikator",
        lead="Ett riskindex per kommun och år från fem nyckeltal.",
        cta="",
    ),
    unsafe_allow_html=True,
)

st.markdown(
    render_landing_stat_strip(
        [
            {
                "label": f"KRI-intervall ({selected_year})",
                "value": f"{_fmt_decimal(_kri_min, 2)} till {_fmt_decimal(_kri_max, 2)}",
                "unit": "",
            },
            {
                "label": "Kommuner med hög risk",
                "value": str(_high_risk_n),
                "unit": f" / {_n_kom}",
            },
            {
                "label": "Analysperiod",
                "value": f"{_y_min} till {_y_max}",
                "unit": "",
            },
            {
                "label": "Urval",
                "value": str(_n_kom),
                "unit": " kommuner",
            },
        ]
    ),
    unsafe_allow_html=True,
)

st.markdown(
    render_landing_what_is_block(
        title="Vad är KRI?",
        p1=(
            "KRI (kommunal riskindikator) är ett viktat sammansatt index som sammanför fem nyckeltal "
            "till en enda sårbarhetspoäng per kommun och år. Indexet jämför alla 290 kommuner inbördes "
            "så att du snabbt ser var strukturella risker är koncentrerade."
        ),
        p2=(
            "Z-poäng jämför varje mått mellan alla kommuner samma år, viktas (skuld per capita 25 %) "
            "och summeras till KRI. Exempel: flera värden tydligt över snitt ger högre KRI och ofta "
            "riskklassen Hög."
        ),
    ),
    unsafe_allow_html=True,
)

st.markdown(render_index_visual_block(), unsafe_allow_html=True)

st.markdown(
    render_landing_steps(
        [
            (
                "Steg 1",
                "Datahämtning",
                "Offentlig data från SCB och Kolada omräknas till jämförbara mått per kommun.",
                "data",
            ),
            (
                "Steg 2",
                "Normalisering",
                "Varje mått görs om till z-poäng samma år, så att alla 290 kommuner mäts på samma skala.",
                "normalize",
            ),
            (
                "Steg 3",
                "Klassificering",
                "KRI fördelas i tre riskklasser utifrån läget mellan kommunerna samma år, för spårbarhet.",
                "classify",
            ),
        ]
    ),
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.markdown(
        render_landing_nav_section_title("Vad hittar du här?", in_panel=True),
        unsafe_allow_html=True,
    )
    _nav_col1, _nav_col2, _nav_col3 = st.columns(3)
    with _nav_col1:
        st.markdown(
            render_landing_nav_card(
                tag="Sida 01",
                title="Riksöversikt",
                desc="Karta, nyckeltal och KRI-fördelning för alla kommuner.",
                icon="map",
            ),
            unsafe_allow_html=True,
        )
        st.page_link("pages/1_riksoversikt.py", label="Öppna Riksöversikt", use_container_width=True)
    with _nav_col2:
        if (pages_dir / "2_riskdekomposition.py").exists():
            st.markdown(
                render_landing_nav_card(
                    tag="Sida 02",
                    title="Riskdekomposition",
                    desc="Riskdrivare per vald kommun jämfört med riket.",
                    icon="layers",
                ),
                unsafe_allow_html=True,
            )
            st.page_link(
                "pages/2_riskdekomposition.py",
                label="Öppna Riskdekomposition",
                use_container_width=True,
            )
        else:
            st.markdown(
                render_landing_nav_card(
                    tag="Sida 02",
                    title="Riskdekomposition",
                    desc="Kommer snart. Djupdykning i vad som driver risken per kommun.",
                    icon="layers",
                ),
                unsafe_allow_html=True,
            )
            st.caption("Kommer snart")
    with _nav_col3:
        if (pages_dir / "3_kommunanalys.py").exists():
            st.markdown(
                render_landing_nav_card(
                    tag="Sida 03",
                    title="Kommunanalys",
                    desc="Trender och tabeller för vald kommun över tid.",
                    icon="search",
                ),
                unsafe_allow_html=True,
            )
            st.page_link(
                "pages/3_kommunanalys.py",
                label="Öppna Kommunanalys",
                use_container_width=True,
            )
        else:
            st.markdown(
                render_landing_nav_card(
                    tag="Sida 03",
                    title="Kommunanalys",
                    desc="Kommer snart. Detaljerad trend och jämförelsekommuner.",
                    icon="search",
                ),
                unsafe_allow_html=True,
            )
            st.caption("Kommer snart")

st.markdown(
    render_landing_credibility(
        pills=[
            "SCB",
            "Arbetsförmedlingen / Kolada",
            "KRI v1.0",
        ],
        meta="Offentliga datakällor",
    ),
    unsafe_allow_html=True,
)
