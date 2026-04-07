"""
Reusable Apache ECharts option builders for the KRI dashboard.

All chart titles, axes, legends, and tooltip text are in Swedish.
Function names and comments are in English.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from app.styles.theme import (
    get_axis_style,
    get_echarts_base_options,
    get_tooltip_style,
)
from src.config import COLORS, DIVERGING_SCALE, MUNICIPALITIES

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GEOJSON_PATH = PROJECT_ROOT / "data" / "geo" / "kommuner.geojson"
CENTROIDS_CSV = PROJECT_ROOT / "data" / "geo" / "kommun_centroids.csv"

# Module-level map: municipality_code -> (lat, lon); filled by _load_municipality_coords()
MUNICIPALITY_COORDS: dict[str, tuple[float, float]] = {}


@lru_cache(maxsize=1)
def _load_municipality_coords() -> dict[str, tuple[float, float]]:
    """Load (lat, lon) per municipality from CSV or GeoJSON."""
    coords: dict[str, tuple[float, float]] = {}

    if CENTROIDS_CSV.exists():
        df = pd.read_csv(CENTROIDS_CSV)
        if {"municipality_code", "lat", "lon"}.issubset(df.columns):
            for _, row in df.iterrows():
                code = str(row["municipality_code"]).zfill(4)
                coords[code] = (float(row["lat"]), float(row["lon"]))
            return coords

    if GEOJSON_PATH.exists():
        with open(GEOJSON_PATH, encoding="utf-8") as fh:
            gj = json.load(fh)
        for feat in gj.get("features", []):
            props = feat.get("properties") or {}
            code = str(props.get("id", "")).zfill(4)
            if not code or code == "0000":
                continue
            gp = props.get("geo_point_2d")
            if gp and len(gp) >= 2:
                lat, lon = float(gp[0]), float(gp[1])
                coords[code] = (lat, lon)
        if coords:
            return coords

    # Fallback: no geometry — caller should still run; map may be empty
    return {}


def _ensure_coords() -> dict[str, tuple[float, float]]:
    global MUNICIPALITY_COORDS
    if not MUNICIPALITY_COORDS:
        MUNICIPALITY_COORDS = _load_municipality_coords()
    return MUNICIPALITY_COORDS


def _bin_color(bin_center: float) -> str:
    """Colour bar by risk zone using normal quartile thresholds on the index scale."""
    if bin_center < -0.6745:
        return COLORS["low_risk"]
    if bin_center > 0.6745:
        return COLORS["high_risk"]
    return COLORS["medium_risk"]


def build_distribution_histogram(kri_scores: list[float], median: float) -> dict[str, Any]:
    """Vertical histogram (24 bins on [-2.5, 2.5]) with median mark line."""
    n_bins = 24
    lo, hi = -2.5, 2.5
    step = (hi - lo) / n_bins
    edges = [lo + i * step for i in range(n_bins + 1)]
    counts = [0] * n_bins
    for x in kri_scores:
        if x < lo:
            i = 0
        elif x >= hi:
            i = n_bins - 1
        else:
            i = min(int((x - lo) / step), n_bins - 1)
        counts[i] += 1

    categories = [f"{edges[i]:.1f}" for i in range(n_bins)]
    bar_data: list[dict[str, Any]] = []
    for i in range(n_bins):
        center = edges[i] + step / 2
        bar_data.append(
            {
                "value": counts[i],
                "itemStyle": {
                    "color": _bin_color(center),
                    "borderRadius": [2, 2, 0, 0],
                },
            }
        )

    median_idx = 0
    if median <= lo:
        median_idx = 0
    elif median >= hi:
        median_idx = n_bins - 1
    else:
        median_idx = min(int((median - lo) / step), n_bins - 1)

    idx_low = max(0, int((-0.6745 - lo) / step))
    idx_high = min(n_bins, int((0.6745 - lo) / step) + 1)

    base = copy.deepcopy(get_echarts_base_options())
    base["tooltip"] = {
        **get_tooltip_style(),
        "trigger": "axis",
        "formatter": (
            "function(params) {"
            "  if (!params || !params.length) return '';"
            "  var p = params[0];"
            "  var lo = p.axisValue !== undefined ? parseFloat(p.axisValue).toFixed(1).replace('.', ',') : '';"
            "  var hi = (parseFloat(p.axisValue) + " + str(round(step, 4)) + ").toFixed(1).replace('.', ',');"
            "  return '<div style=\"font-weight:600;margin-bottom:4px\">KRI-intervall: ' + lo + ' till ' + hi + '</div>'"
            "       + 'Antal kommuner: <b>' + p.value + '</b>';"
            "}"
        ),
    }
    base["xAxis"] = {
        "type": "category",
        "data": categories,
        "name": "KRI Poäng",
        "nameLocation": "middle",
        "nameGap": 36,
        "nameTextStyle": {
            "color": COLORS["text_secondary"],
            "fontSize": 11,
            "fontFamily": "Source Sans Pro",
            "fontWeight": 600,
        },
        **get_axis_style("category"),
    }
    base["xAxis"]["axisLabel"] = {
        **base["xAxis"].get("axisLabel", {}),
        "interval": 3,
    }
    base["yAxis"] = {
        "type": "value",
        "name": "Antal kommuner",
        "nameTextStyle": {
            "color": COLORS["text_secondary"],
            "fontSize": 11,
            "fontFamily": "Source Sans Pro",
            "fontWeight": 600,
            "padding": [0, 0, 10, 0],
        },
        **get_axis_style("value"),
    }
    base["yAxis"]["axisLine"] = {"show": False}
    base["series"] = [
        {
            "type": "bar",
            "data": bar_data,
            "barWidth": "85%",
            "markLine": {
                "symbol": "none",
                "label": {
                    "formatter": "Median",
                    "color": COLORS["primary"],
                    "fontSize": 10,
                    "fontWeight": 600,
                    "fontFamily": "Source Sans Pro",
                    "position": "insideEndTop",
                },
                "lineStyle": {"color": COLORS["primary"], "width": 1.5, "type": "dashed"},
                "data": [{"xAxis": median_idx}],
            },
            "markArea": {
                "silent": True,
                "itemStyle": {"opacity": 0.04},
                "data": [
                    [
                        {"xAxis": 0, "itemStyle": {"color": COLORS["low_risk"]}},
                        {"xAxis": idx_low},
                    ],
                    [
                        {"xAxis": idx_low, "itemStyle": {"color": COLORS["medium_risk"]}},
                        {"xAxis": idx_high},
                    ],
                    [
                        {"xAxis": idx_high, "itemStyle": {"color": COLORS["high_risk"]}},
                        {"xAxis": n_bins},
                    ],
                ],
            },
        }
    ]
    return base


def build_horizontal_contribution_bar(contributions: dict[str, float]) -> dict[str, Any]:
    """Horizontal bars for one municipality's KRI contributions (Swedish labels)."""
    palette = [
        COLORS["primary"],
        COLORS["secondary"],
        COLORS["accent"],
        COLORS["primary_light"],
        COLORS["low_risk"],
    ]
    sorted_items = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
    cats = [k for k, _ in sorted_items]
    vals = [v for _, v in sorted_items]

    series_data: list[dict[str, Any]] = []
    for i, v in enumerate(vals):
        series_data.append(
            {
                "value": v,
                "itemStyle": {
                    "color": palette[i % len(palette)],
                    "borderRadius": [0, 2, 2, 0],
                },
            }
        )

    base = copy.deepcopy(get_echarts_base_options())
    base["grid"] = {"left": 120, "right": 60, "top": 40, "bottom": 40, "containLabel": True}
    base["tooltip"] = {
        **get_tooltip_style(),
        "trigger": "axis",
        "axisPointer": {"type": "shadow"},
    }
    base["xAxis"] = {**get_axis_style("value"), "type": "value", "name": "Bidrag"}
    base["yAxis"] = {
        **get_axis_style("category"),
        "type": "category",
        "data": cats,
        "inverse": True,
    }
    base["yAxis"]["splitLine"] = {"show": False}
    base["series"] = [{"type": "bar", "data": series_data, "barWidth": "60%"}]
    return base


def build_radar(
    municipality_values: list[float],
    national_avg: list[float],
    indicators: list[str],
) -> dict[str, Any]:
    """Radar chart: selected municipality vs Rikssnitt."""
    ind = [{"name": n, "max": 2.5, "min": -2.5} for n in indicators]
    base = copy.deepcopy(get_echarts_base_options())
    base.pop("grid", None)
    base["tooltip"] = {**get_tooltip_style(), "trigger": "item"}
    base["radar"] = {
        "indicator": ind,
        "radius": "65%",
        "splitLine": {"lineStyle": {"color": COLORS["grid"]}},
        "splitArea": {"show": False},
        "axisName": {
            "color": COLORS["text_secondary"],
            "fontSize": 10,
            "fontFamily": "Source Sans Pro",
        },
    }
    base["series"] = [
        {
            "type": "radar",
            "symbol": "none",
            "data": [
                {
                    "value": municipality_values,
                    "name": "Vald kommun",
                    "lineStyle": {"color": COLORS["primary"], "width": 2},
                    "areaStyle": {"color": COLORS["primary"], "opacity": 0.25},
                },
                {
                    "value": national_avg,
                    "name": "Rikssnitt",
                    "lineStyle": {"color": COLORS["accent"], "width": 2, "type": "dashed"},
                    "areaStyle": {"opacity": 0},
                },
            ],
        }
    ]
    base["legend"] = {
        "data": ["Vald kommun", "Rikssnitt"],
        "top": 10,
        "right": 20,
        "textStyle": {"fontFamily": "Source Sans Pro", "color": COLORS["text_primary"]},
    }
    return base


def build_line_trend(years: list[int], series_dict: dict[str, list[float]]) -> dict[str, Any]:
    """KRI trend lines with optional risk zone bands."""
    year_str = [str(y) for y in years]
    base = copy.deepcopy(get_echarts_base_options())
    base["tooltip"] = {**get_tooltip_style(), "trigger": "axis"}
    base["legend"] = {
        "data": list(series_dict.keys()),
        "top": 10,
        "right": 20,
        "textStyle": {"fontFamily": "Source Sans Pro", "color": COLORS["text_primary"]},
    }
    base["xAxis"] = {
        **get_axis_style("category"),
        "type": "category",
        "data": year_str,
        "name": "År",
        "nameTextStyle": {"color": COLORS["text_secondary"], "fontSize": 11},
    }
    base["yAxis"] = {
        **get_axis_style("value"),
        "type": "value",
        "name": "KRI Poäng",
        "nameTextStyle": {"color": COLORS["text_secondary"], "fontSize": 11},
    }
    series_list: list[dict[str, Any]] = []
    for name, vals in series_dict.items():
        is_ref = name == "Rikssnitt"
        series_list.append(
            {
                "name": name,
                "type": "line",
                "data": vals,
                "smooth": True,
                "lineStyle": {
                    "width": 2.5,
                    "color": COLORS["text_tertiary"] if is_ref else COLORS["primary"],
                    "type": "dashed" if is_ref else "solid",
                },
                "itemStyle": {"color": COLORS["text_tertiary"] if is_ref else COLORS["primary"]},
                "showSymbol": False,
            }
        )
    base["series"] = series_list
    # Risk zone markArea (approximate KRI scale)
    if series_list:
        base["series"][0]["markArea"] = {
            "silent": True,
            "itemStyle": {"opacity": 0.04},
            "data": [
                [{"yAxis": -3, "itemStyle": {"color": COLORS["low_risk"]}}, {"yAxis": -0.6745}],
                [{"yAxis": -0.6745, "itemStyle": {"color": COLORS["medium_risk"]}}, {"yAxis": 0.6745}],
                [{"yAxis": 0.6745, "itemStyle": {"color": COLORS["high_risk"]}}, {"yAxis": 3}],
            ],
        }
    return base


def build_grouped_bars_comparison(
    municipalities: list[str],
    components: dict[str, list[float]],
) -> dict[str, Any]:
    """Grouped bars: municipalities x risk components."""
    palette = [
        COLORS["primary"],
        COLORS["secondary"],
        COLORS["accent"],
        COLORS["low_risk"],
        COLORS["medium_risk"],
    ]
    base = copy.deepcopy(get_echarts_base_options())
    base["tooltip"] = {**get_tooltip_style(), "trigger": "axis"}
    base["legend"] = {
        "data": list(components.keys()),
        "top": 10,
        "textStyle": {"fontFamily": "Source Sans Pro", "color": COLORS["text_primary"]},
    }
    base["xAxis"] = {
        **get_axis_style("category"),
        "type": "category",
        "data": municipalities,
    }
    base["yAxis"] = {
        **get_axis_style("value"),
        "type": "value",
        "name": "KRI Poäng",
    }
    series: list[dict[str, Any]] = []
    for i, (comp_name, vals) in enumerate(components.items()):
        series.append(
            {
                "name": comp_name,
                "type": "bar",
                "data": vals,
                "itemStyle": {"color": palette[i % len(palette)]},
            }
        )
    base["series"] = series
    return base


def _scale_debt_to_size(debt: float, dmin: float, dmax: float) -> float:
    """Map debt_per_capita to [6, 18] when population is unavailable."""
    if dmax <= dmin:
        return 12.0
    t = (debt - dmin) / (dmax - dmin)
    return 6 + t * 12


def build_sweden_geo_scatter(kri_df: pd.DataFrame, year: int) -> dict[str, Any]:
    """Scatter plot of municipality centroids (lon/lat); colour by KRI (diverging scale).

    Uses Cartesian axes (not geo.map) so no ECharts map registration is required —
    ``geo.map: \"world\"`` needs a registered GeoJSON, which caused runtime errors
    in streamlit-echarts when the map was missing.
    """
    coords = _ensure_coords()
    sub = kri_df[kri_df["year"] == year].copy()
    if sub.empty:
        sub = kri_df.copy()

    debts = sub["debt_per_capita"].astype(float)
    dmin, dmax = float(debts.min()), float(debts.max())

    enriched: list[dict[str, Any]] = []
    for _, row in sub.iterrows():
        code = str(row["municipality_code"]).zfill(4)
        lat_lon = coords.get(code)
        if lat_lon is None:
            continue
        lat, lon = lat_lon
        kri = float(row["kri_score"])
        rnk = int(row["rank"])
        risk = str(row["risk_class"])
        name = MUNICIPALITIES.get(code, str(row.get("municipality_name", code)))
        debt = float(row["debt_per_capita"])
        size = _scale_debt_to_size(debt, dmin, dmax)
        enriched.append(
            {
                "name": name,
                "value": [lon, lat, kri, rnk, risk],
                "symbolSize": size,
                "itemStyle": {"opacity": 0.85, "borderColor": "#FFFFFF", "borderWidth": 0.6},
            }
        )

    base = copy.deepcopy(get_echarts_base_options())
    base["grid"] = {
        "left": 48,
        "right": 28,
        "top": 24,
        "bottom": 72,
        "containLabel": True,
    }
    base["tooltip"] = {
        "trigger": "item",
        "backgroundColor": COLORS["primary"],
        "borderColor": COLORS["accent"],
        "borderWidth": 1,
        "textStyle": {
            "color": "#FFFFFF",
            "fontFamily": "Source Sans Pro",
            "fontSize": 12,
        },
        "formatter": (
            "function(p) {"
            "var v = p.value;"
            "var kri = (v[2]!==undefined&&v[2]!==null) ? Number(v[2]).toFixed(2).replace('.', ',') : '';"
            "var rang = v[3]!==undefined ? v[3] : '';"
            "var rk = v[4]!==undefined ? v[4] : '';"
            "return '<div style=\"font-weight:600;margin-bottom:4px\">' + p.name + '</div>'"
            "+ 'KRI Poäng: <b>' + kri + '</b><br/>'"
            "+ 'Rang: <b>' + rang + '</b> av 290<br/>'"
            "+ 'Riskklass: <b>' + rk + '</b>';"
            "}"
        ),
    }

    # Sweden bounding box (approx.) for a map-like frame; hide technical degree labels
    _clean_axis: dict[str, Any] = {
        "axisLabel": {"show": False},
        "axisLine": {"show": False},
        "axisTick": {"show": False},
        "name": "",
    }
    base["xAxis"] = {
        **get_axis_style("value"),
        **_clean_axis,
        "type": "value",
        "min": 10.8,
        "max": 24.4,
        "scale": True,
        "splitLine": {"show": True, "lineStyle": {"color": COLORS["grid"], "opacity": 0.3}},
    }
    base["yAxis"] = {
        **get_axis_style("value"),
        **_clean_axis,
        "type": "value",
        "min": 55.0,
        "max": 69.3,
        "scale": True,
        "splitLine": {"show": True, "lineStyle": {"color": COLORS["grid"], "opacity": 0.3}},
    }
    base["visualMap"] = {
        "min": -2.5,
        "max": 2.5,
        "left": 20,
        "bottom": 16,
        "orient": "horizontal",
        "itemWidth": 12,
        "itemHeight": 140,
        "text": ["Hög risk", "Låg risk"],
        "textStyle": {
            "color": COLORS["text_secondary"],
            "fontSize": 10,
            "fontFamily": "Source Sans Pro",
        },
        "inRange": {"color": list(DIVERGING_SCALE)},
        "calculable": False,
        "dimension": 2,
    }
    base["series"] = [
        {
            "name": "KRI",
            "type": "scatter",
            "data": enriched,
        }
    ]
    return base
