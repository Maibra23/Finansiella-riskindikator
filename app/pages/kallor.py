"""
Page: Källor — data sources and methodology overview.

Displays the full data source table from methodology section 2.1 plus
API and coverage details. All user-facing text is in Swedish.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from app.styles.theme import apply_streamlit_theme, render_card_header, render_page_header

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
apply_streamlit_theme()

# Sidebar — mirrors app/main.py
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
    ("kallor.py", "Källor"),
]
for fname, title in nav_items:
    if (pages_dir / fname).exists():
        st.sidebar.page_link(f"pages/{fname}", label=title)

st.sidebar.markdown("<br/>", unsafe_allow_html=True)
st.sidebar.markdown(
    """
    <div class="sidebar-footer">
        <strong>KÄLLA:</strong> SCB, Arbetsförmedlingen<br/>
        Senast uppdaterad 2024-12-31
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.markdown(
    render_page_header(
        eyebrow="KRI · Kommunal Finansiell Riskindikator",
        title="Datakällor & Metod",
        subtitle="Samtliga variabler i indexet hämtas från offentliga, öppna datakällor",
        year="2010–2024",
    ),
    unsafe_allow_html=True,
)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 1: Data source overview table
# ---------------------------------------------------------------------------
st.markdown(
    render_card_header(
        title="Variabler och datakällor",
        subtitle="Indexet kombinerar fem dimensioner av finansiell risk",
        tag="Avsnitt 2.1",
    ),
    unsafe_allow_html=True,
)

sources_df = pd.DataFrame(
    [
        {
            "Variabel": "Skuld per capita",
            "Kolumnnamn": "debt_per_capita",
            "Vikt": "25 %",
            "Källsystem": "SCB PxWeb API",
            "Serie": "BalansKn, post 089",
            "Täckning": "290 kommuner × 15 år",
        },
        {
            "Variabel": "Arbetslöshet",
            "Kolumnnamn": "unemployment",
            "Vikt": "25 %",
            "Källsystem": "Kolada API → Arbetsförmedlingen",
            "Serie": "KPI N03937",
            "Täckning": "290 kommuner × 15 år",
        },
        {
            "Variabel": "Försörjningskvot",
            "Kolumnnamn": "dependency_ratio",
            "Vikt": "20 %",
            "Källsystem": "SCB PxWeb API",
            "Serie": "BefolkningNy, åldrar 0–100+",
            "Täckning": "290 kommuner × 15 år",
        },
        {
            "Variabel": "Befolkningstillväxt (5 år)",
            "Kolumnnamn": "population_growth",
            "Vikt": "15 %",
            "Källsystem": "SCB PxWeb API",
            "Serie": 'BefolkningNy, "tot" ålder',
            "Täckning": "290 kommuner × 15 år",
        },
        {
            "Variabel": "Skattekraft",
            "Kolumnnamn": "tax_base_relative",
            "Vikt": "15 %",
            "Källsystem": "SCB PxWeb API",
            "Serie": "SkatteKraft, OE0101B0",
            "Täckning": "290 kommuner × 15 år",
        },
    ]
)

st.dataframe(
    sources_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Variabel": st.column_config.TextColumn("Variabel", width="medium"),
        "Kolumnnamn": st.column_config.TextColumn("Kolumnnamn", width="medium"),
        "Vikt": st.column_config.TextColumn("Vikt", width="small"),
        "Källsystem": st.column_config.TextColumn("Källsystem", width="large"),
        "Serie": st.column_config.TextColumn("Serie", width="large"),
        "Täckning": st.column_config.TextColumn("Täckning", width="medium"),
    },
)

st.markdown(
    "<p style='font-size:0.82rem;color:#6B7280;margin-top:4px'>"
    "Samtliga fem variabler uppnår <strong>100 % täckning</strong> — inga saknade värden "
    "för någon av de 290 kommunerna under analysperioden 2010–2024."
    "</p>",
    unsafe_allow_html=True,
)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 2: API details (collapsible)
# ---------------------------------------------------------------------------
with st.expander("API-dokumentation — hur data hämtas från respektive källa", expanded=False):
    col_scb, col_kolada = st.columns(2, gap="large")

    with col_scb:
        st.markdown("#### SCB PxWeb API")
        st.markdown(
            "POST-förfrågningar skickas till SCB:s tabellspecifika URL med en JSON-kropp "
            "som anger variabler, regioner och år. Tom `values`-array returnerar alla kommuner."
        )
        st.code(
            """{
  "query": [
    {
      "code": "Region",
      "selection": {
        "filter": "vs:RegionKommun07",
        "values": []
      }
    },
    {
      "code": "Tid",
      "selection": {
        "filter": "item",
        "values": ["2010", "2011", "...", "2024"]
      }
    }
  ],
  "response": { "format": "json" }
}""",
            language="json",
        )
        st.markdown(
            "**Tabeller:** `BalansKn` (skuld) · `BefolkningNy` (befolkning) · "
            "`SkatteKraft` (skattekraft)"
        )

    with col_kolada:
        st.markdown("#### Kolada API")
        st.markdown(
            "REST API för kommunala nyckeltal. Arbetslöshetsdata hämtas via Kolada "
            "som vidarepublicerar Arbetsförmedlingens statistik."
        )
        st.code(
            """# Sök nyckeltal
GET /v2/kpi?title=arbetslöshet

# Hämta data för alla år
GET /v2/data/kpi/N03937/year/2010,2011,...,2024""",
            language="bash",
        )
        st.markdown(
            "**KPI:** `N03937` — Andel öppet arbetslösa och personer i program med aktivitetsstöd, "
            "16–64 år (% av befolkningen)"
        )

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 3: Licens och öppen data
# ---------------------------------------------------------------------------
st.markdown(
    render_card_header(
        title="Licens och öppen data",
        subtitle="All data är offentlig och fritt tillgänglig",
        tag="Licens",
    ),
    unsafe_allow_html=True,
)

license_df = pd.DataFrame(
    [
        {
            "Källa": "SCB Statistikdatabasen",
            "Licens": "SCB öppen licens",
            "Användning": "Fri att använda, kräver källhänvisning",
        },
        {
            "Källa": "Kolada / RKA",
            "Licens": "Creative Commons CC0",
            "Användning": "Fri att använda utan restriktioner",
        },
        {
            "Källa": "Arbetsförmedlingen (via Kolada)",
            "Licens": "Offentlig statistik",
            "Användning": "Fri att använda, kräver källhänvisning",
        },
    ]
)

st.dataframe(
    license_df,
    use_container_width=True,
    hide_index=True,
)
