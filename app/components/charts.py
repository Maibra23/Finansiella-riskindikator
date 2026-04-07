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
            "  var lo = parseFloat(p.axisValue);"
            "  var hi = lo + " + str(round(step, 4)) + ";"
            "  var loStr = lo.toFixed(2).replace('.', ',');"
            "  var hiStr = hi.toFixed(2).replace('.', ',');"
            "  var count = p.value || 0;"
            "  var pct = (count / 290 * 100).toFixed(1).replace('.', ',');"
            "  var zone = lo < -0.6745 ? 'Låg risk' : (lo >= 0.6745 ? 'Hög risk' : 'Medel risk');"
            "  var zoneColor = lo < -0.6745 ? '#2E7D5B' : (lo >= 0.6745 ? '#B94A48' : '#D4A03C');"
            "  var zBadge = '<span style=\"background:' + zoneColor + ';color:#fff;"
            "border-radius:3px;padding:1px 6px;font-size:10px;font-weight:600;\">' + zone + '</span>';"
            "  return '<div style=\"font-weight:700;font-size:12px;margin-bottom:6px\">"
            "KRI-intervall: ' + loStr + ' till ' + hiStr + '</div>'"
            "  + zBadge + '<br/><br/>'"
            "  + 'Antal kommuner: <b>' + count + '</b> av 290<br/>'"
            "  + 'Andel: <b>' + pct + ' %</b>';"
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
        "formatter": (
            "function(params) {"
            "  if (!params || !params.length) return '';"
            "  var p = params[0];"
            "  var v = typeof p.value === 'number' ? p.value : 0;"
            "  var vStr = v.toFixed(3).replace('.', ',');"
            "  var sign = v >= 0 ? '+' : '';"
            "  var dir = v > 0.01 ? 'Ökar risken' : (v < -0.01 ? 'Minskar risken' : 'Neutralt');"
            "  var dirColor = v > 0.01 ? '#B94A48' : (v < -0.01 ? '#2E7D5B' : '#6B7280');"
            "  var abs = Math.abs(v);"
            "  var share = (abs * 100).toFixed(1).replace('.', ',');"
            "  return '<div style=\"font-weight:700;font-size:12px;margin-bottom:6px\">' + p.name + '</div>'"
            "  + 'Bidrag till KRI: <b>' + sign + vStr + '</b><br/>'"
            "  + '<span style=\"color:' + dirColor + ';font-weight:600\">' + dir + '</span><br/>'"
            "  + 'Absolut bidrag: <b>' + share + ' % av KRI-enheter</b>';"
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
            "  var out = '<div style=\"font-weight:700;font-size:12px;margin-bottom:6px\">' + name + '</div>';"
            "  for (var i = 0; i < indicators.length; i++) {"
            "    var v = typeof vals[i] === 'number' ? vals[i] : 0;"
            "    var vStr = v.toFixed(2).replace('.', ',');"
            "    var sign = v >= 0 ? '+' : '';"
            "    var col = v > 0.5 ? '#B94A48' : (v < -0.5 ? '#2E7D5B' : '#D4A03C');"
            "    if (isRef) col = '#9CA3AF';"
            "    out += '<div style=\"display:flex;justify-content:space-between;gap:16px;"
            "font-size:11px;padding:1px 0\">';"
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
            "  var out = '<div style=\"font-weight:700;font-size:12px;margin-bottom:8px\">År: ' + year + '</div>';"
            "  for (var i = 0; i < params.length; i++) {"
            "    var p = params[i];"
            "    var v = typeof p.value === 'number' ? p.value : null;"
            "    if (v === null) continue;"
            "    var vStr = v.toFixed(3).replace('.', ',');"
            "    var zone = v < -0.6745 ? 'Låg risk' : (v > 0.6745 ? 'Hög risk' : 'Medel risk');"
            "    var zoneCol = v < -0.6745 ? '#2E7D5B' : (v > 0.6745 ? '#B94A48' : '#D4A03C');"
            "    var dot = '<span style=\"display:inline-block;width:8px;height:8px;"
            "border-radius:50%;background:' + p.color + ';margin-right:6px;\"></span>';"
            "    out += '<div style=\"display:flex;align-items:center;justify-content:space-between;"
            "gap:20px;font-size:11px;padding:2px 0;\">';"
            "    out += '<span>' + dot + p.seriesName + '</span>';"
            "    out += '<span style=\"font-family:monospace;font-weight:600\">' + vStr + '"
            "       + ' <span style=\"color:' + zoneCol + ';font-size:10px\">' + zone + '</span></span>';"
            "    out += '</div>';"
            "  }"
            "  return out;"
            "}"
        ),
    }
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
    base["tooltip"] = {
        **get_tooltip_style(),
        "trigger": "axis",
        "axisPointer": {"type": "shadow"},
        "formatter": (
            "function(params) {"
            "  if (!params || !params.length) return '';"
            "  var muni = params[0].axisValue;"
            "  var out = '<div style=\"font-weight:700;font-size:12px;margin-bottom:8px\">' + muni + '</div>';"
            "  var total = 0;"
            "  for (var i = 0; i < params.length; i++) {"
            "    var v = typeof params[i].value === 'number' ? params[i].value : 0;"
            "    total += v;"
            "  }"
            "  for (var j = 0; j < params.length; j++) {"
            "    var p = params[j];"
            "    var v = typeof p.value === 'number' ? p.value : 0;"
            "    var vStr = (v >= 0 ? '+' : '') + v.toFixed(3).replace('.', ',');"
            "    var dir = v > 0.01 ? '▲ Ökar risk' : (v < -0.01 ? '▼ Minskar risk' : '─ Neutral');"
            "    var dirCol = v > 0.01 ? '#B94A48' : (v < -0.01 ? '#2E7D5B' : '#9CA3AF');"
            "    var dot = '<span style=\"display:inline-block;width:8px;height:8px;"
            "border-radius:2px;background:' + p.color + ';margin-right:6px;\"></span>';"
            "    out += '<div style=\"font-size:11px;padding:2px 0;display:flex;"
            "justify-content:space-between;gap:16px\">';"
            "    out += '<span>' + dot + p.seriesName + '</span>';"
            "    out += '<span style=\"font-weight:600;font-family:monospace\">' + vStr"
            "         + ' <span style=\"color:' + dirCol + ';font-size:10px\">' + dir + '</span></span>';"
            "    out += '</div>';"
            "  }"
            "  var totalStr = (total >= 0 ? '+' : '') + total.toFixed(3).replace('.', ',');"
            "  out += '<div style=\"margin-top:8px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.15);"
            "font-size:11px;display:flex;justify-content:space-between\">';"
            "  out += '<span style=\"font-weight:600\">KRI Totalt</span>';"
            "  out += '<span style=\"font-weight:700;font-family:monospace\">' + totalStr + '</span>';"
            "  out += '</div>';"
            "  return out;"
            "}"
        ),
    }
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
        "name": "Bidrag till KRI",
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
        "padding": [10, 14],
        "textStyle": {
            "color": "#FFFFFF",
            "fontFamily": "Source Sans Pro",
            "fontSize": 12,
        },
        "formatter": (
            "function(p) {"
            "  var v = p.value;"
            "  var kri  = (v[2]!=null) ? Number(v[2]).toFixed(3).replace('.', ',') : '–';"
            "  var rang = (v[3]!=null) ? v[3] : '–';"
            "  var rk   = (v[4]!=null) ? v[4] : '–';"
            "  var debt = (v[5]!=null) ? Math.round(v[5]).toLocaleString('sv-SE') + ' kr' : '–';"
            "  var unemp= (v[6]!=null) ? Number(v[6]).toFixed(1).replace('.', ',') + ' %' : '–';"
            "  var pop  = (v[7]!=null) ? (v[7]>=0?'+':'') + Number(v[7]).toFixed(1).replace('.', ',') + ' %' : '–';"
            "  var tax  = (v[8]!=null) ? Number(v[8]).toFixed(1).replace('.', ',') + ' %' : '–';"
            "  var rkCol= rk==='Hög'?'#F87171': rk==='Medel'?'#FCD34D':'#6EE7B7';"
            "  var rkBadge = '<span style=\"background:' + rkCol + ';color:#0B1F3F;border-radius:3px;"
            "padding:1px 7px;font-size:10px;font-weight:700;\">' + rk + '</span>';"
            "  var row = function(label, val) {"
            "    return '<div style=\"display:flex;justify-content:space-between;gap:20px;"
            "font-size:11px;padding:1px 0\"><span style=\"color:rgba(255,255,255,0.65)\">' "
            "+ label + '</span><span style=\"font-weight:600\">' + val + '</span></div>';"
            "  };"
            "  return '<div style=\"font-weight:700;font-size:13px;margin-bottom:8px\">' + p.name + '</div>'"
            "  + '<div style=\"margin-bottom:6px\">' + rkBadge + ' Rang ' + rang + ' av 290</div>'"
            "  + row('KRI Poäng', kri)"
            "  + row('Skuld per capita', debt)"
            "  + row('Arbetslöshet', unemp)"
            "  + row('Befolkningstillväxt (5 år)', pop)"
            "  + row('Skattekraft (% av rikssnitt)', tax);"
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
