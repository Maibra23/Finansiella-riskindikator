"""
app/ui/shell.py
---------------
The application shell shared by every page: branded sidebar with navigation and
the global year selector, page header, and main-column footer.

The sidebar is rendered once per run by the router (app/main.py), so the year
widget keeps one key across all pages and the selected year never resets.
"""

from __future__ import annotations

import html

import streamlit as st

from src.config import SWEDISH_LABELS

KRI_VERSION = "KRI v1.0"


def render_sidebar(pages: dict[str, st.Page], years: list[int]) -> int:
    """Brand, grouped navigation, global year pills and footer. Returns the selected year.

    ``pages`` maps a stable id to its ``st.Page``: startsida, riksoversikt,
    kommunanalys, riskdekomposition, kallor.
    """
    sb = st.sidebar
    sb.markdown(
        """
        <div class="sidebar-brand">
            <div class="brand-mark">KRI Kontrollpanel</div>
            <div class="brand-title">Kommunal Risk</div>
            <div class="brand-sub">Strukturell sårbarhet · SE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sections = [
        ("Översikt", ["startsida", "riksoversikt"]),
        ("Kommun", ["kommunanalys", "riskdekomposition"]),
        ("Metod", ["kallor"]),
    ]
    for label, ids in sections:
        sb.markdown(f'<div class="nav-section">{label}</div>', unsafe_allow_html=True)
        for pid in ids:
            sb.page_link(pages[pid])

    sb.markdown(
        '<div class="sidebar-control"><div class="control-label">Analysår</div></div>',
        unsafe_allow_html=True,
    )
    latest = max(years)
    # One widget for the whole app. The key doubles as the URL query parameter
    # (?ar=2015), so a view can be shared with its year.
    selected = sb.pills(
        "Analysår",
        options=years,
        default=latest,
        required=True,
        key="ar",
        bind="query-params",
        label_visibility="collapsed",
    )
    year = int(selected) if selected is not None else latest
    st.session_state["selected_year"] = year

    sb.markdown(
        f"""
        <div class="sidebar-footer">
            <strong>KÄLLA:</strong> SCB, Arbetsförmedlingen via Kolada<br/>
            Data {min(years)} - {latest} · {KRI_VERSION}
        </div>
        """,
        unsafe_allow_html=True,
    )
    return year


def render_page_header(
    eyebrow: str,
    title: str,
    subtitle: str,
    meta_value: str,
    meta_label: str = "Analysår",
) -> None:
    """Page title block: eyebrow, the page's only h1, subtitle, and a right-hand meta value."""
    st.markdown(
        f"""
<div class="page-header">
  <div class="page-title-group">
    <div class="eyebrow">{html.escape(eyebrow)}</div>
    <h1 class="page-title">{html.escape(title)}</h1>
    <div class="page-sub">{html.escape(subtitle)}</div>
  </div>
  <div class="header-meta">
    <div class="year-display">{html.escape(meta_value)}</div>
    <div>{html.escape(meta_label)}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_footer(first_year: int, last_year: int) -> None:
    """Source line at the bottom of the main column."""
    st.markdown(
        '<div class="footer-note">'
        "<div>Källa: SCB Statistikdatabasen · Arbetsförmedlingen via Kolada</div>"
        f"<div>{KRI_VERSION} · Data {first_year} - {last_year} · "
        f"{SWEDISH_LABELS['weight_sensitivity']} och metod: se Källor och metod</div>"
        "</div>",
        unsafe_allow_html=True,
    )
