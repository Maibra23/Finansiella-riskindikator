"""
Landing page HTML/SVG fragments: index weights and flow diagram.

All user-facing strings are Swedish. Code identifiers in English.
"""

from __future__ import annotations

from src.config import COLORS, SWEDISH_LABELS, WEIGHTS

# Order matches WEIGHTS keys for stable display
_WEIGHT_KEYS: list[tuple[str, str]] = [
    ("debt_per_capita", "debt"),
    ("unemployment", "unemployment"),
    ("dependency_ratio", "dependency_ratio"),
    ("population_growth", "population_growth"),
    ("tax_base", "tax_base"),
]


def render_index_weights_html() -> str:
    """Horizontal weight bars for the five KRI components."""
    rows = []
    for label_key, wkey in _WEIGHT_KEYS:
        pct = int(round(WEIGHTS[wkey] * 100))
        name = SWEDISH_LABELS[label_key]
        rows.append(
            f'<div class="lp-weight-row">'
            f'<span class="lp-weight-name">{name}</span>'
            f'<div class="lp-weight-bar-wrap">'
            f'<div class="lp-weight-bar" style="width:{pct}%;"></div></div>'
            f'<span class="lp-weight-pct">{pct} %</span></div>'
        )
    return f'<div class="lp-weight-list">{"".join(rows)}</div>'


def render_index_flow_svg() -> str:
    """
    Compact SVG: inputs -> KRI -> riskklass. Titles share one baseline, centered over each column.
    """
    p = COLORS["primary"]
    acc = COLORS["accent"]
    low = COLORS["low_risk"]
    med = COLORS["medium_risk"]
    high = COLORS["high_risk"]
    g = COLORS["grid"]
    ts = COLORS["text_secondary"]

    # Column centers for title alignment (text-anchor middle)
    cx1, cx2, cx3 = 61.0, 163.0, 331.0

    return f"""
<svg class="lp-flow-svg" viewBox="0 0 460 72" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
    <marker id="lp-arr" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 z" fill="{acc}"/>
    </marker>
  </defs>
  <!-- One title row, aligned above each column -->
  <text x="{cx1}" y="10" text-anchor="middle" fill="{p}" font-family="Source Sans Pro, sans-serif" font-size="9" font-weight="700">Fem indikatorer</text>
  <text x="{cx2}" y="10" text-anchor="middle" fill="{p}" font-family="Source Sans Pro, sans-serif" font-size="9" font-weight="700">Aggregering</text>
  <text x="{cx3}" y="10" text-anchor="middle" fill="{p}" font-family="Source Sans Pro, sans-serif" font-size="9" font-weight="700">Riskklass</text>
  <!-- Boxes share top y -->
  <rect x="2" y="14" width="118" height="40" rx="2" fill="#FFFFFF" stroke="{g}" stroke-width="1"/>
  <text x="{cx1}" y="36" text-anchor="middle" fill="{p}" font-family="Source Sans Pro, sans-serif" font-size="8.5" font-weight="600">Viktad z-poängsumma</text>
  <text x="{cx1}" y="48" text-anchor="middle" fill="{ts}" font-family="Source Sans Pro, sans-serif" font-size="7.5">(se staplar ovan)</text>
  <line x1="122" y1="34" x2="132" y2="34" stroke="{acc}" stroke-width="1.5" marker-end="url(#lp-arr)"/>
  <rect x="136" y="18" width="54" height="32" rx="3" fill="{p}" stroke="{acc}" stroke-width="1"/>
  <text x="{cx2}" y="34" text-anchor="middle" fill="#FFFFFF" font-family="Source Sans Pro, sans-serif" font-size="13" font-weight="700">KRI</text>
  <text x="{cx2}" y="44" text-anchor="middle" fill="rgba(255,255,255,0.8)" font-family="IBM Plex Mono, monospace" font-size="7">index</text>
  <line x1="192" y1="34" x2="202" y2="34" stroke="{acc}" stroke-width="1.5" marker-end="url(#lp-arr)"/>
  <rect x="206" y="14" width="250" height="40" rx="2" fill="#FFFFFF" stroke="{g}" stroke-width="1"/>
  <rect x="214" y="22" width="68" height="22" rx="2" fill="rgba(46,125,91,0.12)" stroke="{low}" stroke-width="1"/>
  <text x="248" y="36" text-anchor="middle" fill="{low}" font-family="Source Sans Pro, sans-serif" font-size="9" font-weight="700">Låg</text>
  <rect x="288" y="22" width="68" height="22" rx="2" fill="rgba(212,160,60,0.12)" stroke="{med}" stroke-width="1"/>
  <text x="322" y="36" text-anchor="middle" fill="#8B6914" font-family="Source Sans Pro, sans-serif" font-size="9" font-weight="700">Medel</text>
  <rect x="362" y="22" width="68" height="22" rx="2" fill="rgba(185,74,72,0.12)" stroke="{high}" stroke-width="1"/>
  <text x="396" y="36" text-anchor="middle" fill="{high}" font-family="Source Sans Pro, sans-serif" font-size="9" font-weight="700">Hög</text>
  <text x="{cx3}" y="62" text-anchor="middle" fill="{ts}" font-family="Source Sans Pro, sans-serif" font-size="7.5">Kvartiler per år · N = 290</text>
</svg>
"""


def render_index_visual_block() -> str:
    """Section title + weights + flow diagram for the landing page."""
    return f"""
<div class="lp-section">
  <div class="lp-section-title">Indexet i överblick</div>
  <div class="lp-card-light lp-visual">
    {render_index_weights_html()}
    <div class="lp-flow-svg-wrap">{render_index_flow_svg()}</div>
  </div>
</div>
"""
