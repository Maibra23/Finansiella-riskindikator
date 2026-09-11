"""
Sweden municipality choropleth map using Folium + GeoJSON.

Each kommunpolygon is filled by KRI colour using the same diverging green->yellow->red
scale as the rest of the dashboard.  Requires folium and streamlit-folium.
"""

from __future__ import annotations

import json
from pathlib import Path

import branca.colormap as cm
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import folium_static

from src.config import DIVERGING_SCALE, MAP_TILES, MUNICIPALITIES

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GEOJSON_PATH = PROJECT_ROOT / "data" / "geo" / "kommuner.geojson"


@st.cache_data(show_spinner=False)
def _load_geojson() -> dict | None:
    if not GEOJSON_PATH.exists():
        return None
    try:
        with open(GEOJSON_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        st.error(f"Kunde inte läsa kartdata: {exc}")
        return None


def _build_colormap(scores: pd.Series) -> cm.LinearColormap:
    """Diverging colour scale anchored on the same quartiles that set risk_class.

    The composite KRI is a weighted mean of five z-scores, so its spread is well
    below one standard deviation (≈0.43 in 2024).  A fixed ±2.5 domain therefore
    compresses every municipality into the middle of the scale.  Anchoring the
    neutral colour at 0 and the green/red steps at the year's 25th/75th
    percentiles keeps the map readable *and* consistent with the risk classes
    shown in the tables.
    """
    q25 = float(scores.quantile(0.25))
    q75 = float(scores.quantile(0.75))
    extent = max(abs(float(scores.min())), abs(float(scores.max())), 1e-6)

    # Strictly increasing stops, one per colour in DIVERGING_SCALE (6 colours).
    stops = [-extent, q25, 0.0, q75, (q75 + extent) / 2, extent]
    if any(b <= a for a, b in zip(stops, stops[1:])):
        # Degenerate spread (e.g. a single municipality selected), fall back to
        # an evenly spaced symmetric domain rather than crashing branca.
        step = 2 * extent / (len(DIVERGING_SCALE) - 1)
        stops = [-extent + i * step for i in range(len(DIVERGING_SCALE))]
    return cm.LinearColormap(
        colors=list(DIVERGING_SCALE),
        index=stops,
        vmin=-extent,
        vmax=extent,
        caption="KRI Poäng  ·  Lägre = lägre risk",
    )


def build_choropleth_map(kri_df: pd.DataFrame, year: int) -> folium.Map | None:
    """Build the Folium map for a given year, or None when map data is missing."""
    sub = kri_df[kri_df["year"] == year].copy()
    sub["municipality_code"] = sub["municipality_code"].astype(str).str.zfill(4)

    # Build per-code lookup with pre-formatted display strings
    data_dict: dict[str, dict] = {}
    for _, row in sub.iterrows():
        code = str(row["municipality_code"]).zfill(4)
        kri = float(row["kri_score"])
        debt = float(row.get("debt_per_capita", 0))
        unemp = float(row.get("unemployment", 0))
        pop = float(row.get("population_growth", 0))
        tax = float(row.get("tax_base_relative", 0))
        rnk = int(row["rank"])
        risk = str(row["risk_class"])
        data_dict[code] = {
            "kri_score": kri,
            "rank": rnk,
            "risk_class": risk,
            # Pre-formatted strings for tooltip display
            "kri_fmt": f"{kri:+.2f}".replace(".", ","),
            "rank_fmt": f"{rnk} / 290",
            "debt_fmt": f"{int(debt):,}".replace(",", "\u202f") + " kr",
            "unemp_fmt": f"{unemp:.1f}".replace(".", ",") + " %",
            "pop_fmt": (("+" if pop >= 0 else "") + f"{pop:.1f}").replace(".", ",") + " %",
            "tax_fmt": f"{tax:.1f}".replace(".", ",") + " %",
        }

    # Deep-copy GeoJSON so cached original stays clean
    _raw = _load_geojson()
    if _raw is None:
        st.warning("Kartfilen saknas (data/geo/kommuner.geojson). Kartan kan inte visas.")
        return None
    geojson = json.loads(json.dumps(_raw))
    for feat in geojson["features"]:
        code = feat["properties"].get("id", "").zfill(4)
        d = data_dict.get(code, {})
        feat["properties"]["KRI Poäng"] = d.get("kri_fmt", "Saknas")
        feat["properties"]["Rang"] = d.get("rank_fmt", "Saknas")
        feat["properties"]["Riskklass"] = d.get("risk_class", "Saknas")
        feat["properties"]["Skuld/capita"] = d.get("debt_fmt", "Saknas")
        feat["properties"]["Arbetslöshet"] = d.get("unemp_fmt", "Saknas")
        feat["properties"]["Befolkningstillväxt"] = d.get("pop_fmt", "Saknas")
        feat["properties"]["Skattekraft"] = d.get("tax_fmt", "Saknas")
        # Numeric KRI for colour lookup
        feat["properties"]["_kri"] = d.get("kri_score", 0.0)
        # Resolve name from MUNICIPALITIES dict as fallback
        feat["properties"]["Kommun"] = MUNICIPALITIES.get(
            code, feat["properties"].get("kom_namn", code)
        )

    colormap = _build_colormap(sub["kri_score"].astype(float))

    m = folium.Map(
        location=[63.0, 17.5],
        zoom_start=5,
        tiles=None,
        prefer_canvas=True,
        zoom_control=True,
        scrollWheelZoom=False,
    )
    m.get_root().html.add_child(
        folium.Element(
            "<style>.folium-map .leaflet-container "
            f"{{ background: {MAP_TILES['background']}; }}</style>"
        )
    )
    folium.TileLayer(
        tiles=MAP_TILES["url"],
        attr=MAP_TILES["attribution"],
        name=MAP_TILES["name"],
        max_zoom=MAP_TILES["max_zoom"],
        control=False,
    ).add_to(m)

    def _style(feature: dict) -> dict:
        kri_val = feature["properties"].get("_kri", 0.0)
        return {
            "fillColor": colormap(kri_val),
            "color": "#CCCCCC",
            "weight": 0.5,
            "fillOpacity": 0.82,
        }

    def _highlight(feature: dict) -> dict:
        return {
            "color": "#1A1A2E",
            "weight": 2.0,
            "fillOpacity": 0.95,
        }

    tooltip_css = (
        "font-family: 'Source Sans Pro', sans-serif;"
        "font-size: 13px;"
        "line-height: 1.5;"
        "background: #ffffff;"
        "border: 1px solid #E5E7EB;"
        "border-radius: 6px;"
        "padding: 12px 14px;"
        "box-shadow: 0 4px 16px rgba(0,0,0,0.10);"
        "color: #1A1A2E;"
    )

    folium.GeoJson(
        geojson,
        style_function=_style,
        highlight_function=_highlight,
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "Kommun", "Riskklass", "KRI Poäng", "Rang",
                "Skuld/capita", "Arbetslöshet",
                "Befolkningstillväxt", "Skattekraft",
            ],
            aliases=[
                "<b>Kommun</b>", "<b>Riskklass</b>", "KRI Poäng", "Rang",
                "Skuld per capita", "Arbetslöshet",
                "Befolkningstillväxt (5 år)", "Skattekraft (% rikssnitt)",
            ],
            sticky=True,
            style=tooltip_css,
        ),
    ).add_to(m)

    colormap.add_to(m)

    return m


def render_choropleth(kri_df: pd.DataFrame, year: int, height: int = 480) -> None:
    """Render a full polygon choropleth of Sweden's 290 municipalities."""
    m = build_choropleth_map(kri_df, year)
    if m is None:
        return
    folium_static(m, width=None, height=height)
