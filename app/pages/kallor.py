"""
Page: Källor, data sources and methodology overview.

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
from src.config import SENSITIVITY, SWEDISH_LABELS

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
apply_streamlit_theme()


@st.cache_data(show_spinner=False)
def _load_sensitivity() -> pd.DataFrame | None:
    """Weight-sensitivity band, or None when the optional layer is not built."""
    p = PROJECT_ROOT / "data" / "processed" / "kri_sensitivity.parquet"
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p)
        df["year"] = df["year"].astype(int)
        return df
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def _modal_agreement(year: int) -> int | None:
    """How many municipalities keep their published class as the modal class."""
    results = PROJECT_ROOT / "data" / "processed" / "kri_results.parquet"
    sens = _load_sensitivity()
    if sens is None or not results.exists():
        return None
    kri = pd.read_parquet(results, columns=["municipality_code", "year", "risk_class"])
    kri["year"] = kri["year"].astype(int)
    merged = kri.merge(sens, on=["municipality_code", "year"])
    sub = merged[merged["year"] == year]
    return int((sub["modal_class"] == sub["risk_class"]).sum())


sens_df = _load_sensitivity()

# Sidebar, mirrors app/main.py
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
        year="2010 - 2024",
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
            "Källsystem": "Kolada API (Arbetsförmedlingen)",
            "Serie": "KPI N03937",
            "Täckning": "290 kommuner × 15 år",
        },
        {
            "Variabel": "Försörjningskvot",
            "Kolumnnamn": "dependency_ratio",
            "Vikt": "20 %",
            "Källsystem": "SCB PxWeb API",
            "Serie": "BefolkningNy, åldrar 0 - 100+",
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
    "Samtliga fem variabler uppnår <strong>100 % täckning</strong>: inga saknade värden "
    "för någon av de 290 kommunerna under analysperioden 2010 - 2024."
    "</p>",
    unsafe_allow_html=True,
)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 2: API details (collapsible)
# ---------------------------------------------------------------------------
with st.expander("API-dokumentation: hur data hämtas från respektive källa", expanded=False):
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
            "**KPI:** `N03937`: Andel öppet arbetslösa och personer i program med aktivitetsstöd, "
            "16 - 64 år (% av befolkningen)"
        )

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 3: Viktkänslighet
# ---------------------------------------------------------------------------
st.markdown(
    render_card_header(
        title=SWEDISH_LABELS["weight_sensitivity"],
        subtitle="Hur mycket beror rangordningen på just de valda vikterna?",
        tag="Metod",
    ),
    unsafe_allow_html=True,
)

_delta_sv = f"{SENSITIVITY['delta']:.2f}".replace(".", ",")

st.markdown(
    f"""
KRI viktar fem z-poäng med **0,25 skuld · 0,25 arbetslöshet · 0,20 försörjningskvot ·
0,15 befolkningstillväxt · 0,15 skattekraft**. Vikterna är motiverade utifrån offentlig
finansieringsteori. De är alltså *valda*, inte skattade ur data. Det är en rimlig
invändning mot varje sammansatt index, och den besvaras här med en mätning i stället
för ett argument.

**Metod.** Varje vikt tillåts variera likformigt med
±{_delta_sv} kring sitt nominella värde. Vektorn normeras så att summan
förblir 1. Höjer man skuldvikten måste något annat sänkas, vilket är precis den
avvägning invändningen handlar om. Indexet räknas om {int(SENSITIVITY['n_draws'])}
gånger och kvartilgränserna beräknas om *inom varje omräkning*, så att resultatet
motsvarar vad klassificeringen hade gett om de vikterna varit de verkliga.
Beräkningen är deterministisk (fast frö), så bandet är reproducerbart.

En kommun kallas **robust** när den behåller sin publicerade riskklass i minst
{SENSITIVITY['robust_threshold']:.0%} av omräkningarna, annars **gränsfall**. Gränsfall
betyder att kommunen ligger nära gränsen mellan två riskklasser - inte att klassningen
är felaktig.
"""
)

if sens_df is not None:
    _latest = int(sens_df["year"].max())
    _sub = sens_df[sens_df["year"] == _latest]
    _robust = int(_sub["is_robust"].sum())
    _modal_agree = _modal_agreement(_latest) or len(_sub)
    st.markdown(
        f"""
**Resultat {_latest}.** {_robust} av {len(_sub)} kommuner är robusta. Den viktigaste
siffran är dock en annan: för **{_modal_agree} av {len(_sub)}** kommuner är den
publicerade riskklassen också den vanligaste klassen över alla omräkningar.
Känslighetsanalysen bekräftar alltså indexet i stället för att ifrågasätta det.
"""
    )

st.markdown("**Hur känsligt är resultatet för valet av ±-intervall?**")
st.dataframe(
    pd.DataFrame(
        [
            {"Viktvariation": "±0,03", "Robusta": "259 av 290", "Gränsfall": 31,
             "Modal ≠ publicerad": 1, "Medianintervall": "15 platser"},
            {"Viktvariation": "±0,05 (används)", "Robusta": "241 av 290", "Gränsfall": 49,
             "Modal ≠ publicerad": 1, "Medianintervall": "26 platser"},
            {"Viktvariation": "±0,10", "Robusta": "194 av 290", "Gränsfall": 96,
             "Modal ≠ publicerad": 2, "Medianintervall": "52 platser"},
        ]
    ),
    use_container_width=True,
    hide_index=True,
)
st.caption(
    "Antalet gränsfall växer med intervallet, som väntat, men slutsatsen gör det inte: "
    "den publicerade klassen är den vanligaste klassen för minst 288 av 290 kommuner "
    "vid samtliga tre intervall."
)

with st.expander("Varför inte PCA-vikter? En prövad och förkastad metod", expanded=False):
    st.markdown(
        """
Det naturliga alternativet är att låta data bestämma vikterna genom
**principalkomponentanalys**. Metoden prövades på samtliga femton år och förkastades
av tre skäl:

1. **Fel tecken på skuld.** Första principalkomponenten laddar *negativt* på skuld
   varje år 2010 - 2024 (mellan -0,08 och -0,39). Ett index byggt på den skulle rangordna
   Sveriges mest skuldsatta kommuner bland de minst riskutsatta. Eskilstuna, med
   302 000 kr i skuld per invånare, skulle gå från Hög risk till klart under
   rikssnittet. PC1 mäter inte risk utan en tillväxt-tillbakagång-axel: växande,
   välbeställda kommuner lånar till infrastruktur, medan krympande kommuner har
   låg skuld men svag demografi.

2. **Ingen dominerande komponent.** PC1 förklarar bara ~44 % av variansen och PC2
   ligger över Kaiser-kriteriet. Viktning via PCA förutsätter att en komponent
   dominerar, vilket den inte gör här.

3. **Ingen jämförbarhet över tid.** PCA-vikterna skattas per år och rör sig kraftigt
   - skuldvikten varierar med faktor 5 och arbetslöshetsvikten med faktor 23 över
   perioden. En kommuns poäng skulle då förändras för att vikterna rört sig, inte
   för att ekonomin gjort det, vilket omöjliggör tidsserien.

En teckenbegränsad variant (icke-negativ PC1) prövades också. Den tilldelar skuld
vikten **noll** samtliga femton år. Den "lagar" alltså metoden genom att stryka den
variabel indexet finns till för att mäta.
"""
    )

with st.expander("Avgränsningar", expanded=False):
    st.markdown(
        """
Osäkerhetsbandet mäter känslighet för **ett** subjektivt val: viktningen. Det gör
inte indexet objektivt, och det omfattar inte:

- **Osäkerhet i data.** Mätfel i SCB:s skuldsiffror och interpolerade serier
  behandlas inte här.
- **Osäkerhet i variabelvalet.** Att lägga till eller ta bort en indikator påverkar
  resultatet betydligt mer än att omvikta de nuvarande fem.
- **Beroenden mellan vikter.** Vikterna dras oberoende av varandra. Normeringen
  fångar kravet att summan är 1, men inte en uppfattning om att exempelvis skuld
  alltid bör väga tyngre än befolkning.

Kommunernas publicerade KRI-poäng, rang och riskklass påverkas aldrig av denna
beräkning. Den redovisar hur stabila de värdena är, inte vad de ska vara.
"""
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
