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
    base["grid"] = {"left": 56, "right": 28, "top": 20, "bottom": 70, "containLabel": True}
    base["tooltip"] = {
        **get_tooltip_style(),
        "trigger": "axis",
        "formatter": (
            "function(params) {"
            "  if (!params || !params.length) return '';"
            "  var p = params[0];"
            "  var lo = parseFloat(p.axisValue);"
            "  var hi = lo + " + str(round(step, 4)) + ";"
            "  var loStr = lo.toFixed(2).replace('.', ',');"
            "  var hiStr = hi.toFixed(2).replace('.', ',');"
            "  var count = (typeof p.value === 'object' && p.value !== null) ? (p.value.value || 0) : (p.value || 0);"
            "  var pct = (Number(count) / 290 * 100).toFixed(1).replace('.', ',');"
            "  var zone = lo < -0.6745 ? 'Låg risk' : (lo >= 0.6745 ? 'Hög risk' : 'Medel risk');"
            "  var zoneColor = lo < -0.6745 ? '#2E7D5B' : (lo >= 0.6745 ? '#B94A48' : '#D4A03C');"
            "  var zBadge = '<span style=\"background:' + zoneColor + ';color:#fff;"
            "border-radius:3px;padding:2px 8px;font-size:11px;font-weight:700;\">' + zone + '</span>';"
            "  return '<div style=\"font-weight:700;font-size:13px;color:#1A1A2E;margin-bottom:8px\">"
            "KRI-intervall: ' + loStr + ' \u2013 ' + hiStr + '</div>'"
            "  + '<div style=\"margin-bottom:8px\">' + zBadge + '</div>'"
            "  + '<div style=\"font-size:11px;color:#1A1A2E;line-height:1.8\">"
            "Antal kommuner: <b>' + count + '</b> av 290<br/>'"
            "  + 'Andel: <b>' + pct + '\u202f%</b><br/>'"
            "  + '<span style=\"color:#6B7280;font-size:10px\">KRI = viktat z-po\u00e4ngindex \u2212 h\u00f6gre v\u00e4rde = h\u00f6gre risk</span></div>';"
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
    base["grid"] = {"left": 150, "right": 70, "top": 30, "bottom": 50, "containLabel": True}
    base["tooltip"] = {
        **get_tooltip_style(),
        "trigger": "axis",
        "axisPointer": {"type": "shadow"},
        "formatter": (
            "function(params) {"
            "  if (!params || !params.length) return '';"
            "  var p = params[0];"
            "  var v = typeof p.value === 'number' ? p.value : "
            "         (typeof p.value === 'object' && p.value !== null ? (p.value.value || 0) : 0);"
            "  var vStr = (v >= 0 ? '+' : '') + v.toFixed(3).replace('.', ',');"
            "  var dir = v > 0.01 ? '\u25b2 \u00d6kar risk' : (v < -0.01 ? '\u25bc Minskar risk' : '\u2500 Neutral p\u00e5verkan');"
            "  var dirColor = v > 0.01 ? '#B94A48' : (v < -0.01 ? '#2E7D5B' : '#6B7280');"
            "  return '<div style=\"font-weight:700;font-size:13px;color:#1A1A2E;margin-bottom:8px\">' + p.name + '</div>'"
            "  + '<div style=\"font-size:11px;color:#1A1A2E;line-height:1.8\">"
            "Bidrag till KRI: <b style=\"font-family:monospace\">' + vStr + ' po\u00e4ng</b><br/>'"
            "  + '<span style=\"color:' + dirColor + ';font-weight:600\">' + dir + '</span><br/>'"
            "  + '<span style=\"color:#6B7280;font-size:10px\">V\u00e4gd z-po\u00e4ng \u00d7 indikatorvikt</span></div>';"
            "}"
        ),
    }
    base["xAxis"] = {**get_axis_style("value"), "type": "value", "name": "Bidrag till KRI"}
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
    # Build indicator names JS array for tooltip
    ind_js = "[" + ",".join(f'"{n}"' for n in indicators) + "]"
    base = copy.deepcopy(get_echarts_base_options())
    base.pop("grid", None)
    base["tooltip"] = {
        **get_tooltip_style(),
        "trigger": "item",
        "formatter": (
            "function(params) {"
            "  var indicators = " + ind_js + ";"
            "  var vals = params.value;"
            "  var name = params.seriesName || params.name || '';"
            "  var isRef = name === 'Rikssnitt';"
            "  var out = '<div style=\"font-weight:700;font-size:12px;color:#1A1A2E;margin-bottom:6px\">' + name + '</div>';"
            "  for (var i = 0; i < indicators.length; i++) {"
            "    var v = typeof vals[i] === 'number' ? vals[i] : 0;"
            "    var vStr = v.toFixed(2).replace('.', ',');"
            "    var sign = v >= 0 ? '+' : '';"
            "    var col = v > 0.5 ? '#B94A48' : (v < -0.5 ? '#2E7D5B' : '#D4A03C');"
            "    if (isRef) col = '#9CA3AF';"
            "    out += '<div style=\"display:flex;justify-content:space-between;gap:16px;"
            "font-size:11px;color:#1A1A2E;padding:1px 0\">';"
            "    out += '<span>' + indicators[i] + '</span>';"
            "    out += '<span style=\"font-weight:600;color:' + col + '\">' + sign + vStr + '</span>';"
            "    out += '</div>';"
            "  }"
            "  out += '<div style=\"font-size:10px;color:#9CA3AF;margin-top:6px\">"
            "Z-poäng: +högt = hög risk, -lågt = låg risk</div>';"
            "  return out;"
            "}"
        ),
    }
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
    base["tooltip"] = {
        **get_tooltip_style(),
        "trigger": "axis",
        "axisPointer": {"type": "line", "lineStyle": {"color": COLORS["accent"], "width": 1.5, "type": "dashed"}},
        "formatter": (
            "function(params) {"
            "  if (!params || !params.length) return '';"
            "  var year = params[0].axisValue;"
            "  var out = '<div style=\"font-weight:700;font-size:12px;color:#1A1A2E;margin-bottom:8px\">"
            "\\u00c5r: ' + year + '</div>';"
            "  for (var i = 0; i < params.length; i++) {"
            "    var p = params[i];"
            "    var v = typeof p.value === 'number' ? p.value : null;"
            "    if (v === null || isNaN(v)) continue;"
            "    var vStr = v.toFixed(3).replace('.', ',');"
            "    var zone = v < -0.6745 ? 'Låg risk' : (v > 0.6745 ? 'Hög risk' : 'Medel risk');"
            "    var zoneCol = v < -0.6745 ? '#2E7D5B' : (v > 0.6745 ? '#B94A48' : '#D4A03C');"
            "    var dot = '<span style=\"display:inline-block;width:8px;height:8px;"
            "border-radius:50%;background:' + p.color + ';margin-right:6px;\"></span>';"
            "    out += '<div style=\"display:flex;align-items:center;justify-content:space-between;"
            "gap:20px;font-size:11px;color:#1A1A2E;padding:2px 0;\">';"
            "    out += '<span>' + dot + p.seriesName + '</span>';"
            "    out += '<span style=\"font-family:monospace;font-weight:600\">' + vStr + '"
            "       + ' <span style=\"color:' + zoneCol + ';font-size:10px\">' + zone + '</span></span>';"
            "    out += '</div>';"
            "  }"
            "  return out;"
            "}"
        ),
    }
    base["grid"] = {"left": 56, "right": 30, "top": 60, "bottom": 70, "containLabel": True}
    base["legend"] = {
        "data": list(series_dict.keys()),
        "top": 6,
        "right": 20,
        "textStyle": {"fontFamily": "Source Sans Pro", "fontSize": 11, "color": COLORS["text_primary"]},
        "type": "scroll",
        "pageIconColor": COLORS["primary"],
        "pageTextStyle": {"color": COLORS["text_secondary"]},
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
    _TREND_PALETTE = [
        COLORS["primary"],     # #0B1F3F
        COLORS["high_risk"],   # #B94A48
        COLORS["secondary"],   # #4A6FA5
        COLORS["low_risk"],    # #2E7D5B
        COLORS["accent"],      # #C4A35A
        "#7B2D8E",             # purple
        "#E07040",             # orange
    ]
    series_list: list[dict[str, Any]] = []
    color_idx = 0
    for name, vals in series_dict.items():
        is_ref = name == "Rikssnitt"
        if is_ref:
            line_color = COLORS["text_tertiary"]
        else:
            line_color = _TREND_PALETTE[color_idx % len(_TREND_PALETTE)]
            color_idx += 1
        series_list.append(
            {
                "name": name,
                "type": "line",
                "data": vals,
                "smooth": True,
                "lineStyle": {
                    "width": 2.5,
                    "color": line_color,
                    "type": "dashed" if is_ref else "solid",
                },
                "itemStyle": {"color": line_color},
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
    base["tooltip"] = {
        **get_tooltip_style(),
        "trigger": "axis",
        "axisPointer": {"type": "shadow"},
        "formatter": (
            "function(params) {"
            "  if (!params || !params.length) return '';"
            "  var muni = params[0].axisValue;"
            "  var out = '<div style=\"font-weight:700;font-size:12px;color:#1A1A2E;margin-bottom:8px\">' + muni + '</div>';"
            "  var total = 0;"
            "  for (var i = 0; i < params.length; i++) {"
            "    var v = typeof params[i].value === 'number' ? params[i].value : 0;"
            "    total += v;"
            "  }"
            "  for (var j = 0; j < params.length; j++) {"
            "    var p = params[j];"
            "    var v = typeof p.value === 'number' ? p.value : 0;"
            "    var vStr = (v >= 0 ? '+' : '') + v.toFixed(3).replace('.', ',');"
            "    var dir = v > 0.01 ? '\\u25b2 \\u00d6kar risk' : (v < -0.01 ? '\\u25bc Minskar risk' : '\\u2500 Neutral');"
            "    var dirCol = v > 0.01 ? '#B94A48' : (v < -0.01 ? '#2E7D5B' : '#9CA3AF');"
            "    var dot = '<span style=\"display:inline-block;width:8px;height:8px;"
            "border-radius:2px;background:' + p.color + ';margin-right:6px;\"></span>';"
            "    out += '<div style=\"font-size:11px;color:#1A1A2E;padding:2px 0;display:flex;"
            "justify-content:space-between;gap:16px\">';"
            "    out += '<span>' + dot + p.seriesName + '</span>';"
            "    out += '<span style=\"font-weight:600;font-family:monospace\">' + vStr"
            "         + ' <span style=\"color:' + dirCol + ';font-size:10px\">' + dir + '</span></span>';"
            "    out += '</div>';"
            "  }"
            "  var totalStr = (total >= 0 ? '+' : '') + total.toFixed(3).replace('.', ',');"
            "  out += '<div style=\"margin-top:8px;padding-top:6px;border-top:1px solid #EEF0F3;"
            "font-size:11px;color:#1A1A2E;display:flex;justify-content:space-between\">';"
            "  out += '<span style=\"font-weight:600\">KRI Totalt</span>';"
            "  out += '<span style=\"font-weight:700;font-family:monospace\">' + totalStr + '</span>';"
            "  out += '</div>';"
            "  return out;"
            "}"
        ),
    }
    base["grid"] = {"left": 56, "right": 24, "top": 60, "bottom": 80, "containLabel": True}
    base["legend"] = {
        "data": list(components.keys()),
        "top": 10,
        "textStyle": {"fontFamily": "Source Sans Pro", "color": COLORS["text_primary"], "fontSize": 11},
        "type": "scroll",
    }
    base["xAxis"] = {
        **get_axis_style("category"),
        "type": "category",
        "data": municipalities,
        "axisLabel": {"rotate": 20, "fontSize": 11, "overflow": "truncate", "width": 120},
    }
    base["yAxis"] = {
        **get_axis_style("value"),
        "type": "value",
        "name": "Bidrag till KRI",
        "nameTextStyle": {"color": COLORS["text_secondary"], "fontSize": 11},
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
        unemp = float(row.get("unemployment", 0))
        pop_growth = float(row.get("population_growth", 0))
        tax_base = float(row.get("tax_base_relative", 0))
        size = _scale_debt_to_size(debt, dmin, dmax)
        # value: [lon, lat, kri_score, rank, risk_class, debt, unemployment, pop_growth, tax_base]
        enriched.append(
            {
                "name": name,
                "value": [lon, lat, kri, rnk, risk, debt, unemp, pop_growth, tax_base],
                "symbolSize": size,
                "itemStyle": {"opacity": 0.85, "borderColor": "#FFFFFF", "borderWidth": 0.6},
            }
        )

    base = copy.deepcopy(get_echarts_base_options())
    base["grid"] = {
        "left": 60,
        "right": 28,
        "top": 16,
        "bottom": 100,
        "containLabel": True,
    }
    base["tooltip"] = {
        **get_tooltip_style(),
        "trigger": "item",
        "formatter": (
            "function(p) {"
            "  var v = p.value;"
            "  var kri  = (v[2]!=null) ? Number(v[2]).toFixed(3).replace('.', ',') : '-';"
            "  var rang = (v[3]!=null) ? v[3] : '-';"
            "  var rk   = (v[4]!=null) ? v[4] : '-';"
            "  var debt = (v[5]!=null) ? Math.round(v[5]).toLocaleString('sv-SE') + ' kr' : '-';"
            "  var unemp= (v[6]!=null) ? Number(v[6]).toFixed(1).replace('.', ',') + ' %' : '-';"
            "  var pop  = (v[7]!=null) ? (v[7]>=0?'+':'') + Number(v[7]).toFixed(1).replace('.', ',') + ' %' : '-';"
            "  var tax  = (v[8]!=null) ? Number(v[8]).toFixed(1).replace('.', ',') + ' %' : '-';"
            "  var rkCol= rk==='H\\u00f6g'?'#B94A48': rk==='Medel'?'#D4A03C':'#2E7D5B';"
            "  var rkBadge = '<span style=\"background:' + rkCol + ';color:#fff;border-radius:3px;"
            "padding:1px 7px;font-size:10px;font-weight:700;\">' + rk + '</span>';"
            "  var row = function(label, val) {"
            "    return '<div style=\"display:flex;justify-content:space-between;gap:20px;"
            "font-size:11px;color:#1A1A2E;padding:1px 0\"><span style=\"color:#6B7280\">' "
            "+ label + '</span><span style=\"font-weight:600;color:#1A1A2E\">' + val + '</span></div>';"
            "  };"
            "  return '<div style=\"font-weight:700;font-size:13px;color:#1A1A2E;margin-bottom:8px\">' + p.name + '</div>'"
            "  + '<div style=\"margin-bottom:6px\">' + rkBadge + ' <span style=\"color:#6B7280\">Rang ' + rang + ' av 290</span></div>'"
            "  + row('KRI Po\\u00e4ng', kri)"
            "  + row('Skuld per capita', debt)"
            "  + row('Arbetsl\\u00f6shet', unemp)"
            "  + row('Befolkningstillv\\u00e4xt (5 \\u00e5r)', pop)"
            "  + row('Skattekraft (% av rikssnitt)', tax);"
            "}"
        ),
    }

    # Sweden geographic bounding box — show lat/lon axes to give spatial scale context
    _geo_axis_label: dict[str, Any] = {
        "show": True,
        "color": COLORS["text_tertiary"],
        "fontSize": 9,
        "fontFamily": "Source Sans Pro",
    }
    base["xAxis"] = {
        **get_axis_style("value"),
        "type": "value",
        "min": 10.8,
        "max": 24.4,
        "scale": True,
        "name": "Longitud (°E)",
        "nameLocation": "middle",
        "nameGap": 28,
        "nameTextStyle": {"color": COLORS["text_secondary"], "fontSize": 10, "fontFamily": "Source Sans Pro"},
        "axisLabel": {**_geo_axis_label, "formatter": "{value}°"},
        "axisLine": {"show": False},
        "axisTick": {"show": False},
        "splitLine": {"show": True, "lineStyle": {"color": COLORS["grid"], "opacity": 0.3}},
    }
    base["yAxis"] = {
        **get_axis_style("value"),
        "type": "value",
        "min": 55.0,
        "max": 69.3,
        "scale": True,
        "name": "Latitud (°N)",
        "nameLocation": "middle",
        "nameGap": 38,
        "nameTextStyle": {"color": COLORS["text_secondary"], "fontSize": 10, "fontFamily": "Source Sans Pro"},
        "axisLabel": {**_geo_axis_label, "formatter": "{value}°"},
        "axisLine": {"show": False},
        "axisTick": {"show": False},
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


def build_raw_indicator_histogram(
    values: list[float],
    label: str,
    unit: str,
    n_bins: int = 20,
) -> dict[str, Any]:
    """Histogram of a raw (pre-normalization) indicator in its natural unit.

    Used to show users the indicator's distribution before z-score standardisation.
    """
    if not values:
        return {}
    lo = min(values)
    hi = max(values) + 1e-9
    step = (hi - lo) / n_bins
    edges = [lo + i * step for i in range(n_bins + 1)]
    counts = [0] * n_bins
    for x in values:
        idx = min(int((x - lo) / step), n_bins - 1)
        counts[idx] += 1

    def _fmt_k(v: float) -> str:
        if abs(v) >= 1_000_000:
            return f"{v / 1_000_000:.1f}M"
        if abs(v) >= 1_000:
            return f"{v / 1_000:.0f}k"
        return f"{v:.1f}"

    categories = [_fmt_k(edges[i]) for i in range(n_bins)]
    bar_data = [
        {"value": c, "itemStyle": {"color": COLORS["secondary"], "borderRadius": [2, 2, 0, 0]}}
        for c in counts
    ]

    edges_js = "[" + ",".join(str(round(e, 2)) for e in edges) + "]"

    base = copy.deepcopy(get_echarts_base_options())
    base["grid"] = {"left": 56, "right": 28, "top": 20, "bottom": 70, "containLabel": True}
    base["tooltip"] = {
        **get_tooltip_style(),
        "trigger": "axis",
        "formatter": (
            "function(params) {"
            "  var edges = " + edges_js + ";"
            "  if (!params || !params.length) return '';"
            "  var i = params[0].dataIndex;"
            "  var lo = edges[i], hi = edges[i + 1];"
            "  var fmt = function(v) {"
            "    if (Math.abs(v) >= 1000000) return (v/1000000).toFixed(1).replace('.',',') + '\u202fM';"
            "    if (Math.abs(v) >= 1000) return Math.round(v/1000) + '\u202fk';"
            "    return v.toFixed(1).replace('.',',');"
            "  };"
            "  var count = (typeof params[0].value === 'object' && params[0].value !== null)"
            "    ? (params[0].value.value || 0) : (params[0].value || 0);"
            "  var pct = (Number(count) / 290 * 100).toFixed(1).replace('.', ',');"
            "  return '<div style=\"font-weight:700;font-size:13px;color:#1A1A2E;margin-bottom:8px\">"
            + label + ": ' + fmt(lo) + ' \u2013 ' + fmt(hi) + ' " + unit + "</div>'"
            "  + '<div style=\"font-size:11px;color:#1A1A2E;line-height:1.8\">"
            "Antal kommuner: <b>' + count + '</b> av 290<br/>'"
            "  + 'Andel: <b>' + pct + '\u202f%</b><br/>'"
            "  + '<span style=\"color:#6B7280;font-size:10px\">R\u00e5data f\u00f6re z-po\u00e4ngsnormalisering</span></div>';"
            "}"
        ),
    }
    base["xAxis"] = {
        **get_axis_style("category"),
        "type": "category",
        "data": categories,
        "name": f"{label} ({unit})",
        "nameLocation": "middle",
        "nameGap": 36,
        "nameTextStyle": {
            "color": COLORS["text_secondary"],
            "fontSize": 11,
            "fontFamily": "Source Sans Pro",
            "fontWeight": 600,
        },
        "axisLabel": {"interval": max(0, n_bins // 8 - 1), "rotate": 30, "fontSize": 10},
    }
    base["yAxis"] = {
        **get_axis_style("value"),
        "type": "value",
        "name": "Antal kommuner",
        "nameTextStyle": {
            "color": COLORS["text_secondary"],
            "fontSize": 11,
            "fontFamily": "Source Sans Pro",
            "fontWeight": 600,
            "padding": [0, 0, 10, 0],
        },
        "axisLine": {"show": False},
    }
    base["series"] = [{"type": "bar", "data": bar_data, "barWidth": "85%"}]
    return base
