"""
app/main.py
-----------
Entry point for the KRI Streamlit dashboard.

Applies the global theme, loads KRI data once (cached), and provides a shared
sidebar used by every page.  Run with:

    streamlit run app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make project root importable regardless of working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from app.styles.theme import apply_streamlit_theme, render_sidebar_header, render_data_source_footer
from src.config import SWEDISH_LABELS, START_YEAR, END_YEAR

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


# Expose data so pages can import it without re-loading.
kri_df = load_kri_data()

# ---------------------------------------------------------------------------
# Shared sidebar controls (written here so every page inherits them via
# st.session_state).
# ---------------------------------------------------------------------------

render_sidebar_header(subtitle="Kommunal Finansiell Riskindikator")

available_years = sorted(kri_df["year"].unique().tolist())
default_year = max(available_years)

selected_year: int = st.sidebar.slider(
    SWEDISH_LABELS["select_year"],
    min_value=min(available_years),
    max_value=max(available_years),
    value=default_year,
    step=1,
    format="%d",
)

risk_options = ["Alla", "Hög", "Medel", "Låg"]
selected_risk: str = st.sidebar.selectbox(
    SWEDISH_LABELS["filter_risk_class"],
    options=risk_options,
    index=0,
)

# Persist selections so page files can access them.
st.session_state["selected_year"] = selected_year
st.session_state["selected_risk"] = selected_risk
st.session_state["kri_df"] = kri_df

render_data_source_footer()

# ---------------------------------------------------------------------------
# Landing page content (shown when navigating directly to main.py).
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div style='text-align:center; padding: 3rem 1rem 1rem;'>
        <h1 style='font-size:36px;'>Kommunal Finansiell Riskindikator</h1>
        <p style='font-size:18px; color:#6B7280;'>
            Datadriven analys av strukturell ekonomisk sårbarhet i svenska kommuner
        </p>
        <p style='font-size:15px; color:#6B7280; margin-top:0.5rem;'>
            Välj en sida i sidofältet för att börja utforska.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)
with col1:
    st.info("**Riksöversikt** — nationell karta och fördelning av KRI-poäng")
with col2:
    st.info("**Riskdekomposition** — vilka faktorer driver risken i varje kommun")
with col3:
    st.info("**Kommunanalys** — djupdykning per kommun med trendanalys och jämförelsekommuner")
