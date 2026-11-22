"""
Central design system for the KRI Dashboard (Streamlit + ECharts).

All user-facing strings passed into render helpers must be in Swedish.
All code identifiers, comments, and docstrings are in English.
"""

from __future__ import annotations

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
            page_icon=":bar_chart:",
            layout="wide",
            # Integer = sidebar width in px with "auto" state: expanded on desktop,
            # collapsed on phones so it does not cover the page.
            initial_sidebar_state=260,
            menu_items={
                "Get Help": None,
                "Report a bug": None,
                "About": "**KRI Kontrollpanel**. Kommunal finansiell riskindikator.\n\nKälla: SCB, Arbetsförmedlingen",
            },
        )
    except StreamlitAPIException:
        # Already set on first page in this session (e.g. home -> multipage navigation).
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
    <style>
    /* Shared rhythm: main + sidebar use the same horizontal gutter so text keylines align. */
    :root {{
        --kri-pad-x: 1.5rem;
        --kri-pad-y: 2rem;
        --kri-label-upper: 11px;
        --kri-label-track: 1.5px;
        /* Matches .brand-mark::before (4px) + gap (10px) so hero eyebrow lines up with sidebar mark */
        --kri-brand-bar-offset: 14px;
        /* Minimal top inset inside .lp-hero so gold eyebrow aligns with sidebar (avoid stacking on --kri-pad-y) */
        --kri-hero-pad-top: 0.35rem;
        /* Streamlit bundles Source Sans 3; no external font download. */
        --kri-font: "Source Sans 3", "Source Sans Pro", -apple-system, "Segoe UI", sans-serif;
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    /* Hide chrome but keep sidebar expand control usable (descendant may stay visible). */
    header[data-testid="stHeader"] {{
        visibility: hidden;
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        overflow: visible;
    }}
    /* Sidebar toggle. Streamlit 1.67 renders the "open sidebar" button inside the hidden
       header, so it is made visible again here. Version-sensitive test-id. */
    [data-testid="stExpandSidebarButton"] {{
        visibility: visible !important;
        position: fixed !important;
        top: 0.75rem !important;
        left: 0.75rem !important;
        z-index: 1002 !important;
        background: {p} !important;
        color: #FFFFFF !important;
        border-radius: 4px;
    }}
    [data-testid="stExpandSidebarButton"] * {{
        color: #FFFFFF !important;
    }}

    html, body {{
        font-family: var(--kri-font) !important;
    }}
    /* Keyboard focus must always be visible (WCAG 2.4.7). */
    :focus-visible {{
        outline: 2px solid {COLORS["secondary"]} !important;
        outline-offset: 2px !important;
    }}

    /* Main content only, never force dark body text on [class*="css"] or it paints the sidebar unreadable */
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

    /* Streamlit sections: avoid extra top offset so main/sidebar align with shared --kri-pad-y */
    [data-testid="stMain"],
    [data-testid="stSidebar"] {{
        padding-top: 0 !important;
        margin-top: 0 !important;
    }}

    [data-testid="stSidebar"] {{
        background-color: {p};
        color: #E8ECF4 !important;
        border-right: 1px solid {border};
    }}

    /* Sidebar header only holds the collapse button (auto-nav is off in config.toml).
       Take it out of the flow so the brand block keeps its position. */
    [data-testid="stSidebarHeader"] {{
        position: absolute !important;
        top: 0.5rem;
        right: 0.5rem;
        height: auto !important;
        padding: 0 !important;
        z-index: 2;
    }}
    [data-testid="stSidebarCollapseButton"] button {{
        color: rgba(255, 255, 255, 0.75) !important;
    }}

    /* Streamlit puts sidebar widgets in stSidebarContent (often no .block-container); pad this node so gutters match main */
    [data-testid="stSidebarContent"] {{
        color: #E8ECF4 !important;
        box-sizing: border-box !important;
        padding-top: var(--kri-pad-y) !important;
        padding-bottom: var(--kri-pad-y) !important;
        padding-left: var(--kri-pad-x) !important;
        padding-right: var(--kri-pad-x) !important;
    }}

    /* Nested .block-container (some Streamlit versions): strip horizontal pad only so we do not double --kri-pad-x */
    [data-testid="stSidebarContent"] .block-container {{
        padding-left: 0 !important;
        padding-right: 0 !important;
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

    /* Sidlänkar: Streamlit sätter mörk text på mörk bakgrund, tvinga ljus text + spann. */
    [data-testid="stSidebarContent"] a[href] {{
        text-decoration: none !important;
        color: rgba(255, 255, 255, 0.92) !important;
        font-size: 13.5px !important;
        line-height: 1.45 !important;
        font-family: var(--kri-font) !important;
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

    /* Borttagen: bred .stApp > ... > div {{ padding-top }} gav vertikal glidning mellan huvudyta och sidopanel */

    [data-testid="stVerticalBlock"] > div {{
        gap: 0.5rem;
    }}

    /* First stack in main: Streamlit sometimes adds top margin on the wrapper */
    [data-testid="stMain"] .block-container > [data-testid="stVerticalBlock"]:first-child {{
        margin-top: 0 !important;
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


    /* Optional tone overrides the colour so the arrow can show the direction of change

    .mono, .num {{ font-variant-numeric: tabular-nums; }}

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
        color: {COLORS["accent_text"]};
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
        font-family: var(--kri-font);
        font-variant-numeric: tabular-nums;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }}
    .year-display {{
        font-size: 32px;
        color: {p};
        font-family: var(--kri-font);
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
        margin-top: 6px;
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
        font-family: var(--kri-font);
        font-variant-numeric: tabular-nums;
        font-size: 12.5px;
    }}
    .kri-table tbody tr:hover {{ background: {hover}; }}
    .rank-cell {{
        font-family: var(--kri-font);
        font-variant-numeric: tabular-nums;
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
    .risk-pill.medel {{ background: rgba(212,160,60,0.12); color: {COLORS["medium_risk_text"]}; border: 1px solid rgba(212,160,60,0.3); }}
    .risk-pill.lag {{ background: rgba(46,125,91,0.12); color: {low}; border: 1px solid rgba(46,125,91,0.3); }}
    /* Gränsfall: markör för viktkänslighet, inte en fjärde riskklass. Medvetet
       färglös: gult betyder redan "Medel" i panelen, så en gul markör på en
       Hög-kommun skulle läsas som en nedgradering. Fylld ram = fastställd
       klassning, streckad ram = klassningen är preliminär. */
    .risk-pill.granfall {{
        background: transparent;
        color: {text_ter};
        border: 1px dashed rgba(156,163,175,0.55);
        text-transform: none;
        letter-spacing: 0.2px;
        font-weight: 500;
    }}

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
        font-family: var(--kri-font);
        font-variant-numeric: tabular-nums;
        font-size: 10.5px;
        background: {bg};
        padding: 2px 6px;
        border-radius: 2px;
        color: {text_sec};
    }}

    /* ── Sidopanel: år-chips + riskklass-piller --------------- */
    /* Bred regel, träffar alla knappar i sidopanelen oberoende av stPills-hierarki.
       button * fångar text i p/span/div oavsett vad Streamlit renderar inuti knappen. */
    [data-testid="stSidebar"] button {{
        background-color: rgba(255,255,255,0.10) !important;
        border: 1px solid rgba(255,255,255,0.25) !important;
        border-radius: 4px !important;
        padding: 4px 9px !important;
        font-family: var(--kri-font) !important;
        font-variant-numeric: tabular-nums;
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
    /* Vald chip: guld bakgrund, mörk marin text */
    [data-testid="stSidebar"] button[aria-pressed="true"] {{
        background-color: {accent} !important;
        border-color: {accent} !important;
        font-weight: 600 !important;
    }}
    [data-testid="stSidebar"] button[aria-pressed="true"],
    [data-testid="stSidebar"] button[aria-pressed="true"] * {{
        color: {p} !important;
    }}

    .sidebar-control {{
        margin-top: 24px;
        padding-top: 20px;
        border-top: 1px solid rgba(255,255,255,0.08);
    }}

    /* ── Landing page (.lp-*): scoped to home; tokens from COLORS --------- */
    .lp-hero {{
        background: {p};
        border-radius: 4px;
        padding: var(--kri-hero-pad-top) var(--kri-pad-x) 20px;
        margin-bottom: 0;
        margin-top: 0 !important;
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
    /* Option A: align first glyph with .brand-mark (bar + gap) when gutters match */
    .lp-hero .lp-eyebrow {{
        padding-left: var(--kri-brand-bar-offset);
        box-sizing: border-box;
    }}
    /* Main sets color on stMain, hero must override for h1 + text */
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
        font-family: var(--kri-font);
        font-variant-numeric: tabular-nums;
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
        color: {COLORS["accent_text"]};
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
        font-family: var(--kri-font);
        font-variant-numeric: tabular-nums;
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
    .lp-step-num {{
        font-family: var(--kri-font);
        font-variant-numeric: tabular-nums;
        font-size: 11px;
        color: {COLORS["accent_text"]};
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
    }}
    .lp-nav-card-head {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 10px;
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
        .lp-hero {{ padding: var(--kri-hero-pad-top) 16px 16px; }}
    }}
    /* ── Modernized components (app/ui) ------------------------------- */
    .card-header--plain {{
        border-bottom: none;
        margin-bottom: 6px;
        padding-bottom: 0;
    }}
    .kri-note {{
        font-size: 13px;
        color: {text_sec};
        margin-top: 4px;
    }}
    .kommun-summary {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 10px;
        font-size: 14.5px;
        color: {text_sec};
        padding: 8px 0;
        font-variant-numeric: tabular-nums;
    }}
    .kommun-summary strong {{ color: {text_pri}; font-weight: 600; }}
    .kommun-summary .sep {{ color: {COLORS["border_strong"]}; }}
    .kommun-summary .risk-pill {{ font-size: 12px; padding: 3px 10px; }}
    /* Numbers in native metrics line up like a statement. */
    [data-testid="stMetricValue"], [data-testid="stMetricDelta"] {{
        font-variant-numeric: tabular-nums;
    }}
    [data-testid="stMetricLabel"] p {{
        font-size: 12px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: {text_sec} !important;
    }}
    /* Landing nav card sits inside a bordered container: no second frame. */
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] .lp-nav-card {{
        border: none;
        padding: 0 0 6px 0;
        min-height: 0;
        background: transparent;
    }}
    /* Startsida entry points: first link primary (navy), second secondary (outlined). */
    .st-key-lp_cta a[data-testid="stPageLink-NavLink"] {{
        border: 1px solid {p};
        border-radius: 6px;
        padding: 8px 16px;
        background: {card};
    }}
    .st-key-lp_cta > [data-testid="stElementContainer"]:first-child a[data-testid="stPageLink-NavLink"] {{
        background: {p};
    }}
    .st-key-lp_cta > [data-testid="stElementContainer"]:first-child a[data-testid="stPageLink-NavLink"] * {{
        color: #FFFFFF !important;
    }}
    .st-key-lp_cta a[data-testid="stPageLink-NavLink"]:hover {{
        background: {COLORS["primary_hover"]};
    }}
    .st-key-lp_cta a[data-testid="stPageLink-NavLink"]:hover * {{
        color: #FFFFFF !important;
    }}
    /* Sidebar section labels: spacing between nav groups. */
    [data-testid="stSidebar"] .nav-section {{
        margin-top: 14px;
        margin-bottom: 4px;
    }}
    @media (max-width: 640px) {{
        .page-header {{ flex-direction: column; align-items: flex-start; gap: 8px; }}
        .header-meta {{ text-align: left; }}
        .page-title {{ font-size: 24px; overflow-wrap: break-word; hyphens: auto; }}
    }}

    @media (prefers-reduced-motion: reduce) {{
        .lp-step, .lp-nav-card {{ transition: none !important; }}
        .lp-step-arrow-svg {{ transition: none !important; }}
    }}
    </style>
    """

    st.markdown(css, unsafe_allow_html=True)


# Charts render inside iframes, so they use a font stack rather than the CSS variable.
ECHARTS_FONT = "'Source Sans 3', 'Source Sans Pro', -apple-system, 'Segoe UI', sans-serif"


def get_tooltip_style() -> dict[str, Any]:
    """Return consistent ECharts tooltip styling (light card, dark text)."""
    return {
        "trigger": "axis",
        "backgroundColor": COLORS["card_bg"],
        "borderColor": COLORS["border"],
        "borderWidth": 1,
        "padding": [10, 14],
        "textStyle": {
            "color": COLORS["text_primary"],
            "fontFamily": ECHARTS_FONT,
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
    out: dict[str, Any] = {
        "axisLine": {"lineStyle": {"color": COLORS["grid"]}},
        "axisTick": {"show": False},
        "axisLabel": {
            "color": COLORS["text_secondary"],
            "fontSize": 11,
            "fontFamily": ECHARTS_FONT,
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


def get_echarts_base_options() -> dict[str, Any]:
    """Shared ECharts JSON base; merge chart-specific options on top."""
    base = {
        "backgroundColor": COLORS["card_bg"],
        "textStyle": {"fontFamily": ECHARTS_FONT, "color": COLORS["text_primary"]},
        # Lets ECharts generate a text description of each chart for screen readers.
        "aria": {"enabled": True},
        "grid": {
            "left": 56,
            "right": 30,
            "top": 50,
            "bottom": 70,
            "containLabel": True,
        },
        "tooltip": get_tooltip_style(),
        "animation": True,
        "animationDuration": 250,
    }
    return base


# ---------------------------------------------------------------------------
# Landing page (home): HTML fragments; Swedish copy from callers
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
    Three numbered steps with arrow connectors (step -> step).
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
    title: str,
    desc: str,
    icon: Literal["map", "layers", "search"],
) -> str:
    """Feature card body; the caller adds an st.page_link so the card is a real link."""
    svg = _NAV_ICONS.get(icon, _NAV_ICONS["map"])
    return f"""
<div class="lp-nav-card">
  <div class="lp-nav-card-head">
    <div class="lp-nav-icon">{svg}</div>
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


