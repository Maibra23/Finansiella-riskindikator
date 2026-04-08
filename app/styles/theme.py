"""
Central design system for the KRI Dashboard (Streamlit + ECharts).

All user-facing strings passed into render helpers must be in Swedish.
All code identifiers, comments, and docstrings are in English.
"""

from __future__ import annotations

import copy
import html
from typing import Any, Literal

import streamlit as st
from streamlit.errors import StreamlitAPIException

from src.config import COLORS

# ---------------------------------------------------------------------------
# Theme application
# ---------------------------------------------------------------------------


def apply_streamlit_theme() -> None:
    """Set page config and inject banking-style CSS (fonts, sidebar, layout)."""
    try:
        st.set_page_config(
            page_title="KRI Kontrollpanel",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                "Get Help": None,
                "Report a bug": None,
                "About": "**KRI Kontrollpanel**. Kommunal finansiell riskindikator.\n\nKälla: SCB, Arbetsförmedlingen",
            },
        )
    except StreamlitAPIException:
        # Already set on first page in this session (e.g. home → multipage navigation).
        pass

    p = COLORS["primary"]
    bg = COLORS["bg"]
    accent = COLORS["accent"]
    border = COLORS["border"]
    text_pri = COLORS["text_primary"]
    text_sec = COLORS["text_secondary"]
    text_ter = COLORS["text_tertiary"]
    card = COLORS["card_bg"]
    hover = COLORS["hover"]
    low = COLORS["low_risk"]
    high = COLORS["high_risk"]

    css = f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">

    <style>
    /* Shared rhythm: main + sidebar use the same horizontal gutter so text keylines align. */
    :root {{
        --kri-pad-x: 1.5rem;
        --kri-pad-y: 2rem;
        --kri-label-upper: 11px;
        --kri-label-track: 1.5px;
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    /* Hide chrome but keep sidebar expand control usable (descendant may stay visible). */
    header[data-testid="stHeader"] {{visibility: hidden; height: 0; overflow: visible;}}
    [data-testid="collapsedControl"] {{
        visibility: visible !important;
        position: fixed !important;
        top: 0.65rem !important;
        left: 0.65rem !important;
        z-index: 1002 !important;
    }}

    html, body {{
        font-family: 'Source Sans Pro', -apple-system, sans-serif !important;
    }}

    /* Main content only — never force dark body text on [class*="css"] or it paints the sidebar unreadable */
    [data-testid="stMain"],
    [data-testid="stMain"] .block-container {{
        color: {text_pri};
    }}

    .stApp {{
        background-color: {bg};
    }}

    .block-container {{
        padding-top: var(--kri-pad-y) !important;
        padding-bottom: var(--kri-pad-y) !important;
        padding-left: var(--kri-pad-x) !important;
        padding-right: var(--kri-pad-x) !important;
        max-width: 1480px !important;
    }}

    [data-testid="stSidebar"] {{
        background-color: {p};
        min-width: 260px !important;
        width: 260px !important;
        color: #E8ECF4 !important;
        border-right: 1px solid {border};
    }}

    /* Fallback if config.toml client.showSidebarNavigation is not applied */
    [data-testid="stSidebarHeader"] {{
        display: none !important;
    }}

    [data-testid="stSidebarContent"] {{
        color: #E8ECF4 !important;
    }}

    /* Sidebar gutters: same --kri-pad-x / --kri-pad-y as main for aligned keylines */
    [data-testid="stSidebar"] .block-container {{
        padding-top: var(--kri-pad-y) !important;
        padding-bottom: var(--kri-pad-y) !important;
        padding-left: var(--kri-pad-x) !important;
        padding-right: var(--kri-pad-x) !important;
        max-width: 100% !important;
    }}
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
        width: 100%;
    }}

    [data-testid="stSidebar"] label {{
        color: rgba(255,255,255,0.5) !important;
        font-size: var(--kri-label-upper) !important;
        text-transform: uppercase !important;
        letter-spacing: var(--kri-label-track) !important;
        font-weight: 600 !important;
    }}

    [data-testid="stSidebar"] .stSlider {{
        color: #E8ECF4 !important;
    }}
    /* White select box: must stay dark text */
    [data-testid="stSidebar"] [data-baseweb="select"] > div {{
        color: {text_pri} !important;
    }}

    [data-testid="stSidebarNav"] {{
        padding-top: 0.25rem;
    }}

    [data-testid="stSidebarNav"] ul {{
        padding-left: 0 !important;
    }}

    [data-testid="stSidebarNav"] li > a {{
        color: rgba(255,255,255,0.75) !important;
        border-radius: 4px;
        padding: 9px 12px !important;
        border-left: 2px solid transparent !important;
    }}

    [data-testid="stSidebarNav"] li > a:hover {{
        background: rgba(255,255,255,0.05) !important;
        color: #FFFFFF !important;
    }}

    [data-testid="stSidebarNav"] li > a[aria-current="page"] {{
        background: rgba(196,163,90,0.12) !important;
        color: #FFFFFF !important;
        border-left: 2px solid {accent} !important;
    }}

    /* Sidlänkar: Streamlit sätter mörk text på mörk bakgrund — tvinga ljus text + spann. */
    [data-testid="stSidebarContent"] a[href] {{
        text-decoration: none !important;
        color: rgba(255, 255, 255, 0.92) !important;
        font-size: 13.5px !important;
        line-height: 1.45 !important;
        font-family: 'Source Sans Pro', -apple-system, sans-serif !important;
        background: transparent !important;
        background-color: transparent !important;
    }}
    [data-testid="stSidebarContent"] a[href] span {{
        color: rgba(255, 255, 255, 0.92) !important;
    }}
    [data-testid="stSidebarContent"] a[href]:hover,
    [data-testid="stSidebarContent"] a[href]:hover span {{
        color: #FFFFFF !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
    }}
    [data-testid="stSidebarContent"] a[href][aria-current="page"],
    [data-testid="stSidebarContent"] a[href][aria-current="page"] span {{
        color: #FFFFFF !important;
        background-color: rgba(196, 163, 90, 0.22) !important;
    }}

    [data-testid="stSidebar"] [data-testid="stCaption"],
    [data-testid="stSidebar"] .stCaption {{
        color: rgba(255, 255, 255, 0.72) !important;
    }}

    .stApp > div > div > div > div {{
        padding-top: 0.5rem;
    }}

    [data-testid="stVerticalBlock"] > div {{
        gap: 0.5rem;
    }}

    /* Equal-height KPI columns: stretch Streamlit horizontal rows in main */
    [data-testid="stMain"] [data-testid="stHorizontalBlock"] {{
        align-items: stretch !important;
    }}
    [data-testid="stMain"] [data-testid="column"] {{
        display: flex !important;
        flex-direction: column !important;
    }}
    [data-testid="stMain"] [data-testid="column"] > div {{
        flex: 1 1 auto !important;
        min-height: 0 !important;
    }}

    /* Exportera-rad: samma kortstil som KPI (använd st.container(border=True)) */
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {{
        background: {card} !important;
        border: 1px solid {border} !important;
        border-radius: 4px !important;
        padding: 16px 20px !important;
    }}
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] button {{
        width: 100%;
    }}

    /* KPI cards */
    .kpi-card {{
        background: {card};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 20px 22px;
        position: relative;
        overflow: hidden;
        height: 100%;
        min-height: 148px;
        box-sizing: border-box;
    }}
    .kpi-card::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 3px;
        height: 100%;
        background: {p};
    }}
    .kpi-card.kpi-primary::before {{ background: {p}; }}
    .kpi-card.kpi-accent::before {{ background: {accent}; }}
    .kpi-card.kpi-danger::before {{ background: {high}; }}
    .kpi-card.kpi-success::before {{ background: {low}; }}
    .kpi-card.kpi-card--tipped {{
        cursor: help;
    }}

    .kpi-label {{
        font-size: var(--kri-label-upper);
        text-transform: uppercase;
        letter-spacing: var(--kri-label-track);
        color: {text_sec};
        margin-bottom: 10px;
        font-weight: 600;
    }}
    .kpi-value {{
        font-size: 32px;
        font-weight: 700;
        color: {p};
        letter-spacing: 0.02em;
        line-height: 1.1;
        font-variant-numeric: tabular-nums;
    }}
    .kpi-unit {{
        font-size: 14px;
        font-weight: 400;
        color: {text_sec};
        margin-left: 0.45em;
        white-space: nowrap;
    }}
    .kpi-delta {{
        display: flex;
        align-items: center;
        gap: 5px;
        font-size: 12px;
        margin-top: 8px;
        font-family: 'IBM Plex Mono', monospace;
    }}
    .delta-up {{ color: {high}; }}
    .delta-down {{ color: {low}; }}
    .delta-flat {{ color: {text_ter}; }}
    .kpi-delta.delta-up::before {{ content: '▲'; font-size: 10px; }}
    .kpi-delta.delta-down::before {{ content: '▼'; font-size: 10px; }}
    .kpi-delta.delta-flat::before {{ content: '●'; font-size: 10px; }}

    .mono, .num {{ font-family: 'IBM Plex Mono', monospace; }}

    /* Cards */
    .card {{
        background: {card};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 22px 24px;
        margin-bottom: 0;
    }}
    .card-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 18px;
        padding-bottom: 14px;
        border-bottom: 1px solid {border};
    }}
    .card-title {{
        font-size: 15px;
        font-weight: 700;
        color: {p};
        letter-spacing: -0.2px;
    }}
    .card-subtitle {{
        font-size: 11.5px;
        color: {text_sec};
        margin-top: 2px;
    }}
    .card-tag {{
        font-size: 9.5px;
        font-family: 'IBM Plex Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: 4px 8px;
        background: {bg};
        color: {text_sec};
        border-radius: 2px;
    }}

    /* Page header */
    .page-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-bottom: 28px;
        padding-bottom: 20px;
        border-bottom: 1px solid {border};
    }}
    .eyebrow {{
        font-size: var(--kri-label-upper);
        text-transform: uppercase;
        letter-spacing: var(--kri-label-track);
        color: {accent};
        font-weight: 600;
        margin-bottom: 6px;
    }}
    .page-title {{
        font-size: 28px;
        font-weight: 700;
        color: {p};
        letter-spacing: -0.5px;
        margin: 0 0 4px 0;
    }}
    .page-sub {{
        font-size: 13.5px;
        color: {text_sec};
    }}
    .header-meta {{
        text-align: right;
        font-size: 11px;
        color: {text_ter};
        font-family: 'IBM Plex Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }}
    .year-display {{
        font-size: 32px;
        color: {p};
        font-family: 'Source Sans Pro', sans-serif;
        font-weight: 300;
        letter-spacing: -1px;
        line-height: 1;
        margin-bottom: 4px;
    }}

    /* Sidebar brand */
    .sidebar-brand {{
        padding-bottom: 24px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 24px;
    }}
    .brand-mark {{
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: var(--kri-label-upper);
        letter-spacing: var(--kri-label-track);
        text-transform: uppercase;
        color: {accent};
        font-weight: 600;
    }}
    .brand-mark::before {{
        content: '';
        display: block;
        width: 4px;
        height: 16px;
        background: {accent};
    }}
    .brand-title {{
        font-size: 17px;
        font-weight: 700;
        margin-top: 10px;
        color: #FFFFFF;
        letter-spacing: -0.2px;
    }}
    .brand-sub {{
        font-size: var(--kri-label-upper);
        color: rgba(255,255,255,0.55);
        margin-top: 2px;
    }}
    .nav-section-label,
    .nav-section {{
        font-size: var(--kri-label-upper);
        text-transform: uppercase;
        letter-spacing: var(--kri-label-track);
        color: rgba(255,255,255,0.4);
        margin-bottom: 12px;
    }}
    .control-label {{
        font-size: var(--kri-label-upper);
        text-transform: uppercase;
        letter-spacing: var(--kri-label-track);
        color: rgba(255,255,255,0.5);
        margin-bottom: 10px;
        margin-top: 8px;
    }}
    .sidebar-footer {{
        font-size: 10px;
        color: rgba(255,255,255,0.35);
        padding-top: 16px;
        margin-top: 8px;
        border-top: 1px solid rgba(255,255,255,0.06);
        line-height: 1.5;
    }}

    /* Tables (HTML) */
    .kri-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }}
    .kri-table thead th {{
        text-align: left;
        padding: 10px 12px;
        font-size: var(--kri-label-upper);
        text-transform: uppercase;
        letter-spacing: var(--kri-label-track);
        color: {text_sec};
        border-bottom: 1.5px solid {p};
        font-weight: 600;
    }}
    .kri-table thead th.num {{ text-align: right; }}
    .kri-table tbody td {{
        padding: 11px 12px;
        border-bottom: 1px solid {border};
        color: {text_pri};
    }}
    .kri-table tbody td.num {{
        text-align: right;
        font-variant-numeric: tabular-nums;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12.5px;
    }}
    .kri-table tbody tr:hover {{ background: {hover}; }}
    .rank-cell {{
        font-family: 'IBM Plex Mono', monospace;
        color: {text_ter};
        font-size: 11.5px;
        width: 36px;
    }}
    .kommun-name {{ font-weight: 600; color: {p}; }}
    .risk-pill {{
        display: inline-block;
        padding: 2px 9px;
        border-radius: 2px;
        font-size: 10.5px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.7px;
    }}
    .risk-pill.hog {{ background: rgba(185,74,72,0.12); color: {high}; border: 1px solid rgba(185,74,72,0.3); }}
    .risk-pill.medel {{ background: rgba(212,160,60,0.12); color: #8B6914; border: 1px solid rgba(212,160,60,0.3); }}
    .risk-pill.lag {{ background: rgba(46,125,91,0.12); color: {low}; border: 1px solid rgba(46,125,91,0.3); }}

    .footer-note {{
        margin-top: 28px;
        padding-top: 16px;
        border-top: 1px solid {border};
        font-size: 11px;
        color: {text_ter};
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px;
    }}
    .footer-note code {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10.5px;
        background: {bg};
        padding: 2px 6px;
        border-radius: 2px;
        color: {text_sec};
    }}

    /* ── Sidopanel: år-chips + riskklass-piller ─────────────── */
    /* Bred regel — träffar alla knappar i sidopanelen oberoende av stPills-hierarki.
       button * fångar text i p/span/div oavsett vad Streamlit renderar inuti knappen. */
    [data-testid="stSidebar"] button {{
        background-color: rgba(255,255,255,0.10) !important;
        border: 1px solid rgba(255,255,255,0.25) !important;
        border-radius: 4px !important;
        padding: 4px 9px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 11px !important;
        font-weight: 500 !important;
        min-height: auto !important;
        height: auto !important;
        line-height: 1.4 !important;
        text-transform: none !important;
        letter-spacing: 0 !important;
    }}
    [data-testid="stSidebar"] button,
    [data-testid="stSidebar"] button * {{
        color: #F3F4F6 !important;
    }}
    [data-testid="stSidebar"] button:hover {{
        background-color: rgba(255,255,255,0.18) !important;
        border-color: rgba(255,255,255,0.40) !important;
    }}
    [data-testid="stSidebar"] button:hover,
    [data-testid="stSidebar"] button:hover * {{
        color: #FFFFFF !important;
    }}
    /* Vald chip — guld bakgrund, mörk marin text */
    [data-testid="stSidebar"] button[aria-pressed="true"] {{
        background-color: {accent} !important;
        border-color: {accent} !important;
        font-weight: 600 !important;
    }}
    [data-testid="stSidebar"] button[aria-pressed="true"],
    [data-testid="stSidebar"] button[aria-pressed="true"] * {{
        color: {p} !important;
    }}

    /* ── Riskklass: punkt-legend ─────────────────────────────── */
    .sidebar-control {{
        margin-top: 24px;
        padding-top: 20px;
        border-top: 1px solid rgba(255,255,255,0.08);
    }}
    .riskklass-legend {{ margin-top: 8px; }}
    .riskklass-rad {{
        display: flex;
        align-items: center;
        font-size: 13.5px;
        color: rgba(255,255,255,0.75);
        margin-bottom: 8px;
        line-height: 1.35;
    }}
    .riskklass-punkt {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
        flex-shrink: 0;
    }}

    /* ── Landing page (.lp-*) — scoped to home; tokens from COLORS ───────── */
    .lp-hero {{
        background: linear-gradient(145deg, {p} 0%, {COLORS["primary_light"]} 55%, #152a52 100%);
        border-radius: 4px;
        padding: 22px 28px 20px;
        margin-bottom: 0;
        border: 1px solid rgba(196,163,90,0.25);
    }}
    .lp-hero-inner {{
        max-width: 720px;
        margin: 0 auto;
        text-align: left;
    }}
    .lp-eyebrow {{
        font-size: var(--kri-label-upper);
        text-transform: uppercase;
        letter-spacing: var(--kri-label-track);
        color: {accent};
        font-weight: 600;
        margin-bottom: 6px;
    }}
    /* Main sets color on stMain — hero must override for h1 + text */
    [data-testid="stMain"] .lp-hero h1.lp-headline,
    .lp-hero h1.lp-headline,
    .lp-hero .lp-headline {{
        font-size: clamp(24px, 3.6vw, 36px);
        font-weight: 700;
        color: #FFFFFF !important;
        letter-spacing: -0.5px;
        line-height: 1.2;
        margin: 0 0 10px 0;
        border: none !important;
        padding: 0 !important;
    }}
    .lp-hero-lead {{
        font-size: 15px;
        color: rgba(255,255,255,0.92);
        line-height: 1.5;
        margin: 0;
        max-width: 38rem;
        text-align: left;
    }}
    .lp-hero-cta {{
        font-size: 13px;
        color: rgba(255,255,255,0.78);
        line-height: 1.45;
        margin: 10px 0 0 0;
        max-width: 38rem;
        text-align: left;
    }}

    .lp-stat-strip {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0;
        background: {card};
        border: 1px solid {border};
        border-top: 3px solid {accent};
        border-radius: 0 0 4px 4px;
        margin-top: -1px;
        margin-bottom: 28px;
        overflow: hidden;
    }}
    .lp-stat-cell {{
        padding: 18px 20px;
        border-right: 1px solid {border};
    }}
    .lp-stat-cell:last-child {{ border-right: none; }}
    .lp-stat-label {{
        font-size: var(--kri-label-upper);
        text-transform: uppercase;
        letter-spacing: var(--kri-label-track);
        color: {text_sec};
        font-weight: 600;
        margin-bottom: 6px;
    }}
    .lp-stat-value {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 28px;
        font-weight: 600;
        color: {p};
        line-height: 1.1;
        letter-spacing: -0.5px;
    }}
    .lp-stat-unit {{
        font-size: 13px;
        font-weight: 400;
        color: {text_sec};
        margin-left: 4px;
    }}

    .lp-section {{
        margin-bottom: 22px;
    }}
    .lp-section-title {{
        font-size: var(--kri-label-upper);
        text-transform: uppercase;
        letter-spacing: var(--kri-label-track);
        color: {accent};
        font-weight: 600;
        margin-bottom: 10px;
    }}
    .lp-card-light {{
        background: {card};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 22px 24px;
    }}
    .lp-body {{
        font-size: 15px;
        color: {text_pri};
        line-height: 1.65;
        margin: 0;
    }}
    .lp-body-secondary {{
        font-size: 14px;
        color: {text_sec};
        line-height: 1.6;
        margin: 10px 0 0 0;
    }}
    .lp-explain-card .lp-body,
    .lp-explain-card .lp-body-secondary {{
        max-width: min(100%, 68ch);
        text-align: left;
    }}

    .lp-card-light.lp-visual {{
        padding: 12px 14px 10px !important;
        display: flex;
        flex-direction: column;
        align-items: stretch;
    }}
    .lp-visual {{
        margin-top: 10px;
    }}
    .lp-weight-list {{
        margin-bottom: 10px;
    }}
    .lp-weight-row {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 4px;
        font-size: 12.5px;
    }}
    .lp-weight-name {{
        flex: 0 0 min(42%, 200px);
        color: {text_pri};
        font-weight: 600;
    }}
    .lp-weight-bar-wrap {{
        flex: 1;
        height: 6px;
        background: {bg};
        border-radius: 2px;
        overflow: hidden;
        border: 1px solid {border};
    }}
    .lp-weight-bar {{
        height: 100%;
        background: {COLORS["secondary"]};
        border-radius: 1px;
    }}
    .lp-weight-pct {{
        flex: 0 0 44px;
        text-align: right;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        color: {text_sec};
    }}
    /* Flow diagram: max width calc(33rem * 1.3) (30% larger than prior 33rem); centered. */
    .lp-flow-svg-wrap {{
        max-width: min(100%, calc(33rem * 1.3));
        width: min(100%, calc(33rem * 1.3));
        align-self: center;
        margin: 8px auto 0;
        overflow: visible;
    }}
    .lp-flow-svg {{
        display: block;
        width: 100%;
        height: auto;
        margin: 0 auto;
    }}

    .lp-steps {{
        display: flex;
        flex-direction: row;
        align-items: stretch;
        gap: 0;
        margin-top: 4px;
    }}
    .lp-step {{
        flex: 1 1 0;
        min-width: 0;
        background: {card};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 18px 18px 20px;
        position: relative;
        border-left: 3px solid {accent};
        transition: box-shadow 0.2s ease, border-color 0.2s ease;
    }}
    .lp-step-connector {{
        flex: 0 0 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: {accent};
        align-self: center;
        opacity: 0.92;
    }}
    .lp-step-arrow-svg {{
        width: 28px;
        height: 16px;
        flex-shrink: 0;
        display: block;
    }}
    .lp-step:hover {{
        box-shadow: 0 4px 14px rgba(11,31,63,0.07);
        border-color: rgba(196,163,90,0.35);
    }}
    .lp-step-num {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        color: {accent};
        font-weight: 600;
        margin-bottom: 8px;
    }}
    .lp-step-title {{
        font-size: 14px;
        font-weight: 700;
        color: {p};
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .lp-step svg {{
        flex-shrink: 0;
        color: {p};
    }}
    .lp-step-text {{
        font-size: 13px;
        color: {text_sec};
        line-height: 1.55;
        margin: 0;
    }}

    .lp-nav-section-title {{
        font-size: 15px;
        font-weight: 700;
        color: {p};
        margin: 28px 0 14px 0;
        padding-bottom: 10px;
        border-bottom: 1px solid {border};
    }}
    .lp-nav-section-title-in-panel {{
        margin-top: 0;
        margin-bottom: 12px;
    }}
    .lp-nav-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin-bottom: 8px;
    }}
    .lp-nav-card {{
        background: {card};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 20px 20px 18px;
        border-left: 3px solid {accent};
        min-height: 120px;
        transition: box-shadow 0.2s ease, border-color 0.2s ease;
    }}
    .lp-nav-card:hover {{
        box-shadow: 0 4px 16px rgba(11,31,63,0.08);
        border-color: rgba(196,163,90,0.4);
    }}
    .lp-nav-card-head {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 10px;
    }}
    .lp-nav-tag {{
        font-size: 9.5px;
        font-family: 'IBM Plex Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        padding: 4px 8px;
        background: {bg};
        color: {text_sec};
        border-radius: 2px;
    }}
    .lp-nav-title {{
        font-size: 15px;
        font-weight: 700;
        color: {p};
        margin: 0 0 8px 0;
        letter-spacing: -0.2px;
    }}
    .lp-nav-desc {{
        font-size: 13px;
        color: {text_sec};
        line-height: 1.5;
        margin: 0;
    }}
    .lp-nav-icon {{
        width: 40px;
        height: 40px;
        border-radius: 4px;
        background: rgba(11,31,63,0.06);
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid {border};
    }}
    .lp-nav-icon svg {{
        width: 22px;
        height: 22px;
        stroke: {p};
        fill: none;
        stroke-width: 1.6;
    }}

    .lp-cred {{
        margin-top: 28px;
        padding: 16px 20px 18px;
        border: 1px solid {border};
        border-radius: 4px;
        background: {card};
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 10px;
        font-size: 12px;
        color: {text_ter};
        text-align: center;
    }}
    .lp-cred-pills {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: center;
        justify-content: center;
    }}
    .lp-cred-pill {{
        font-size: 10.5px;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        padding: 4px 10px;
        border-radius: 2px;
        background: {bg};
        border: 1px solid {border};
        color: {text_sec};
        font-weight: 600;
    }}
    .lp-cred-meta {{
        font-family: 'Source Sans Pro', sans-serif;
        font-size: 11px;
        color: {text_sec};
        line-height: 1.4;
        text-align: center;
        max-width: 100%;
    }}

    @media (max-width: 900px) {{
        .lp-stat-strip {{ grid-template-columns: repeat(2, 1fr); }}
        .lp-stat-cell:nth-child(2) {{ border-right: none; }}
        .lp-steps {{ flex-direction: column; }}
        .lp-step-connector {{
            flex: 0 0 auto;
            width: 100%;
            height: 28px;
            padding: 4px 0;
        }}
        .lp-step-arrow-svg {{
            transform: rotate(90deg);
            width: 22px;
            height: 28px;
        }}
        .lp-nav-grid {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 520px) {{
        .lp-stat-strip {{ grid-template-columns: 1fr; }}
        .lp-stat-cell {{ border-right: none; border-bottom: 1px solid {border}; }}
        .lp-stat-cell:last-child {{ border-bottom: none; }}
        .lp-hero {{ padding: 18px 16px 16px; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
        .lp-step, .lp-nav-card {{ transition: none !important; }}
        .lp-step-arrow-svg {{ transition: none !important; }}
    }}
    </style>
    """

    st.markdown(css, unsafe_allow_html=True)


def get_tooltip_style() -> dict[str, Any]:
    """Return consistent ECharts tooltip styling (light card, dark text)."""
    return {
        "trigger": "axis",
        "backgroundColor": "#FFFFFF",
        "borderColor": COLORS["border"],
        "borderWidth": 1,
        "padding": [10, 14],
        "textStyle": {
            "color": COLORS["text_primary"],
            "fontFamily": "Source Sans Pro",
            "fontSize": 13,
        },
        "extraCssText": "box-shadow: 0 4px 16px rgba(0,0,0,0.10); border-radius: 6px;",
        "axisPointer": {
            "type": "line",
            "lineStyle": {"color": COLORS["accent"], "width": 1, "type": "dashed"},
        },
    }


def get_axis_style(axis_type: Literal["value", "category"] = "value") -> dict[str, Any]:
    """Return axis styling; horizontal dashed grids for value axes only."""
    font = "IBM Plex Mono" if axis_type == "value" else "Source Sans Pro"
    out: dict[str, Any] = {
        "axisLine": {"lineStyle": {"color": COLORS["grid"]}},
        "axisTick": {"show": False},
        "axisLabel": {
            "color": COLORS["text_secondary"],
            "fontSize": 10,
            "fontFamily": font,
        },
    }
    if axis_type == "value":
        out["splitLine"] = {
            "show": True,
            "lineStyle": {"color": COLORS["grid"], "type": "dashed"},
        }
    else:
        out["splitLine"] = {"show": False}
    return out


def format_swedish_int(n: int | float) -> str:
    """Format a whole number with no-break space as thousands separator (Swedish UI)."""
    v = int(round(float(n)))
    sign = "-" if v < 0 else ""
    body = f"{abs(v):,}".replace(",", "\u00a0")
    return f"{sign}{body}"


def get_echarts_base_options() -> dict[str, Any]:
    """Shared ECharts JSON base; merge chart-specific options on top."""
    base = {
        "backgroundColor": COLORS["card_bg"],
        "textStyle": {"fontFamily": "Source Sans Pro", "color": COLORS["text_primary"]},
        "grid": {
            "left": 56,
            "right": 30,
            "top": 50,
            "bottom": 70,
            "containLabel": True,
        },
        "tooltip": get_tooltip_style(),
        "animation": True,
        "animationDuration": 400,
    }
    return base


def render_kpi_card(
    label: str,
    value: str,
    unit: str,
    delta: str,
    delta_direction: Literal["up", "down", "flat"],
    variant: Literal["primary", "accent", "danger", "success"],
    tooltip: str | None = None,
) -> str:
    """Return HTML for a KPI card (caller uses st.markdown(..., unsafe_allow_html=True).

    Optional ``tooltip`` is exposed as the HTML ``title`` attribute (native hover text).
    """
    tip_class = " kpi-card--tipped" if tooltip else ""
    tip_attr = (
        f' title="{html.escape(tooltip, quote=True)}"' if tooltip else ""
    )
    return f"""
<div class="kpi-card kpi-{variant}{tip_class}"{tip_attr}>
  <div class="kpi-label">{label}</div>
  <div class="kpi-value">{value}<span class="kpi-unit">{unit}</span></div>
  <div class="kpi-delta delta-{delta_direction}">{delta}</div>
</div>
"""


def render_card_header(title: str, subtitle: str, tag: str) -> str:
    """Return HTML for a card header row."""
    return f"""
<div class="card-header">
  <div>
    <div class="card-title">{title}</div>
    <div class="card-subtitle">{subtitle}</div>
  </div>
  <span class="card-tag">{tag}</span>
</div>
"""


def render_page_header(eyebrow: str, title: str, subtitle: str, year: str) -> str:
    """Return HTML for the main page title block."""
    return f"""
<div class="page-header">
  <div class="page-title-group">
    <div class="eyebrow">{eyebrow}</div>
    <h1 class="page-title">{title}</h1>
    <div class="page-sub">{subtitle}</div>
  </div>
  <div class="header-meta">
    <div class="year-display">{year}</div>
    <div>Analysår</div>
  </div>
</div>
"""


# ---------------------------------------------------------------------------
# Landing page (home) — HTML fragments; Swedish copy from callers
# ---------------------------------------------------------------------------

_NAV_ICONS: dict[str, str] = {
    "map": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6.5 9 4.5 15 6.5 21 4.5V19l-6 2-6-2-6 2V5.5l6-2zM9 4.5v15M15 6.5v15"/></svg>',
    "layers": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2 2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>',
    "search": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg>',
}


def render_landing_hero(
    eyebrow: str,
    headline: str,
    lead: str,
    cta: str,
) -> str:
    """Dark navy hero block for the home page."""
    cta_html = ""
    if cta.strip():
        cta_html = f'<p class="lp-hero-cta">{cta}</p>'
    return f"""
<div class="lp-hero">
  <div class="lp-hero-inner">
    <div class="lp-eyebrow">{eyebrow}</div>
    <h1 class="lp-headline">{headline}</h1>
    <p class="lp-hero-lead">{lead}</p>
    {cta_html}
  </div>
</div>
"""


def render_landing_stat_strip(stats: list[dict[str, str]]) -> str:
    """
    Four (or fewer) stat cells. Each dict: label, value, optional unit (key 'unit').
    """
    cells = []
    for s in stats:
        unit = s.get("unit", "")
        uhtml = f'<span class="lp-stat-unit">{unit}</span>' if unit else ""
        cells.append(
            f'<div class="lp-stat-cell"><div class="lp-stat-label">{s["label"]}</div>'
            f'<div class="lp-stat-value">{s["value"]}{uhtml}</div></div>'
        )
    return f'<div class="lp-stat-strip">{"".join(cells)}</div>'


def render_landing_section_title(text: str) -> str:
    """Eyebrow-style section title on light background."""
    return f'<div class="lp-section-title">{text}</div>'


def render_landing_what_is_block(title: str, p1: str, p2: str) -> str:
    """'Vad är KRI?' explanatory card."""
    return f"""
<div class="lp-section">
  {render_landing_section_title(title)}
  <div class="lp-card-light lp-explain-card">
    <p class="lp-body">{p1}</p>
    <p class="lp-body-secondary">{p2}</p>
  </div>
</div>
"""


def _landing_step_connector_svg() -> str:
    """Horizontal arrow between pipeline steps (decorative)."""
    return (
        '<div class="lp-step-connector" aria-hidden="true">'
        '<svg class="lp-step-arrow-svg" viewBox="0 0 44 20" xmlns="http://www.w3.org/2000/svg" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" focusable="false">'
        '<path d="M4 10h26"/><path d="M26 4l10 6-10 6"/>'
        "</svg></div>"
    )


def render_landing_steps(
    steps: list[tuple[str, str, str, str]],
) -> str:
    """
    Three numbered steps with arrow connectors (step → step).
    Each tuple: (number_label, title, body, icon_key data|normalize|classify).
    """
    icon_extra = {
        "data": '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3M5 17c0 1.7 3.1 3 7 3s7-1.3 7-3"/><path d="M5 5v14c0 1.7 3.1 3 7 3s7-1.3 7-3V5"/></svg>',
        "normalize": '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true"><path d="M4 19V5M4 19h16M8 17V7M12 17v-5M16 17v-9"/></svg>',
        "classify": '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true"><path d="M4 6h16v12H4z"/><path d="M8 10h8M8 14h5"/></svg>',
    }
    parts: list[str] = []
    for i, (num, title, body, kind) in enumerate(steps):
        ic = icon_extra.get(kind, icon_extra["data"])
        parts.append(
            f"""
<div class="lp-step">
  <div class="lp-step-num">{num}</div>
  <div class="lp-step-title">{ic}<span>{title}</span></div>
  <p class="lp-step-text">{body}</p>
</div>
"""
        )
        if i < len(steps) - 1:
            parts.append(_landing_step_connector_svg())
    return (
        '<div class="lp-section"><div class="lp-section-title">Så fungerar det i korthet</div>'
        f'<div class="lp-steps">{"".join(parts)}</div></div>'
    )


def render_landing_nav_card(
    tag: str,
    title: str,
    desc: str,
    icon: Literal["map", "layers", "search"],
) -> str:
    """Feature card (visual only; pair with st.page_link below for accessibility)."""
    svg = _NAV_ICONS.get(icon, _NAV_ICONS["map"])
    return f"""
<div class="lp-nav-card">
  <div class="lp-nav-card-head">
    <div class="lp-nav-icon">{svg}</div>
    <span class="lp-nav-tag">{tag}</span>
  </div>
  <div class="lp-nav-title">{title}</div>
  <p class="lp-nav-desc">{desc}</p>
</div>
"""


def render_landing_nav_section_title(text: str, in_panel: bool = False) -> str:
    """H2-style title above the three feature cards."""
    cls = "lp-nav-section-title"
    if in_panel:
        cls += " lp-nav-section-title-in-panel"
    return f'<div class="{cls}">{text}</div>'


def render_landing_credibility(
    pills: list[str],
    meta: str,
) -> str:
    """Sources + KRI version line."""
    pill_html = "".join(f'<span class="lp-cred-pill">{p}</span>' for p in pills)
    return f"""
<div class="lp-cred">
  <div class="lp-cred-pills">{pill_html}</div>
  <div class="lp-cred-meta">{meta}</div>
</div>
"""


# ---------------------------------------------------------------------------
# Risk colour helpers
# ---------------------------------------------------------------------------

_RISK_COLOR_MAP: dict[str, str] = {
    "Låg": COLORS["low_risk"],
    "Medel": COLORS["medium_risk"],
    "Hög": COLORS["high_risk"],
    "låg": COLORS["low_risk"],
    "medel": COLORS["medium_risk"],
    "hög": COLORS["high_risk"],
    "Lag": COLORS["low_risk"],
    "Hog": COLORS["high_risk"],
}


def get_risk_color(risk_class: str) -> str:
    """Return hex colour for a Swedish risk class label."""
    color = _RISK_COLOR_MAP.get(risk_class)
    if color is None:
        raise ValueError(
            f"Okänd riskklass: '{risk_class}'. Giltiga värden: 'Låg', 'Medel', 'Hög'."
        )
    return color


def get_risk_badge_html(risk_class: str) -> str:
    """Return a pill span for use with st.markdown(..., unsafe_allow_html=True)."""
    css_map = {"Låg": "lag", "Medel": "medel", "Hög": "hog"}
    cls = css_map.get(risk_class, "medel")
    return f'<span class="risk-pill {cls}">{risk_class}</span>'
