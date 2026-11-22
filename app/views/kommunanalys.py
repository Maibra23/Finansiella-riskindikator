"""
Kommunanalys: how exposed is one municipality, and how has that changed?

Summary and exports, sensitivity callout, six KPIs with 15-year sparklines,
trend against the national average, the ten most similar municipalities, full
history and data quality. All user-facing text is in Swedish.
"""

from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from app.data import cached_pdf, kommun_history, load_kri_data, load_sensitivity, year_range, year_slice
from app.formatting import fmt_decimal, fmt_int, fmt_range
from app.ui.components import card_header, indicator_delta, kpi, render_kommun_summary
from app.ui.shell import render_footer, render_page_header
from src.config import SENSITIVITY, SWEDISH_LABELS

# Heavy imports (ECharts, scikit-learn) come after the shell (already drawn by the router).
from streamlit_echarts import st_echarts

from app.components.charts import build_line_trend
from src.clustering import get_peer_municipalities
from src.risk_scale import RiskScale
from src.validators import get_municipality_flags

log = logging.getLogger(__name__)

UNEMP_COL = "Öppet arbetslösa (% av 18-65 år)"

kri_df = load_kri_data()
sens_df = load_sensitivity()
selected_year: int = st.session_state["selected_year"]
first_year, last_year = year_range(kri_df)

render_page_header(
    eyebrow="Kommun",
    title=SWEDISH_LABELS["municipality_analysis"],
    subtitle="Detaljerad genomgång av en kommuns strukturella ekonomiska riskprofil.",
    meta_value=str(selected_year),
)

year_df = year_slice(kri_df, selected_year).sort_values("municipality_name")
n_total = len(year_df)
all_names = year_df["municipality_name"].tolist()
name_to_code = dict(zip(all_names, year_df["municipality_code"].astype(str).str.zfill(4)))

# Shared with Riskdekomposition: the kommun chosen on either page carries over.
prev_selection = st.session_state.get("selected_municipality", all_names[0])
default_idx = all_names.index(prev_selection) if prev_selection in all_names else 0

# ---------------------------------------------------------------------------
# Context row: selector · summary · actions
# ---------------------------------------------------------------------------
sel_col, sum_col, act_col = st.columns([1.2, 2, 1.2], gap="medium", vertical_alignment="bottom")
with sel_col:
    selected_name: str = st.selectbox(
        SWEDISH_LABELS["select_municipality"],
        options=all_names,
        index=default_idx,
        key="ka_muni_select",
    )
st.session_state["selected_municipality"] = selected_name
selected_code = name_to_code[selected_name]

sel_rows = year_df[year_df["municipality_code"] == selected_code]
if sel_rows.empty:
    st.warning("Ingen data finns för vald kommun och år. Välj ett annat år i sidopanelen.")
    st.stop()
sel_row = sel_rows.iloc[0]
risk = str(sel_row["risk_class"])

sens_row = None
if sens_df is not None:
    _m = sens_df[(sens_df["municipality_code"] == selected_code) & (sens_df["year"] == selected_year)]
    sens_row = _m.iloc[0] if not _m.empty else None

with sum_col:
    render_kommun_summary(sel_row, sens_row, n_total)

history = kommun_history(kri_df, selected_code)
display_history = history.sort_values("year", ascending=False)[[
    "year", "kri_score", "rank", "risk_class",
    "debt_per_capita", "unemployment", "dependency_ratio",
    "population_growth", "tax_base_relative",
]].rename(columns={
    "year": "År",
    "kri_score": "KRI Poäng",
    "rank": "Rang",
    "risk_class": "Riskklass",
    "debt_per_capita": "Skuld per capita (kr)",
    "unemployment": UNEMP_COL,
    "dependency_ratio": "Försörjningskvot",
    "population_growth": "Befolkningstillväxt (%)",
    "tax_base_relative": "Skattekraft (% av rikssnitt)",
})
csv_data = display_history.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")

with act_col:
    st.download_button(
        "Ladda ner data (CSV)",
        data=csv_data,
        file_name=f"kri_{selected_code}_{selected_name.replace(' ', '_')}.csv",
        mime="text/csv",
        key="ka_download_csv",
        on_click="ignore",
        icon=":material/download:",
        width="stretch",
        help="All tidsdata för vald kommun. Semikolon mellan kolumner och komma som decimaltecken.",
    )
    st.download_button(
        "Ladda ner rapport (PDF)",
        data=lambda: cached_pdf(selected_year),
        file_name=f"kri_rapport_{selected_year}.pdf",
        mime="application/pdf",
        key="ka_download_pdf",
        on_click="ignore",
        icon=":material/picture_as_pdf:",
        width="stretch",
        help=f"Riksomfattande PDF-rapport för {selected_year} (alla kommuner). "
        "Skapas när du klickar, några sekunder första gången.",
    )

# ---------------------------------------------------------------------------
# Weight-sensitivity callout
# ---------------------------------------------------------------------------
if sens_row is not None:
    _stability = float(sens_row["class_stability"])
    _delta_txt = fmt_decimal(SENSITIVITY["delta"], 2)
    _interval = fmt_range(sens_row["rank_p05"], sens_row["rank_p95"])
    if bool(sens_row["is_robust"]):
        st.success(
            f"**Viktkänslighet:** klassningen är stabil. {selected_name} hamnar i {risk} risk i "
            f"{_stability:.0%} av de {int(SENSITIVITY['n_draws'])} omräkningar där varje vikt "
            f"varierats med ±{_delta_txt}. Rangen ligger då inom {_interval} av {n_total}.",
            icon=":material/verified:",
        )
    else:
        st.warning(
            f"**Viktkänslighet:** klassningen är känslig för viktvalet. {selected_name} hamnar i "
            f"{risk} risk i {_stability:.0%} av de {int(SENSITIVITY['n_draws'])} omräkningar där "
            f"varje vikt varierats med ±{_delta_txt}, och rangen rör sig inom {_interval} av "
            f"{n_total}. Kommunen ligger nära gränsen mellan två riskklasser.",
            icon=":material/warning:",
        )

# ---------------------------------------------------------------------------
# KPI grid 3 x 2 with sparklines
# ---------------------------------------------------------------------------
prev_year = selected_year - 1
prev_rows = history[history["year"] == prev_year]
prev_row = prev_rows.iloc[0] if not prev_rows.empty else None
period = f"mot {prev_year}" if prev_row is not None else None
upto = history[history["year"] <= selected_year]


def _pv(col: str) -> float | None:
    return float(prev_row[col]) if prev_row is not None else None


def _spark(col: str) -> list[float]:
    return upto[col].astype(float).tolist()


# (label, value, delta, better_when, help, column). Rank 1 = most vulnerable,
# so a higher rank number is better.
_kpis = [
    ("KRI Poäng", fmt_decimal(sel_row["kri_score"], 2),
     indicator_delta(sel_row["kri_score"], _pv("kri_score"), nd=2), "lower",
     "Sammansatt index: viktat medelvärde av fem z-poäng. Högre värde = större strukturell "
     "sårbarhet. Linjen visar utvecklingen sedan " + str(first_year) + ".", "kri_score"),
    (SWEDISH_LABELS["rank"], f"{int(sel_row['rank'])} av {n_total}",
     indicator_delta(sel_row["rank"], _pv("rank"), nd=0, unit=" platser"), "higher",
     "Rang 1 är den mest sårbara kommunen. Ett högre rangtal betyder lägre relativ risk.", "rank"),
    (SWEDISH_LABELS["debt_per_capita"], f"{fmt_int(sel_row['debt_per_capita'])} kr",
     indicator_delta(sel_row["debt_per_capita"], _pv("debt_per_capita"), nd=0, unit=" kr"), "lower",
     "Kommunens samlade låneskuld per invånare: lång- och kortfristiga lån inklusive obligationer "
     "(SCB BalansKn).", "debt_per_capita"),
    (UNEMP_COL, f"{fmt_decimal(sel_row['unemployment'], 1)} %",
     indicator_delta(sel_row["unemployment"], _pv("unemployment"), nd=1, unit=" p.e."), "lower",
     "Öppet arbetslösa som andel av alla invånare 18-65 år (Kolada N03937), inte av arbetskraften. "
     "Nivån är därför ungefär hälften av den vanliga arbetslöshetsgraden.", "unemployment"),
    ("Försörjningskvot", fmt_decimal(sel_row["dependency_ratio"], 3),
     indicator_delta(sel_row["dependency_ratio"], _pv("dependency_ratio"), nd=3), "lower",
     "Antal unga och äldre per person i arbetsför ålder. Högre kvot = större tryck på välfärden.",
     "dependency_ratio"),
    (f"{SWEDISH_LABELS['tax_base']} (% av rikssnitt)", f"{fmt_decimal(sel_row['tax_base_relative'], 1)} %",
     indicator_delta(sel_row["tax_base_relative"], _pv("tax_base_relative"), nd=1, unit=" p.e."),
     "higher", "Beskattningsbar inkomst per invånare i procent av rikssnittet. Lägre = svagare "
     "skattebas.", "tax_base_relative"),
]
for start in (0, 3):
    for col, (label, value, delta, better, help_txt, column) in zip(
        st.columns(3, gap="small"), _kpis[start:start + 3]
    ):
        with col:
            kpi(label, value, delta=delta, better_when=better, help=help_txt,  # type: ignore[arg-type]
                period_label=period, spark=_spark(column))

st.caption(
    f"Nyckeltal för {selected_year} jämfört med {prev_year}, med utvecklingen sedan {first_year}. "
    "Pilen visar förändringens riktning, färgen om förändringen ökar (röd) eller minskar (grön) "
    "risken. Rang 1 är den mest sårbara kommunen."
)

st.page_link(
    "views/riskdekomposition.py",
    label=f"Visa riskdrivare för {selected_name}",
    icon=":material/stacked_bar_chart:",
)

# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------
with st.container(border=True):
    card_header(
        f"KRI-trend {first_year} - {last_year}",
        f"{selected_name} jämfört med rikssnittet",
        help_md=(
            "Bakgrundsbanden visar riskzonerna (grönt Låg, gult Medel, rött Hög) med gränser "
            "beräknade över hela perioden. Rikssnittet är medelvärdet av alla kommuners KRI "
            "samma år och ligger nära 0 per konstruktion."
        ),
    )
    pivot = kri_df.pivot_table(index="year", columns="municipality_code", values="kri_score")
    all_years = pivot.index.astype(int).tolist()
    trend_series = {
        selected_name: pivot[selected_code].astype(float).tolist(),
        "Rikssnitt": pivot.mean(axis=1).astype(float).tolist(),
    }
    st_echarts(
        build_line_trend(all_years, trend_series, RiskScale.pooled(kri_df)),
        height="360px",
        key=f"ka_trend_{selected_code}_{selected_year}",
    )


def _highlight_extremes(s: pd.Series, higher_is_worse: bool = True) -> list[str]:
    """Background tint: red for the worst value in the column, green for the best."""
    if s.dtype.kind not in "iufb" or s.isna().all():
        return [""] * len(s)
    styles = [""] * len(s)
    v_min_idx, v_max_idx = s.idxmin(), s.idxmax()
    if v_min_idx == v_max_idx:
        return styles
    worst_bg = "background-color: rgba(185, 74, 72, 0.12)"
    best_bg = "background-color: rgba(46, 125, 91, 0.12)"
    worst, best = (v_max_idx, v_min_idx) if higher_is_worse else (v_min_idx, v_max_idx)
    styles[s.index.get_loc(worst)] = worst_bg
    styles[s.index.get_loc(best)] = best_bg
    return styles


_LEGEND = "Rött = sämsta värdet i kolumnen, grönt = bästa."

# ---------------------------------------------------------------------------
# Peers
# ---------------------------------------------------------------------------
with st.container(border=True):
    card_header(
        SWEDISH_LABELS["similar_municipalities"],
        "Kommuner med likartad riskprofil över alla fem indikatorer",
        help_md=(
            "Likheten mäts som euklidiskt avstånd mellan kommunernas fem z-poäng samma år. "
            "**Avstånd**: lägre värde = mer lik vald kommun."
        ),
    )
    try:
        peer_df = get_peer_municipalities(selected_code, kri_df, n=10, year=selected_year)
        if peer_df.empty:
            st.info("Det finns inga jämförbara kommuner för vald kommun och år.")
        else:
            extra_cols = ["municipality_code", "rank", "debt_per_capita", "unemployment",
                          "dependency_ratio", "population_growth", "tax_base_relative"]
            peer_df = peer_df.merge(year_slice(kri_df, selected_year)[extra_cols],
                                    on="municipality_code", how="left")
            peer_display = peer_df.rename(columns={
                "municipality_name": "Kommun",
                "rank": "Rang",
                "kri_score": "KRI",
                "risk_class": "Riskklass",
                "debt_per_capita": "Skuld (kr)",
                "unemployment": "Öppet arbetslösa (%)",
                "dependency_ratio": "Försörjning",
                "population_growth": "Befolkning (%)",
                "tax_base_relative": "Skattekraft (%)",
                "distance": "Avstånd",
            })[[
                "Rang", "Kommun", "Riskklass", "KRI", "Skuld (kr)", "Öppet arbetslösa (%)",
                "Försörjning", "Befolkning (%)", "Skattekraft (%)", "Avstånd",
            ]]
            peer_styled = (
                peer_display.style
                .apply(_highlight_extremes, higher_is_worse=True, subset=["KRI"])
                .apply(_highlight_extremes, higher_is_worse=True, subset=["Skuld (kr)"])
                .apply(_highlight_extremes, higher_is_worse=True, subset=["Öppet arbetslösa (%)"])
                .apply(_highlight_extremes, higher_is_worse=True, subset=["Försörjning"])
                .apply(_highlight_extremes, higher_is_worse=False, subset=["Befolkning (%)"])
                .apply(_highlight_extremes, higher_is_worse=False, subset=["Skattekraft (%)"])
                .format({
                    "KRI": lambda x: fmt_decimal(x, 2),
                    "Skuld (kr)": fmt_int,
                    "Öppet arbetslösa (%)": lambda x: fmt_decimal(x, 1),
                    "Försörjning": lambda x: fmt_decimal(x, 3),
                    "Befolkning (%)": lambda x: fmt_decimal(x, 1),
                    "Skattekraft (%)": lambda x: fmt_decimal(x, 1),
                    "Avstånd": lambda x: fmt_decimal(x, 3),
                    "Rang": "{:.0f}",
                })
            )
            st.dataframe(
                peer_styled,
                hide_index=True,
                alt=f"Tabell över de tio kommuner som mest liknar {selected_name}",
                column_config={
                    "Avstånd": st.column_config.Column(
                        help="Euklidiskt avstånd mellan kommunernas fem z-poäng. Lägre värde = mer lik."
                    ),
                },
            )
            st.caption(_LEGEND)
    except Exception:
        log.exception("Peer calculation failed for %s", selected_code)
        st.warning("Kunde inte beräkna jämförbara kommuner. Försök igen eller välj en annan kommun.")

# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
with st.container(border=True):
    card_header(
        "Underliggande data, alla år",
        f"Alla indikatorer för {selected_name}, {first_year} - {last_year}",
    )
    history_styled = (
        display_history.style
        .apply(_highlight_extremes, higher_is_worse=True, subset=["KRI Poäng"])
        # Rank 1 = most vulnerable, so the lowest rank number is the worst value.
        .apply(_highlight_extremes, higher_is_worse=False, subset=["Rang"])
        .apply(_highlight_extremes, higher_is_worse=True, subset=["Skuld per capita (kr)"])
        .apply(_highlight_extremes, higher_is_worse=True, subset=[UNEMP_COL])
        .apply(_highlight_extremes, higher_is_worse=True, subset=["Försörjningskvot"])
        .apply(_highlight_extremes, higher_is_worse=False, subset=["Befolkningstillväxt (%)"])
        .apply(_highlight_extremes, higher_is_worse=False, subset=["Skattekraft (% av rikssnitt)"])
        .format({
            "KRI Poäng": lambda x: fmt_decimal(x, 2),
            "Skuld per capita (kr)": fmt_int,
            UNEMP_COL: lambda x: fmt_decimal(x, 1),
            "Försörjningskvot": lambda x: fmt_decimal(x, 3),
            "Befolkningstillväxt (%)": lambda x: fmt_decimal(x, 1),
            "Skattekraft (% av rikssnitt)": lambda x: fmt_decimal(x, 1),
            "Rang": "{:.0f}",
            "År": "{:.0f}",
        })
    )
    st.dataframe(
        history_styled,
        hide_index=True,
        alt=f"Tabell med alla indikatorer för {selected_name}, {first_year} - {last_year}",
    )
    st.caption(_LEGEND)

# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------
with st.expander(SWEDISH_LABELS["data_quality"]):
    flags = get_municipality_flags(selected_code)
    if flags:
        for flag in flags:
            st.warning(flag)
    else:
        st.success("Inga kända datakvalitetsproblem för denna kommun.")

    muni_cols = ["debt_per_capita", "unemployment", "dependency_ratio",
                 "population_growth", "tax_base_relative"]
    col_labels = {
        "debt_per_capita": "Skuld per capita",
        "unemployment": SWEDISH_LABELS["unemployment"],
        "dependency_ratio": "Försörjningskvot",
        "population_growth": "Befolkningstillväxt",
        "tax_base_relative": "Skattekraft",
    }
    missing_count = int(history[muni_cols].isna().sum().sum())
    total_cells = len(history) * len(muni_cols)
    q1, q2, q3 = st.columns(3)
    q1.metric("Datapunkter totalt", f"{total_cells}")
    q2.metric("Kompletta", f"{total_cells - missing_count}")
    q3.metric("Saknade", f"{missing_count}")
    if missing_count > 0:
        st.markdown("**Saknade värden per variabel:**")
        for col in muni_cols:
            n_miss = int(history[col].isna().sum())
            if n_miss > 0:
                st.markdown(f"- **{col_labels[col]}**: {n_miss} år saknas")

render_footer(first_year, last_year)
