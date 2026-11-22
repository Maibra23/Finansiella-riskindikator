"""
Riksöversikt: national overview of KRI for all 290 municipalities.

Answers "where is risk concentrated this year?": risk-class filter, four KPIs,
map and distribution, top/bottom 15 with weight-sensitivity intervals, and
exports. Charts use streamlit-echarts. All user-facing text is in Swedish.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.data import cached_pdf, load_kri_data, load_sensitivity, year_range, year_slice
from app.formatting import (
    fmt_count_of,
    fmt_decimal,
    fmt_int,
    fmt_range,
    fmt_signed,
)
from app.ui.components import card_header, kpi, risk_badge
from app.ui.shell import render_footer, render_page_header
from src.config import MUNICIPALITIES, SENSITIVITY, SWEDISH_LABELS

# Heavy imports (ECharts, Folium) come after the shell (already drawn by the router).
from streamlit_echarts import st_echarts

from app.components.charts import build_distribution_histogram, build_raw_indicator_histogram
from app.components.sweden_choropleth import render_choropleth
from src.risk_scale import RiskScale

RISK_OPTIONS = ["Hög", "Medel", "Låg"]
_RISK_DOT = {"Hög": "🔴", "Medel": "🟡", "Låg": "🟢"}

# KPI explanations, reachable by mouse, keyboard and touch through the help icon.
_HELP_MEDIAN_KRI = (
    "Median KRI är mittenvärdet i urvalet: hälften av kommunerna har lägre KRI och hälften högre. "
    "Medianen påverkas mindre av enstaka extrema kommuner än ett medelvärde. KRI är ett viktat "
    "medelvärde av fem z-poäng, så värdet är en indexpoäng, inte antal standardavvikelser."
)
_HELP_HIGH_RISK = (
    "Antal kommuner i riskklass Hög i urvalet. Riskklasserna är relativa: en fjärdedel av "
    "kommunerna klassas som Hög risk varje år, så antalet för hela riket är alltid ungefär "
    "en fjärdedel och säger inte om Sverige som helhet blivit mer eller mindre sårbart."
)
_HELP_MEDIAN_DEBT = (
    "Median låneskuld per invånare i urvalet. Medianen dras mindre av enstaka extremvärden "
    "än ett medelvärde. Förändringen anges i procent mot föregående år."
)
_HELP_POP_CHANGE = (
    "Medelvärdet av kommunernas befolkningsförändring över fem år, i procent. Förändringen mot "
    "föregående år anges i procentenheter (p.e.)."
)

kri_df = load_kri_data()
sens_df = load_sensitivity()
selected_year: int = st.session_state["selected_year"]
first_year, last_year = year_range(kri_df)

render_page_header(
    eyebrow="Översikt",
    title="Riksöversikt",
    subtitle="Strukturell ekonomisk sårbarhet i Sveriges kommuner",
    meta_value=str(selected_year),
)

year_df = year_slice(kri_df, selected_year)
n_total = len(year_df)
# Left join keeps every municipality even if the optional layer is absent.
if sens_df is not None:
    year_df = year_df.merge(
        sens_df[sens_df["year"] == selected_year].drop(columns="year"),
        on="municipality_code",
        how="left",
    )

# ---------------------------------------------------------------------------
# Filter bar (risk class). Empty selection = all municipalities.
# ---------------------------------------------------------------------------
with st.container(border=True):
    _risks = st.pills(
        "Riskklass",
        options=RISK_OPTIONS,
        selection_mode="multi",
        default=st.session_state.get("selected_risks") or None,
        format_func=lambda r: f"{_RISK_DOT[r]} {r}",
        key="rv_risk_filter",
        persist_state="session",
        help="Visa bara kommuner i valda riskklasser. Inget val = alla kommuner.",
    )
    selected_risks: list[str] = list(_risks) if _risks else []
    st.session_state["selected_risks"] = selected_risks
    # Backward-compatible alias read by older code paths.
    st.session_state["selected_risk"] = (
        selected_risks[0] if len(selected_risks) == 1 else ("Alla" if not selected_risks else "Multi")
    )
    filtered_df = (
        year_df[year_df["risk_class"].isin(selected_risks)].copy() if selected_risks else year_df.copy()
    )
    st.caption(
        f"Visar {fmt_count_of(len(filtered_df), n_total)} kommuner"
        if selected_risks
        else f"Visar alla {n_total} kommuner"
    )

if filtered_df.empty:
    st.info("Inga kommuner matchar filtret. Välj en annan riskklass eller rensa filtret.")
    render_footer(first_year, last_year)
    st.stop()

# ---------------------------------------------------------------------------
# KPI row. The previous year is filtered by the same risk classes (each kommun's
# own class that year), so the comparison is like for like.
# ---------------------------------------------------------------------------
prev_year = selected_year - 1
prev_all = year_slice(kri_df, prev_year)
prev_df = prev_all[prev_all["risk_class"].isin(selected_risks)] if selected_risks else prev_all
period = (f"mot {prev_year}, samma urval" if selected_risks else f"mot {prev_year}") if not prev_df.empty else None


def _delta(cur: float, prv: float | None, nd: int, unit: str = "") -> str | None:
    if prv is None or prev_df.empty:
        return None
    d = cur - prv
    if abs(d) < 0.5 * 10 ** (-nd):
        return "Oförändrat"
    return f"{fmt_signed(d, nd)}{unit}"


median_kri = float(filtered_df["kri_score"].median())
high_n = int((filtered_df["risk_class"] == "Hög").sum())
median_debt = float(filtered_df["debt_per_capita"].median())
pop_mean = float(filtered_df["population_growth"].mean())

prev_debt = float(prev_df["debt_per_capita"].median()) if not prev_df.empty else None
debt_pct = (median_debt - prev_debt) / prev_debt * 100 if prev_debt else None

k1, k2, k3, k4 = st.columns(4, gap="small")
with k1:
    kpi(
        "Median KRI",
        fmt_decimal(median_kri, 2),
        delta=_delta(median_kri, float(prev_df["kri_score"].median()) if not prev_df.empty else None, 2),
        better_when="lower",
        help=_HELP_MEDIAN_KRI,
        period_label=period,
    )
with k2:
    kpi(
        "Högriskkommuner",
        fmt_count_of(high_n, len(filtered_df)),
        delta=_delta(high_n, int((prev_df["risk_class"] == "Hög").sum()) if not prev_df.empty else None, 0),
        better_when="lower",
        help=_HELP_HIGH_RISK,
        period_label=period,
    )
with k3:
    kpi(
        SWEDISH_LABELS["median_debt"],
        f"{fmt_int(median_debt)} kr",
        delta=_delta(debt_pct, 0.0, 1, " %") if debt_pct is not None else None,
        better_when="lower",
        help=_HELP_MEDIAN_DEBT,
        period_label=period,
    )
with k4:
    kpi(
        "Befolkningsförändring, 5 år",
        f"{fmt_signed(pop_mean, 2)} %",
        delta=_delta(pop_mean, float(prev_df["population_growth"].mean()) if not prev_df.empty else None,
                     2, " p.e."),
        better_when="higher",
        help=_HELP_POP_CHANGE,
        period_label=period,
    )

st.space("small")

# ---------------------------------------------------------------------------
# Map + distribution
# ---------------------------------------------------------------------------
# Built from the unfiltered year: zone boundaries must stay identical to the
# risk classes shown in the tables, which a risk filter must not shift.
_risk_scale = RiskScale.for_year(kri_df, selected_year)
_risk_key = "alla" if not selected_risks else "-".join(sorted(selected_risks))
include_codes = (
    set(filtered_df["municipality_code"].astype(str).str.zfill(4)) if selected_risks else None
)

map_col, dist_col = st.columns([1.55, 1.0], gap="medium")

with map_col:
    with st.container(border=True):
        card_header(
            "Geografisk fördelning",
            f"Kommunerna färgade efter KRI {selected_year}",
            help_md=(
                "Varje kommun fylls med en färg efter sin KRI-poäng: **grön** = lägre risk, "
                "**gul** = medel, **röd** = högre risk. Färgskalan är centrerad på 0 och spänner "
                "över årets faktiska spridning. Brytpunkterna mot grönt och rött ligger på årets "
                "25:e och 75:e percentil, samma gränser som riskklasserna. Skalan räknas alltid "
                "på hela riket, så färgerna ändras inte av riskfiltret. "
                "**Kommuner utanför riskfiltret visas i ljusgrått.** Hovra över en kommun för "
                "KRI, rang, skuld per capita, öppen arbetslöshet, befolkningstillväxt och "
                "skattekraft. Kartan kan panoreras och zoomas."
            ),
        )
        render_choropleth(year_df, selected_year, height=440, include_codes=include_codes)

with dist_col:
    with st.container(border=True):
        _dist_view = st.segmented_control(
            "Vy",
            options=["KRI (normaliserad)", "Skuld per capita (rådata)"],
            default="KRI (normaliserad)",
            label_visibility="collapsed",
            key="rv_dist_view",
        )
        _show_raw = _dist_view == "Skuld per capita (rådata)"
        scores = filtered_df["kri_score"].astype(float).tolist()
        card_header(
            "Skuld per capita (rådata)" if _show_raw else "KRI-fördelning",
            (
                f"Råvärden före normalisering, {len(filtered_df)} kommuner"
                if _show_raw
                else f"Fördelning av KRI, {len(filtered_df)} kommuner"
            ),
            help_md=(
                "**KRI-fördelningen** visar det sammansatta indexet: ett viktat medelvärde av fem "
                "z-poäng (skuld, öppen arbetslöshet, försörjningskvot, befolkningstillväxt, "
                "skattekraft). Värden nära 0 är genomsnittliga, negativa betyder lägre risk än "
                f"rikssnittet. Gröna staplar = Låg risk (KRI under {fmt_decimal(_risk_scale.low, 2)}), "
                f"gula = Medel, röda = Hög risk (KRI över {fmt_signed(_risk_scale.high, 2)}). "
                "Brytpunkterna är årets 25:e och 75:e percentil. Den streckade linjen är medianen. "
                "**Rådata (skuld)** visar skuld per capita i kronor före normaliseringen och "
                "illustrerar hur indexet gör absoluta värden jämförbara."
            ),
        )
        if _show_raw:
            raw_opt = build_raw_indicator_histogram(
                filtered_df["debt_per_capita"].astype(float).tolist(), "Skuld per capita", "kr"
            )
            st_echarts(options=raw_opt, height="400px", key=f"raw_hist_{selected_year}_{_risk_key}")
        else:
            hist_opt = build_distribution_histogram(
                scores, median_kri, _risk_scale, total=len(scores)
            )
            st_echarts(options=hist_opt, height="400px", key=f"dist_{selected_year}_{_risk_key}")

st.space("small")

# ---------------------------------------------------------------------------
# Rankings
# ---------------------------------------------------------------------------
top15_high = filtered_df.nsmallest(15, "rank").sort_values("rank")
top15_low = filtered_df.nlargest(15, "rank").sort_values("rank", ascending=False)


def _uncertainty_cell(row: pd.Series) -> str:
    """Rank interval for a robust kommun, gränsfall marker for a fragile one."""
    if pd.isna(row.get("is_robust")):
        return "<td class='num'>-</td>"
    if not bool(row["is_robust"]):
        return (
            "<td class='num'>"
            f"<span class='risk-pill granfall'>{SWEDISH_LABELS['boundary_case'].lower()}</span>"
            "</td>"
        )
    return f"<td class='num'>{fmt_range(row['rank_p05'], row['rank_p95'])}</td>"


def _table_html(df: pd.DataFrame) -> str:
    show_uncertainty = "is_robust" in df.columns
    rows = []
    for _, row in df.iterrows():
        code = str(row["municipality_code"]).zfill(4)
        name = MUNICIPALITIES.get(code, str(row.get("municipality_name", "")))
        cells = (
            f"<td class='rank-cell'>{int(row['rank'])}</td>"
            f"<td class='kommun-name'>{name}</td>"
            f"<td class='num'>{fmt_decimal(float(row['kri_score']), 2)}</td>"
            f"<td>{risk_badge(str(row['risk_class']))}</td>"
        )
        if show_uncertainty:
            cells += _uncertainty_cell(row)
        rows.append(f"<tr>{cells}</tr>")
    headers = "<th>Rang</th><th>Kommun</th><th class='num'>KRI</th><th>Riskklass</th>"
    if show_uncertainty:
        headers += f"<th class='num'>{SWEDISH_LABELS['uncertainty']}</th>"
    return (
        "<table class='kri-table'><thead><tr>" + headers + "</tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
    )


def _robust_subtitle(df: pd.DataFrame, fallback: str) -> str:
    if "is_robust" not in df.columns or df["is_robust"].isna().any():
        return fallback
    return (
        f"{fmt_count_of(int(df['is_robust'].sum()), len(df))} robusta vid "
        f"±{fmt_decimal(SENSITIVITY['delta'], 2)} viktvariation"
    )


_rank_help = (
    "**Topp 15 högst risk** är de 15 kommuner med lägst rang (rang 1 = mest sårbar) för valt år, "
    "**topp 15 lägst risk** de 15 mest robusta. KRI är det sammansatta indexet: ju högre värde, "
    "desto större strukturell sårbarhet. Riskklassen bygger på årets kvartiler: under 25:e "
    "percentilen Låg risk, över 75:e percentilen Hög risk, däremellan Medel."
)
if sens_df is not None:
    _sens_year = sens_df[sens_df["year"] == selected_year]
    _rank_help += (
        "\n\n**Osäkerhet.** Vikterna i KRI (0,25 skuld · 0,25 öppen arbetslöshet · 0,20 "
        "försörjningskvot · 0,15 befolkning · 0,15 skattekraft) är motiverade utifrån offentlig "
        "finansieringsteori, inte skattade ur data. Kolumnen visar hur mycket rangen beror på just "
        f"det valet: varje vikt varieras med ±{fmt_decimal(SENSITIVITY['delta'], 2)}, indexet "
        f"räknas om {int(SENSITIVITY['n_draws'])} gånger och intervallet mellan 5:e och 95:e "
        "percentilen av rangen redovisas. En kommun är **robust** när den behåller sin riskklass i "
        f"minst {SENSITIVITY['robust_threshold']:.0%} av omräkningarna, annars **gränsfall**: den "
        "ligger nära gränsen mellan två klasser, vilket inte betyder att klassningen är fel. "
        f"För {selected_year} är {fmt_count_of(int(_sens_year['is_robust'].sum()), len(_sens_year))} "
        "kommuner robusta. Publicerad KRI, rang och riskklass påverkas aldrig av beräkningen."
    )

tbl1, tbl2 = st.columns(2, gap="medium")
with tbl1:
    with st.container(border=True):
        card_header(
            SWEDISH_LABELS["top_highest_risk"],
            _robust_subtitle(top15_high, f"Mest sårbara kommuner {selected_year}"),
            help_md=_rank_help,
        )
        st.markdown(_table_html(top15_high), unsafe_allow_html=True)
with tbl2:
    with st.container(border=True):
        card_header(
            SWEDISH_LABELS["top_lowest_risk"],
            _robust_subtitle(top15_low, f"Mest robusta kommuner {selected_year}"),
            help_md=_rank_help,
        )
        st.markdown(_table_html(top15_low), unsafe_allow_html=True)

# Jump straight to one kommun's analysis (tables are HTML, so links live here).
_jump_options = filtered_df.sort_values("rank")["municipality_name"].tolist()
_jump = st.selectbox(
    "Öppna kommun",
    options=_jump_options,
    index=None,
    placeholder="Välj en kommun för att öppna Kommunanalys",
    key="rv_jump",
)
if _jump:
    st.session_state["selected_municipality"] = _jump
    st.switch_page("views/kommunanalys.py")

st.space("small")

# ---------------------------------------------------------------------------
# All municipalities + exports
# ---------------------------------------------------------------------------
with st.expander(f"Alla kommuner {selected_year}"):
    all_cols = {
        "rank": "Rang",
        "municipality_name": "Kommun",
        "risk_class": "Riskklass",
        "kri_score": "KRI",
        "debt_per_capita": "Skuld per capita (kr)",
        "unemployment": "Öppet arbetslösa (% av 18-65 år)",
        "dependency_ratio": "Försörjningskvot",
        "population_growth": "Befolkningstillväxt 5 år (%)",
        "tax_base_relative": "Skattekraft (% av rikssnitt)",
    }
    all_df = filtered_df.sort_values("rank")[list(all_cols)].rename(columns=all_cols)
    if "rank_p05" in filtered_df.columns:
        all_df["Osäkerhet"] = [
            fmt_range(a, b) if not pd.isna(a) else "-"
            for a, b in zip(filtered_df.sort_values("rank")["rank_p05"],
                            filtered_df.sort_values("rank")["rank_p95"])
        ]
    st.dataframe(
        all_df.style.format({
            "KRI": lambda x: fmt_decimal(x, 2),
            "Skuld per capita (kr)": fmt_int,
            "Öppet arbetslösa (% av 18-65 år)": lambda x: fmt_decimal(x, 1),
            "Försörjningskvot": lambda x: fmt_decimal(x, 3),
            "Befolkningstillväxt 5 år (%)": lambda x: fmt_decimal(x, 1),
            "Skattekraft (% av rikssnitt)": lambda x: fmt_decimal(x, 1),
        }),
        hide_index=True,
        height=420,
        alt=f"Tabell över alla kommuner {selected_year} sorterade efter rang",
        column_config={"Kommun": st.column_config.TextColumn(pinned=True)},
    )
    st.download_button(
        "Ladda ner alla kommuner (CSV)",
        data=all_df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name=f"kri_alla_kommuner_{selected_year}.csv",
        mime="text/csv",
        on_click="ignore",
        icon=":material/download:",
        key="rv_csv_all",
        help="Semikolon mellan kolumner och komma som decimaltecken, öppnas direkt i Excel.",
    )

st.download_button(
    f"Ladda ner rapport (PDF) {selected_year}",
    data=lambda: cached_pdf(selected_year),
    file_name=f"kri_rapport_{selected_year}.pdf",
    mime="application/pdf",
    on_click="ignore",
    type="primary",
    icon=":material/picture_as_pdf:",
    key="rv_pdf",
    help=f"Riksomfattande PDF-rapport för {selected_year} med alla kommuner. "
    "Skapas när du klickar, några sekunder första gången.",
)

render_footer(first_year, last_year)
