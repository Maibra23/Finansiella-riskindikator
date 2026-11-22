"""
app/main.py
-----------
Router for the KRI Streamlit dashboard.

Applies the theme, loads the data once (cached), renders the one shared sidebar
(navigation + global year) and runs the selected page. Run with:

    streamlit run app/main.py

URL paths: / (Startsida), /riksoversikt, /kommunanalys, /riskdekomposition, /kallor.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.data import load_kri_data
from app.styles.theme import apply_streamlit_theme
from app.ui.shell import render_sidebar

# Theme first, so even a cold first visit shows the branded shell immediately.
apply_streamlit_theme()

PAGES: dict[str, st.Page] = {
    "startsida": st.Page("views/startsida.py", title="Startsida", icon=":material/home:", default=True),
    "riksoversikt": st.Page(
        "views/riksoversikt.py", title="Riksöversikt", icon=":material/map:", url_path="riksoversikt"
    ),
    "kommunanalys": st.Page(
        "views/kommunanalys.py", title="Kommunanalys", icon=":material/search:", url_path="kommunanalys"
    ),
    "riskdekomposition": st.Page(
        "views/riskdekomposition.py",
        title="Riskdekomposition",
        icon=":material/stacked_bar_chart:",
        url_path="riskdekomposition",
    ),
    "kallor": st.Page(
        "views/kallor.py", title="Källor och metod", icon=":material/menu_book:", url_path="kallor"
    ),
}

page = st.navigation(list(PAGES.values()), position="hidden")

kri_df = load_kri_data()
# Kept for backward compatibility: some code reads the frame from session state.
st.session_state["kri_df"] = kri_df

render_sidebar(PAGES, sorted(kri_df["year"].unique().tolist()))

page.run()
