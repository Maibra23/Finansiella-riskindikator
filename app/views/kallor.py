"""
Page: Källor, data sources and methodology overview.

Displays the full data source table from methodology section 2.1 plus
API and coverage details. All user-facing text is in Swedish.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.data import load_kri_data, load_sensitivity, modal_agreement, year_range
from app.ui.components import card_header
from app.ui.shell import render_footer, render_page_header
from src.config import SENSITIVITY, SWEDISH_LABELS

METHODOLOGY_URL = (
    "https://github.com/Maibra23/Kommunal-Finansiell-Riskindikator/blob/master/docs/methodology.md"
)
_SCB = "https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/"

kri_df = load_kri_data()
sens_df = load_sensitivity()
first_year, last_year = year_range(kri_df)

render_page_header(
    eyebrow="Metod",
    title="Datakällor och metod",
    subtitle="Samtliga variabler i indexet hämtas från offentliga, öppna datakällor",
    meta_value=f"{first_year} - {last_year}",
    meta_label="Analysperiod",
)
st.caption(
    "Avsnittet gäller hela analysperioden; årsvalet i sidopanelen påverkar inte sidan. "
    f"Fullständig metodbeskrivning: [docs/methodology.md]({METHODOLOGY_URL})."
)

# ---------------------------------------------------------------------------
# Section 1: Data source overview table
# ---------------------------------------------------------------------------
card_header(
    "Variabler och datakällor",
    "Indexet kombinerar fem dimensioner av strukturell ekonomisk risk",
)

sources_df = pd.DataFrame(
    [
        {
            "Variabel": "Låneskuld per capita",
            "Kolumnnamn": "debt_per_capita",
            "Vikt": "25 %",
            "Källsystem": "SCB PxWeb API",
            "Serie": "BalansKn, poster 081-085, 090, 136",
            "Källa": _SCB + "START__OE__OE0107__OE0107G/BalansKn/",
            "Täckning": "290 kommuner × 15 år",
        },
        {
            "Variabel": "Öppet arbetslösa (andel av invånare 18-65 år)",
            "Kolumnnamn": "unemployment",
            "Vikt": "25 %",
            "Källsystem": "Kolada API (Arbetsförmedlingen)",
            "Serie": "KPI N03937",
            "Källa": "https://www.kolada.se/verktyg/fri-sokning/?kpis=N03937",
            "Täckning": "290 kommuner × 15 år",
        },
        {
            "Variabel": "Försörjningskvot",
            "Kolumnnamn": "dependency_ratio",
            "Vikt": "20 %",
            "Källsystem": "SCB PxWeb API",
            "Serie": "BefolkningNy, åldrar 0 - 100+",
            "Källa": _SCB + "START__BE__BE0101__BE0101A/BefolkningNy/",
            "Täckning": "290 kommuner × 15 år",
        },
        {
            "Variabel": "Befolkningstillväxt (5 år)",
            "Kolumnnamn": "population_growth",
            "Vikt": "15 %",
            "Källsystem": "SCB PxWeb API",
            "Serie": 'BefolkningNy, "tot" ålder',
            "Källa": _SCB + "START__BE__BE0101__BE0101A/BefolkningNy/",
            "Täckning": "290 kommuner × 15 år",
        },
        {
            "Variabel": "Skattekraft",
            "Kolumnnamn": "tax_base_relative",
            "Vikt": "15 %",
            "Källsystem": "SCB PxWeb API",
            "Serie": "SkatteKraft, OE0101B0",
            "Källa": _SCB + "START__OE__OE0101/SkatteKraft/",
            "Täckning": "290 kommuner × 15 år",
        },
    ]
)

st.dataframe(
    sources_df,
    width="stretch",
    hide_index=True,
    column_config={
        "Variabel": st.column_config.TextColumn("Variabel", width="medium"),
        "Kolumnnamn": st.column_config.TextColumn("Kolumnnamn", width="medium"),
        "Vikt": st.column_config.TextColumn("Vikt", width="small"),
        "Källsystem": st.column_config.TextColumn("Källsystem", width="large"),
        "Serie": st.column_config.TextColumn("Serie", width="large"),
        "Täckning": st.column_config.TextColumn("Täckning", width="medium"),
        "Källa": st.column_config.LinkColumn("Källa", display_text="Öppna", width="small"),
    },
)

st.markdown(
    "<p class='kri-note'>"
    "Samtliga fem variabler uppnår <strong>100 % täckning</strong>: inga saknade värden "
    f"för någon av de 290 kommunerna under analysperioden {first_year} - {last_year}."
    "</p>",
    unsafe_allow_html=True,
)

st.space("small")

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
GET /v3/kpi?title=arbetslöshet

# Hämta data för alla år
GET /v3/data/kpi/N03937/year/2010,2011,...,2024""",
            language="bash",
        )
        st.markdown(
            "**KPI:** `N03937`: Öppet arbetslösa av befolkningen, 18 - 65 år, andel (%). "
            "Nämnaren är alla invånare i åldern, inte arbetskraften, så nivån är lägre än "
            "den vanliga arbetslöshetsgraden. Till och med 2022 avsåg nyckeltalet 18 - 64 år."
        )

st.space("small")

# ---------------------------------------------------------------------------
# Section 3: Viktkänslighet
# ---------------------------------------------------------------------------
card_header(
    SWEDISH_LABELS["weight_sensitivity"],
    "Hur mycket beror rangordningen på just de valda vikterna?",
)

_delta_sv = f"{SENSITIVITY['delta']:.2f}".replace(".", ",")

st.markdown(
    f"""
KRI viktar fem z-poäng med **0,25 skuld · 0,25 öppen arbetslöshet · 0,20 försörjningskvot ·
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
    _modal_agree = modal_agreement(_latest) or len(_sub)
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
            {"Viktvariation": "±0,03", "Robusta": "254 av 290", "Gränsfall": 36,
             "Modal ≠ publicerad": 2, "Medianintervall": "14 platser"},
            {"Viktvariation": "±0,05 (används)", "Robusta": "235 av 290", "Gränsfall": 55,
             "Modal ≠ publicerad": 2, "Medianintervall": "24 platser"},
            {"Viktvariation": "±0,10", "Robusta": "198 av 290", "Gränsfall": 92,
             "Modal ≠ publicerad": 3, "Medianintervall": "49 platser"},
        ]
    ),
    width="stretch",
    hide_index=True,
)
st.caption(
    "Antalet gränsfall växer med intervallet, som väntat, men slutsatsen gör det inte: "
    "den publicerade klassen är den vanligaste klassen för minst 287 av 290 kommuner "
    "vid samtliga tre intervall (2024)."
)

with st.expander("Varför inte PCA-vikter? En prövad och förkastad metod", expanded=False):
    st.markdown(
        """
Det naturliga alternativet är att låta data bestämma vikterna genom
**principalkomponentanalys**. Metoden prövades på samtliga femton år och förkastades
av tre skäl:

1. **Fel tecken på skuld.** Första principalkomponenten laddar *negativt* på skuld
   varje år från 2011 (ned till -0,32) och nära noll 2010. Ett index byggt på den
   skulle rangordna Sveriges mest skuldsatta kommuner bland de minst riskutsatta: de
   29 mest skuldsatta kommunerna hamnar i genomsnitt på 20:e i stället för 69:e
   riskpercentilen. Eskilstuna, med 121 000 kr i låneskuld per invånare, skulle gå
   från Hög risk (rang 6) till klart under rikssnittet. PC1 mäter inte risk utan en tillväxt-tillbakagång-axel: växande,
   välbeställda kommuner lånar till infrastruktur, medan krympande kommuner har
   låg skuld men svag demografi.

2. **Ingen dominerande komponent.** PC1 förklarar bara 40 - 44 % av variansen och PC2
   ligger över Kaiser-kriteriet. Viktning via PCA förutsätter att en komponent
   dominerar, vilket den inte gör här.

3. **Ingen jämförbarhet över tid.** PCA-vikterna skattas per år och rör sig kraftigt
   - skuldvikten varierar mellan 0,006 och 0,16 och arbetslöshetsvikten mellan 0,009
   och 0,20 över perioden. En kommuns poäng skulle då förändras för att vikterna rört sig, inte
   för att ekonomin gjort det, vilket omöjliggör tidsserien.

En teckenbegränsad variant (icke-negativ PC1) prövades också. Den tilldelar skuld
vikten **noll** i fjorton av femton år. Den "lagar" alltså metoden genom att stryka den
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

st.space("small")

# ---------------------------------------------------------------------------
# Section 3: Licens och öppen data
# ---------------------------------------------------------------------------
card_header("Licens och öppen data", "All data är offentlig och fritt tillgänglig")

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
    width="stretch",
    hide_index=True,
)

render_footer(first_year, last_year)
