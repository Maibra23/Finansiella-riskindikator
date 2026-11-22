"""
app/ui/components.py
--------------------
Reusable page components: KPI metric, card header with help popover, risk badge
and the kommun summary line shared by Kommunanalys and Riskdekomposition.

Delta rule (one rule, product-wide, UX_UI_MODERNIZATION_PLAN.md §A7.5):
- the arrow shows the sign of the change (▲ increase, ▼ decrease);
- the colour shows desirability: red when the change means more risk,
  green when it means less, grey when there is no change or no comparison.
"""

from __future__ import annotations

import html
from typing import Literal, Sequence

import pandas as pd
import streamlit as st

from app.formatting import fmt_count_of, fmt_decimal, fmt_range, fmt_signed
from src.config import SWEDISH_LABELS

BetterWhen = Literal["higher", "lower"]


def delta_color_for(better_when: BetterWhen | None, has_delta: bool = True) -> str:
    """Map desirability to st.metric's delta_color.

    "lower" (higher is worse: KRI, skuld, arbetslöshet ...) -> "inverse";
    "higher" (higher is better: skattekraft, befolkning, rang) -> "normal";
    no comparison -> "off".
    """
    if not has_delta or better_when is None:
        return "off"
    return "inverse" if better_when == "lower" else "normal"


def kpi(
    label: str,
    value: str,
    *,
    delta: str | None,
    better_when: BetterWhen | None,
    help: str | None = None,
    period_label: str | None = None,
    spark: Sequence[float] | None = None,
) -> None:
    """Bordered st.metric with the product-wide delta rule.

    ``delta`` must start with "+" or "-" so the arrow follows the sign. Pass
    ``None`` when there is no previous year; pass the text "Oförändrat" when the
    value did not change (shown grey, without an arrow).
    """
    unchanged = delta is not None and not delta.startswith(("+", "-"))
    st.metric(
        label,
        value,
        delta=delta if delta is not None else "Saknas",
        delta_color="off" if (delta is None or unchanged) else delta_color_for(better_when),
        delta_arrow="off" if (delta is None or unchanged) else "auto",
        delta_description=period_label,
        help=help,
        border=True,
        chart_data=list(spark) if spark is not None else None,
        chart_type="line",
    )


def card_header(title: str, subtitle: str = "", help_md: str | None = None) -> None:
    """Card title and subtitle, with an optional "Om ..." popover holding the explanation."""
    if help_md:
        left, right = st.columns([5, 1], vertical_alignment="top")
    else:
        left, right = st.container(), None
    with left:
        st.markdown(
            f'<div class="card-header card-header--plain"><div>'
            f'<div class="card-title">{html.escape(title)}</div>'
            + (f'<div class="card-subtitle">{html.escape(subtitle)}</div>' if subtitle else "")
            + "</div></div>",
            unsafe_allow_html=True,
        )
    if right is not None:
        with right:
            with st.popover("Om", icon=":material/info:", width="stretch"):
                st.markdown(help_md)


def risk_badge(risk_class: str) -> str:
    """Tinted pill with dark text, e.g. "Hög risk". Text carries the meaning, colour supports it."""
    css = {"Låg": "lag", "Medel": "medel", "Hög": "hog"}.get(risk_class, "medel")
    return f'<span class="risk-pill {css}">{html.escape(risk_class)} risk</span>'


def render_kommun_summary(
    row: pd.Series,
    sens_row: pd.Series | None,
    n_total: int,
) -> None:
    """Badge · KRI 1,07 · Rang 6 av 290 · Osäkerhet 3 - 9 (when the sensitivity layer exists)."""
    parts = [
        risk_badge(str(row["risk_class"])),
        f"<span>KRI <strong>{fmt_decimal(float(row['kri_score']), 2)}</strong></span>",
        f"<span>Rang <strong>{fmt_count_of(int(row['rank']), n_total)}</strong></span>",
    ]
    if sens_row is not None and not pd.isna(sens_row.get("rank_p05")):
        parts.append(
            f"<span>{SWEDISH_LABELS['uncertainty']} "
            f"<strong>{fmt_range(sens_row['rank_p05'], sens_row['rank_p95'])}</strong></span>"
        )
    st.markdown(
        '<div class="kommun-summary">' + '<span class="sep">·</span>'.join(parts) + "</div>",
        unsafe_allow_html=True,
    )


def indicator_delta(
    current: float,
    previous: float | None,
    *,
    nd: int,
    unit: str = "",
) -> str | None:
    """Signed delta text with unit for kpi(); None without a previous value, "Oförändrat" for no change."""
    if previous is None or pd.isna(previous):
        return None
    diff = float(current) - float(previous)
    if abs(diff) < 0.5 * 10 ** (-nd):
        return "Oförändrat"
    return f"{fmt_signed(diff, nd)}{unit}"
