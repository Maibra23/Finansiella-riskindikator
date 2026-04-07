"""
app/styles/theme.py
-------------------
Central design system for the KRI Dashboard.

All user-facing strings are in Swedish.
All code identifiers, comments, and docstrings are in English.
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# 1. Color Palette (from PRD section 5)
# ---------------------------------------------------------------------------

COLORS: dict[str, str] = {
    "primary": "#1B2A4A",        # Dark blue — headings, sidebar
    "secondary": "#4A6FA5",      # Steel blue — secondary elements
    "accent": "#C4A35A",         # Gold — highlights, accents
    "low_risk": "#2E7D5B",       # Green
    "medium_risk": "#D4A03C",    # Amber
    "high_risk": "#B94A48",      # Red
    "background": "#F7F8FA",     # Page background
    "text_primary": "#1A1A2E",   # Main body text
    "text_secondary": "#6B7280", # Muted / secondary text
    "grid_lines": "#E5E7EB",     # Chart gridlines
    "white": "#FFFFFF",
    "border": "#D1D5DB",
}

# ---------------------------------------------------------------------------
# 2. apply_streamlit_theme()
# ---------------------------------------------------------------------------

def apply_streamlit_theme() -> None:
    """Apply global Streamlit page config and custom CSS.

    Must be called once at the top of every page file, before any other
    Streamlit call.  Injects Source Sans Pro from Google Fonts, overrides
    default Streamlit colours and component styles.

    All text visible to the user (labels, placeholders, aria text) is in
    Swedish.
    """
    st.set_page_config(
        page_title="KRI Kontrollpanel",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": None,
            "Report a bug": None,
            "About": "**KRI Kontrollpanel** — Kommunal Finansiell Riskindikator\n\nKälla: SCB, Arbetsförmedlingen",
        },
    )

    css = f"""
    <!-- Google Fonts: Source Sans Pro -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,200..900;1,200..900&display=swap" rel="stylesheet">

    <style>
    /* ── Global reset & font ─────────────────────────────────────── */
    html, body, [class*="css"] {{
        font-family: 'Source Sans 3', 'Source Sans Pro', sans-serif !important;
        color: {COLORS['text_primary']};
    }}

    /* ── Page background ─────────────────────────────────────────── */
    .stApp {{
        background-color: {COLORS['background']};
    }}

    /* ── Main content area ───────────────────────────────────────── */
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }}

    /* ── Headings ────────────────────────────────────────────────── */
    h1 {{
        font-family: 'Source Sans 3', sans-serif !important;
        font-weight: 700;
        font-size: 28px;
        color: {COLORS['primary']} !important;
        border-bottom: 3px solid {COLORS['accent']};
        padding-bottom: 0.4rem;
        margin-bottom: 0.8rem;
    }}

    h2 {{
        font-family: 'Source Sans 3', sans-serif !important;
        font-weight: 600;
        font-size: 22px;
        color: {COLORS['primary']} !important;
        margin-bottom: 0.6rem;
    }}

    h3 {{
        font-family: 'Source Sans 3', sans-serif !important;
        font-weight: 600;
        font-size: 18px;
        color: {COLORS['primary']} !important;
    }}

    /* ── Sidebar ─────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background-color: {COLORS['primary']};
    }}

    [data-testid="stSidebar"] * {{
        color: #FFFFFF !important;
    }}

    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stSlider label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stRadio label {{
        color: #E2E8F0 !important;
        font-weight: 600;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    [data-testid="stSidebar"] [data-testid="stSidebarNav"] {{
        border-bottom: 1px solid rgba(255,255,255,0.15);
        padding-bottom: 1rem;
        margin-bottom: 1rem;
    }}

    /* Sidebar nav links */
    [data-testid="stSidebar"] a {{
        color: #CBD5E1 !important;
        text-decoration: none;
    }}

    [data-testid="stSidebar"] a:hover {{
        color: {COLORS['accent']} !important;
    }}

    /* ── Metric / KPI built-in widget ────────────────────────────── */
    [data-testid="stMetric"] {{
        background-color: {COLORS['white']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        padding: 1.1rem 1.4rem;
        box-shadow: 0 1px 4px rgba(27,42,74,0.07);
    }}

    [data-testid="stMetricLabel"] {{
        font-size: 13px !important;
        font-weight: 600 !important;
        color: {COLORS['text_secondary']} !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}

    [data-testid="stMetricValue"] {{
        font-size: 34px !important;
        font-weight: 700 !important;
        color: {COLORS['primary']} !important;
    }}

    [data-testid="stMetricDelta"] svg {{
        width: 14px;
        height: 14px;
    }}

    /* ── DataFrames / Tables (zebra striping) ────────────────────── */
    [data-testid="stDataFrame"] table,
    .stTable table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }}

    [data-testid="stDataFrame"] th,
    .stTable th {{
        background-color: {COLORS['primary']};
        color: #FFFFFF !important;
        font-weight: 600;
        padding: 10px 14px;
        text-align: left;
    }}

    [data-testid="stDataFrame"] tr:nth-child(even),
    .stTable tr:nth-child(even) {{
        background-color: #F0F4F8;
    }}

    [data-testid="stDataFrame"] tr:hover,
    .stTable tr:hover {{
        background-color: #E8EEF7;
    }}

    [data-testid="stDataFrame"] td,
    .stTable td {{
        padding: 9px 14px;
        border-bottom: 1px solid {COLORS['grid_lines']};
        color: {COLORS['text_primary']};
    }}

    /* ── Selectbox / Dropdowns ───────────────────────────────────── */
    .stSelectbox > div > div {{
        border-radius: 6px;
        border-color: {COLORS['border']};
    }}

    /* ── Slider ──────────────────────────────────────────────────── */
    .stSlider [data-baseweb="slider"] {{
        padding: 0 4px;
    }}

    /* ── Buttons ─────────────────────────────────────────────────── */
    .stButton > button {{
        background-color: {COLORS['primary']};
        color: #FFFFFF;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        padding: 0.5rem 1.2rem;
        transition: background-color 0.2s ease;
    }}

    .stButton > button:hover {{
        background-color: {COLORS['secondary']};
        color: #FFFFFF;
    }}

    .stDownloadButton > button {{
        background-color: {COLORS['accent']};
        color: {COLORS['primary']};
        border: none;
        border-radius: 6px;
        font-weight: 700;
    }}

    /* ── Expander ────────────────────────────────────────────────── */
    [data-testid="stExpander"] {{
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        background-color: {COLORS['white']};
    }}

    /* ── Divider ─────────────────────────────────────────────────── */
    hr {{
        border-color: {COLORS['grid_lines']};
        margin: 1.5rem 0;
    }}

    /* ── Risk badge labels used in custom HTML ───────────────────── */
    .risk-badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.02em;
    }}

    .risk-badge-lag   {{ background-color: #D1FAE5; color: {COLORS['low_risk']}; }}
    .risk-badge-medel {{ background-color: #FEF3C7; color: #92400E; }}
    .risk-badge-hog   {{ background-color: #FEE2E2; color: {COLORS['high_risk']}; }}

    /* ── KPI card custom (used by render_kpi_card) ───────────────── */
    .kpi-card {{
        background-color: {COLORS['white']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        padding: 1.1rem 1.4rem;
        box-shadow: 0 1px 4px rgba(27,42,74,0.07);
        height: 100%;
    }}

    .kpi-card-title {{
        font-size: 12px;
        font-weight: 600;
        color: {COLORS['text_secondary']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }}

    .kpi-card-value {{
        font-size: 34px;
        font-weight: 700;
        color: {COLORS['primary']};
        line-height: 1.1;
    }}

    .kpi-card-delta-pos {{
        font-size: 13px;
        color: {COLORS['low_risk']};
        font-weight: 600;
        margin-top: 4px;
    }}

    .kpi-card-delta-neg {{
        font-size: 13px;
        color: {COLORS['high_risk']};
        font-weight: 600;
        margin-top: 4px;
    }}

    .kpi-card-delta-neu {{
        font-size: 13px;
        color: {COLORS['text_secondary']};
        font-weight: 600;
        margin-top: 4px;
    }}
    </style>
    """

    st.markdown(css, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 3. get_plotly_template()
# ---------------------------------------------------------------------------

def get_plotly_template() -> dict:
    """Return a Plotly layout template dict matching the KRI design system.

    Usage::

        import plotly.graph_objects as go
        fig = go.Figure(layout=go.Layout(**get_plotly_template()["layout"]))

    Returns a dict with a ``"layout"`` key ready to spread into go.Layout /
    update_layout calls.  Does NOT return a named Plotly template string —
    use ``fig.update_layout(**get_plotly_template()["layout"])`` directly.
    """
    font_family = "Source Sans 3, Source Sans Pro, sans-serif"

    return {
        "layout": {
            "font": {
                "family": font_family,
                "color": COLORS["text_primary"],
                "size": 13,
            },
            "title": {
                "font": {
                    "family": font_family,
                    "color": COLORS["primary"],
                    "size": 16,
                    "weight": "bold",
                },
                "x": 0.0,
                "xanchor": "left",
            },
            "paper_bgcolor": COLORS["white"],
            "plot_bgcolor": COLORS["white"],
            "colorway": [
                COLORS["primary"],
                COLORS["secondary"],
                COLORS["accent"],
                COLORS["low_risk"],
                COLORS["medium_risk"],
                COLORS["high_risk"],
            ],
            "xaxis": {
                "gridcolor": COLORS["grid_lines"],
                "linecolor": COLORS["grid_lines"],
                "tickfont": {"color": COLORS["text_secondary"], "size": 12},
                "title_font": {"color": COLORS["text_secondary"], "size": 13},
                "zeroline": False,
            },
            "yaxis": {
                "gridcolor": COLORS["grid_lines"],
                "linecolor": COLORS["grid_lines"],
                "tickfont": {"color": COLORS["text_secondary"], "size": 12},
                "title_font": {"color": COLORS["text_secondary"], "size": 13},
                "zeroline": False,
            },
            "legend": {
                "bgcolor": "rgba(0,0,0,0)",
                "bordercolor": COLORS["grid_lines"],
                "borderwidth": 1,
                "font": {"color": COLORS["text_primary"], "size": 12},
            },
            "hoverlabel": {
                "bgcolor": COLORS["white"],
                "bordercolor": COLORS["border"],
                "font": {
                    "family": font_family,
                    "color": COLORS["text_primary"],
                    "size": 13,
                },
            },
            "margin": {"l": 60, "r": 30, "t": 60, "b": 60},
            # Remove Plotly logo / modebar
            "modebar": {"remove": ["logo"]},
        }
    }


# ---------------------------------------------------------------------------
# 4. get_risk_color()
# ---------------------------------------------------------------------------

_RISK_COLOR_MAP: dict[str, str] = {
    "Låg": COLORS["low_risk"],
    "Medel": COLORS["medium_risk"],
    "Hög": COLORS["high_risk"],
    # Tolerant aliases
    "låg": COLORS["low_risk"],
    "medel": COLORS["medium_risk"],
    "hög": COLORS["high_risk"],
    "Lag": COLORS["low_risk"],
    "Hog": COLORS["high_risk"],
}


def get_risk_color(risk_class: str) -> str:
    """Return the hex color for a Swedish risk class label.

    Parameters
    ----------
    risk_class:
        One of ``"Låg"``, ``"Medel"``, or ``"Hög"`` (case-insensitive).

    Returns
    -------
    str
        Hex color string, e.g. ``"#2E7D5B"``.

    Raises
    ------
    ValueError
        If ``risk_class`` is not recognised.
    """
    color = _RISK_COLOR_MAP.get(risk_class)
    if color is None:
        raise ValueError(
            f"Okänd riskklass: '{risk_class}'. "
            f"Giltiga värden: 'Låg', 'Medel', 'Hög'."
        )
    return color


def get_risk_badge_html(risk_class: str) -> str:
    """Return an HTML badge span for the given Swedish risk class.

    Produces a coloured inline badge suitable for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    css_class_map = {
        "Låg": "risk-badge-lag",
        "Medel": "risk-badge-medel",
        "Hög": "risk-badge-hog",
    }
    css_cls = css_class_map.get(risk_class, "risk-badge-neu")
    return f'<span class="risk-badge {css_cls}">{risk_class}</span>'


# ---------------------------------------------------------------------------
# 5. render_kpi_card()
# ---------------------------------------------------------------------------

def render_kpi_card(
    title: str,
    value: str | int | float,
    delta: float | None = None,
    prefix: str = "",
    suffix: str = "",
    delta_inverted: bool = False,
    help_text: str | None = None,
) -> None:
    """Render a KPI metric card using custom HTML for consistent styling.

    Parameters
    ----------
    title:
        Swedish label shown above the value in small caps,
        e.g. ``"Högrisk kommuner"``.
    value:
        The primary metric value.  Pass a pre-formatted string for full
        control (e.g. ``"3 452 kr"``), or a number which will be formatted
        with thousands separator.
    delta:
        Optional change vs previous period.  Positive → good by default;
        pass ``delta_inverted=True`` for metrics where positive = bad
        (e.g. number of high-risk municipalities).
    prefix:
        String prepended to the value display, e.g. ``"kr "`` (rare).
    suffix:
        String appended to the value display, e.g. ``" %"`` or ``" kr"``.
    delta_inverted:
        When ``True``, a positive delta is displayed in red (worse) and a
        negative delta in green (better).  Default: ``False``.
    help_text:
        Optional Swedish tooltip shown as a small ``ⓘ`` icon.
    """
    # Format numeric values
    if isinstance(value, (int, float)):
        formatted_value = f"{value:,.0f}".replace(",", "\u202f")
    else:
        formatted_value = str(value)

    display_value = f"{prefix}{formatted_value}{suffix}"

    # Delta HTML
    delta_html = ""
    if delta is not None:
        sign = "+" if delta > 0 else ""
        delta_str = f"{sign}{delta:,.1f}".replace(",", "\u202f")
        if delta == 0:
            css_cls = "kpi-card-delta-neu"
            arrow = "→"
            delta_label = "oförändrat"
        elif (delta > 0 and not delta_inverted) or (delta < 0 and delta_inverted):
            css_cls = "kpi-card-delta-pos"
            arrow = "▲"
            delta_label = "mot föregående år"
        else:
            css_cls = "kpi-card-delta-neg"
            arrow = "▼"
            delta_label = "mot föregående år"

        delta_html = (
            f'<div class="{css_cls}">'
            f'{arrow} {delta_str}{suffix} {delta_label}'
            f'</div>'
        )

    help_html = ""
    if help_text:
        help_html = (
            f'<span title="{help_text}" style="cursor:help; color: #9CA3AF; '
            f'font-size:14px; margin-left:4px;">ⓘ</span>'
        )

    card_html = f"""
    <div class="kpi-card">
        <div class="kpi-card-title">{title}{help_html}</div>
        <div class="kpi-card-value">{display_value}</div>
        {delta_html}
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 6. Sidebar helpers
# ---------------------------------------------------------------------------

def render_sidebar_header(subtitle: str | None = None) -> None:
    """Render KRI branding block at the top of the sidebar.

    Parameters
    ----------
    subtitle:
        Optional Swedish subtitle line under the logo text.
    """
    logo_html = f"""
    <div style="padding: 0.5rem 0 1.2rem 0; border-bottom: 1px solid rgba(255,255,255,0.15); margin-bottom: 1.2rem;">
        <div style="font-size: 20px; font-weight: 700; color: #FFFFFF; letter-spacing: -0.01em;">
            📊 KRI Kontrollpanel
        </div>
        <div style="font-size: 11px; color: #94A3B8; margin-top: 3px; line-height: 1.4;">
            {subtitle or "Kommunal Finansiell Riskindikator"}
        </div>
    </div>
    """
    st.sidebar.markdown(logo_html, unsafe_allow_html=True)


def render_data_source_footer() -> None:
    """Render a small 'Källa' footer at the bottom of the sidebar."""
    footer_html = """
    <div style="position: fixed; bottom: 1rem; font-size: 11px; color: #64748B; line-height: 1.5;">
        <strong style="color:#94A3B8;">Källa:</strong> SCB, Arbetsförmedlingen<br>
        <span style="color:#64748B;">Period: 2010–2024</span>
    </div>
    """
    st.sidebar.markdown(footer_html, unsafe_allow_html=True)
