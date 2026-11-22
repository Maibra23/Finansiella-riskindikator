"""
Riskdekomposition: why is one municipality's risk what it is?

Contribution of each factor to KRI, z-score radar against the national average,
side-by-side comparison of 2 - 5 municipalities, and their KRI trends.
All user-facing text is in Swedish.
"""

from __future__ import annotations

import streamlit as st

from app.data import load_kri_data, load_sensitivity, year_range, year_slice
from app.formatting import fmt_decimal, fmt_signed
from app.ui.components import card_header, render_kommun_summary
from app.ui.shell import render_footer, render_page_header
from src.config import INDICATOR_COLORS, SWEDISH_LABELS

# Heavy imports (ECharts) come after the shell (already drawn by the router).
from streamlit_echarts import st_echarts

from app.components.charts import (
    build_grouped_bars_comparison,
    build_horizontal_contribution_bar,
    build_line_trend,
    build_radar,
)
from src.risk_scale import RiskScale

# Indicator id -> (contribution column, z column, label, short radar label)
INDICATORS = [
    ("debt", "contribution_debt", "z_debt", "Skuld per capita", "Skuld"),
    ("unemployment", "contribution_unemployment", "z_unemployment",
     SWEDISH_LABELS["unemployment"], SWEDISH_LABELS["unemployment"]),
    ("dependency_ratio", "contribution_dependency", "z_dependency", "Försörjningskvot", "Försörjning"),
    ("population_growth", "contribution_population", "z_population", "Befolkningstillväxt", "Befolkning"),
    ("tax_base", "contribution_tax_base", "z_tax_base", "Skattekraft", "Skattekraft"),
]

# Default selection for "Jämför kommuner" (names must exist in the year's data).
DEFAULT_COMPARE_MUNICIPALITIES: tuple[str, ...] = (
    "Huddinge",
    "Karlskrona",
    "Malmö",
    "Växjö",
    "Kiruna",
)

kri_df = load_kri_data()
sens_df = load_sensitivity()
selected_year: int = st.session_state["selected_year"]
first_year, last_year = year_range(kri_df)

render_page_header(
    eyebrow="Kommun",
    title=SWEDISH_LABELS["risk_decomposition"],
    subtitle="Vilka faktorer som driver risken i en enskild kommun.",
    meta_value=str(selected_year),
)

year_df = year_slice(kri_df, selected_year).sort_values("rank")
n_total = len(year_df)
muni_options = year_df["municipality_name"].tolist()
name_to_code = dict(zip(muni_options, year_df["municipality_code"].astype(str).str.zfill(4)))
rank_of = dict(zip(muni_options, year_df["rank"].astype(int)))

# Shared with Kommunanalys; first visit falls back to the most vulnerable kommun.
shared = st.session_state.get("selected_municipality")
default_idx = muni_options.index(shared) if shared in muni_options else 0

sel_col, sum_col = st.columns([1.2, 2], gap="medium", vertical_alignment="bottom")
with sel_col:
    selected_name: str = st.selectbox(
        SWEDISH_LABELS["select_municipality"],
        options=muni_options,
        index=default_idx,
        format_func=lambda n: f"{rank_of[n]} · {n}",
        key="rd_muni_select",
        help="Sorterad efter rang: 1 är den mest sårbara kommunen.",
    )
st.session_state["selected_municipality"] = selected_name
selected_code = name_to_code[selected_name]
sel_row = year_df[year_df["municipality_code"] == selected_code].iloc[0]

sens_row = None
if sens_df is not None:
    _m = sens_df[(sens_df["municipality_code"] == selected_code) & (sens_df["year"] == selected_year)]
    sens_row = _m.iloc[0] if not _m.empty else None
with sum_col:
    render_kommun_summary(sel_row, sens_row, n_total)

st.page_link(
    "views/kommunanalys.py",
    label=f"Visa kommunanalys för {selected_name}",
    icon=":material/search:",
)

# ---------------------------------------------------------------------------
# Contributions + radar
# ---------------------------------------------------------------------------
with st.container(border=True):
    card_header(
        "Riskbidrag per faktor",
        f"Bidragen summeras till KRI {fmt_decimal(sel_row['kri_score'], 2)}",
        help_md=(
            "Varje stapel är indikatorns vikt gånger kommunens z-poäng. **Rött** drar upp risken, "
            "**grönt** drar ned den, och de fem bidragen summeras exakt till kommunens KRI. "
            "Radardiagrammet visar de underliggande z-poängen jämfört med rikssnittet: utåt = "
            "högre risk på den indikatorn."
        ),
    )
    col_bar, col_radar = st.columns(2)
    with col_bar:
        contributions = {label: float(sel_row[c]) for _, c, _, label, _ in INDICATORS}
        st_echarts(
            build_horizontal_contribution_bar(contributions),
            height="320px",
            key=f"rd_contrib_bar_{selected_code}_{selected_year}",
        )
        _top = max(contributions.items(), key=lambda kv: kv[1])
        st.caption(
            f"Största riskdrivare: **{_top[0]}** ({fmt_signed(_top[1], 2)})."
            if _top[1] > 0.01
            else "Ingen faktor drar upp risken nämnvärt."
        )
    with col_radar:
        z_cols = [z for _, _, z, _, _ in INDICATORS]
        national_avg = year_df[z_cols].mean()
        st_echarts(
            build_radar(
                [float(sel_row[z]) for z in z_cols],
                [float(national_avg[z]) for z in z_cols],
                [short for *_, short in INDICATORS],
            ),
            height="320px",
            key=f"rd_radar_{selected_code}_{selected_year}",
        )

# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------
with st.container(border=True):
    card_header(
        "Jämför kommuner",
        "Välj 2 - 5 kommuner för att jämföra riskbidragen sida vid sida",
        help_md=(
            "Staplarna visar varje faktors bidrag till KRI. Varje indikator har samma färg i hela "
            "panelen. Hovra för att se summan, kommunens totala KRI."
        ),
    )
    default_compare = [n for n in DEFAULT_COMPARE_MUNICIPALITIES if n in muni_options]
    if len(default_compare) < 2:
        default_compare = [selected_name] + [x for x in muni_options if x != selected_name][:4]
    compare_names = st.multiselect(
        "Jämför kommuner",
        options=muni_options,
        default=default_compare[:5],
        max_selections=5,
        key="rd_compare_select",
        label_visibility="collapsed",
    )
    if len(compare_names) >= 2:
        compare_df = year_df.set_index("municipality_name").loc[compare_names]
        components_data = {
            label: compare_df[c].astype(float).tolist() for _, c, _, label, _ in INDICATORS
        }
        st_echarts(
            build_grouped_bars_comparison(
                compare_names,
                components_data,
                colors=[INDICATOR_COLORS[i] for i, *_ in INDICATORS],
            ),
            height="360px",
            key=f"rd_grouped_{selected_year}",
        )
    else:
        st.info("Välj minst 2 kommuner för att se jämförelsen.")

# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------
with st.container(border=True):
    card_header(
        f"KRI-trend {first_year} - {last_year}",
        "Utvecklingen för valda kommuner jämfört med rikssnittet",
    )
    trend_names = compare_names if compare_names else [selected_name]
    pivot = kri_df.pivot_table(index="year", columns="municipality_code", values="kri_score")
    all_years = pivot.index.astype(int).tolist()
    series_dict = {n: pivot[name_to_code[n]].astype(float).tolist() for n in trend_names}
    series_dict["Rikssnitt"] = pivot.mean(axis=1).astype(float).tolist()
    st_echarts(
        build_line_trend(all_years, series_dict, RiskScale.pooled(kri_df)),
        height="380px",
        key=f"rd_trend_{selected_year}",
    )

render_footer(first_year, last_year)
