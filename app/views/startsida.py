"""
Startsida: what KRI is, live headline numbers for the selected year, and two
explicit entry points into the analysis.
"""

from __future__ import annotations

import streamlit as st

from app.components.landing_visuals import render_index_visual_block
from app.data import load_kri_data, year_range, year_slice
from app.formatting import fmt_count_of, fmt_range_decimal
from app.styles.theme import (
    render_landing_hero,
    render_landing_nav_card,
    render_landing_nav_section_title,
    render_landing_stat_strip,
    render_landing_steps,
    render_landing_what_is_block,
)
from app.ui.shell import render_footer

kri_df = load_kri_data()
selected_year: int = st.session_state["selected_year"]
year_df = year_slice(kri_df, selected_year)
first_year, last_year = year_range(kri_df)
n_kom = int(year_df["municipality_code"].nunique())
n_high = int((year_df["risk_class"] == "Hög").sum())

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
                "value": fmt_range_decimal(year_df["kri_score"].min(), year_df["kri_score"].max()),
            },
            {"label": f"Hög risk ({selected_year})", "value": fmt_count_of(n_high, n_kom)},
            {"label": "Analysperiod", "value": f"{first_year} - {last_year}"},
            {"label": "Urval", "value": str(n_kom), "unit": " kommuner"},
        ]
    ),
    unsafe_allow_html=True,
)

# Primary entry points directly under the numbers.
with st.container(horizontal=True, gap="small", key="lp_cta"):
    st.page_link(
        "views/riksoversikt.py", label="Öppna riksöversikten", icon=":material/map:"
    )
    st.page_link(
        "views/kommunanalys.py", label="Analysera en kommun", icon=":material/search:"
    )

st.space("small")

what_col, visual_col = st.columns([1.1, 1], gap="medium")
with what_col:
    st.markdown(
        render_landing_what_is_block(
            title="Vad är KRI?",
            p1=(
                "KRI (kommunal riskindikator) är ett viktat sammansatt index som sammanför fem "
                f"nyckeltal till en enda sårbarhetspoäng per kommun och år. Indexet jämför alla "
                f"{n_kom} kommuner inbördes så att du snabbt ser var strukturella ekonomiska "
                "risker är koncentrerade."
            ),
            p2=(
                "Varje mått görs om till z-poäng mot alla kommuner samma år, viktas (skuld per "
                "capita och öppen arbetslöshet 25 % vardera, försörjningskvot 20 %, "
                "befolkningstillväxt och skattekraft 15 % vardera) och summeras till KRI. "
                "Riskklasserna är relativa: den fjärdedel av kommunerna som har högst KRI ett år "
                "klassas som Hög risk. KRI rangordnar kommuner mot varandra och är ingen prognos "
                "för enskilda kommuners ekonomi."
            ),
        ),
        unsafe_allow_html=True,
    )
with visual_col:
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
                f"Varje mått görs om till z-poäng samma år, så att alla {n_kom} kommuner mäts "
                "på samma skala.",
                "normalize",
            ),
            (
                "Steg 3",
                "Klassificering",
                "KRI delas in i tre riskklasser efter årets kvartiler: lägsta fjärdedelen Låg, "
                "högsta fjärdedelen Hög, övriga Medel.",
                "classify",
            ),
        ]
    ),
    unsafe_allow_html=True,
)

st.markdown(render_landing_nav_section_title("Vad hittar du här?"), unsafe_allow_html=True)
_cards = [
    ("Riksöversikt", "Karta, nyckeltal och KRI-fördelning för alla kommuner.", "map",
     "views/riksoversikt.py"),
    ("Kommunanalys", "Nyckeltal, trender, liknande kommuner och export för en kommun.", "search",
     "views/kommunanalys.py"),
    ("Riskdekomposition", "Vilka faktorer som driver en kommuns risk, och jämförelser.", "layers",
     "views/riskdekomposition.py"),
]
for col, (title, desc, icon, path) in zip(st.columns(3, gap="medium"), _cards):
    with col:
        with st.container(border=True):
            st.markdown(
                render_landing_nav_card(title=title, desc=desc, icon=icon),  # type: ignore[arg-type]
                unsafe_allow_html=True,
            )
            st.page_link(path, label=f"Gå till {title}", icon=":material/arrow_forward:")

render_footer(first_year, last_year)
