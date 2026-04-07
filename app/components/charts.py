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

# ---------------------------------------------------------------------------
# Local JsCode helper — wraps a JS function string with the placeholder
# markers that streamlit-echarts uses to identify executable JavaScript.
# This avoids importing JsCode (which requires the Streamlit runtime).
# ---------------------------------------------------------------------------
_JS_PLACEHOLDER = "--x_x--0_0--"


def _js(code: str) -> str:
    """Wrap *code* so streamlit-echarts evaluates it as JavaScript."""
    return f"{_JS_PLACEHOLDER}{code}{_JS_PLACEHOLDER}"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GEOJSON_PATH = PROJECT_ROOT / "data" / "geo" / "kommuner.geojson"
CENTROIDS_CSV = PROJECT_ROOT / "data" / "geo" / "kommun_centroids.csv"

# ---------------------------------------------------------------------------
# Shared tooltip CSS constants — reused across all formatter strings
# ---------------------------------------------------------------------------
# These are Python strings injected into JS formatter template literals.
_TT_HDR = "font-weight:700;font-size:14px;color:#1A1A2E;margin-bottom:8px;line-height:1.35"
_TT_HDR_SM = "font-weight:700;font-size:13px;color:#1A1A2E;margin-bottom:6px;line-height:1.35"
_TT_ROW = (
    "display:flex;justify-content:space-between;gap:20px;"
    "font-size:12px;color:#1A1A2E;padding:2px 0;line-height:1.45"
)
_TT_BODY = "font-size:12px;color:#1A1A2E;line-height:1.65"
_TT_LBL = "color:#6B7280;font-weight:400"
_TT_VAL = "font-weight:600;color:#1A1A2E"
_TT_VAL_MONO = "font-weight:600;color:#1A1A2E;font-family:monospace"
_TT_MUTED = "color:#6B7280;font-size:11px;line-height:1.5"
_TT_FTR = "color:#9CA3AF;font-size:11px;margin-top:6px;padding-top:6px;border-top:1px solid #F3F4F6;line-height:1.45"
_TT_DIVIDER = "border-top:1px solid #F3F4F6;margin:6px 0"

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
    _step_val = str(round(step, 4))
    base["tooltip"] = {
        **get_tooltip_style(),
        "trigger": "axis",
        "formatter": _js(
            "function(p){"
            "if(!p||!p.length)return '';"
            "var x=p[0],lo=parseFloat(x.axisValue),hi=lo+" + _step_val + ";"
            "var d=x.data,n=(d&&typeof d==='object'&&'value' in d)?d.value:(typeof x.value==='number'?x.value:0);"
            "var pct=(n/290*100).toFixed(1).replace('.',',');"
            "var z=lo<-0.6745?'Låg risk':lo>=0.6745?'Hög risk':'Medel risk';"
            "var c=lo<-0.6745?'#2E7D5B':lo>=0.6745?'#B94A48':'#D4A03C';"
            "return '<b>KRI '+lo.toFixed(2).replace('.',',')+' \\u2013 '+hi.toFixed(2).replace('.',',')+'</b><br/>'"
            "+'<span style=\"background:'+c+';color:#fff;border-radius:3px;padding:1px 6px;font-size:10px\">'+z+'</span><br/><br/>'"
            "+'Antal: <b>'+n+'</b> / 290 ('+pct+'\\u202f%)';}"
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
        "formatter": _js(
            "function(p){"
            "if(!p||!p.length)return '';"
            "var x=p[0],d=x.data;"
            "var v=(d&&typeof d==='object'&&'value' in d)?d.value:(typeof x.value==='number'?x.value:0);"
            "var s=(v>=0?'+':'')+v.toFixed(3).replace('.',',');"
            "var dir=v>0.01?'\\u25b2 \\u00d6kar risk':v<-0.01?'\\u25bc Minskar risk':'Neutral';"
            "var dc=v>0.01?'#B94A48':v<-0.01?'#2E7D5B':'#6B7280';"
            "return '<b>'+x.name+'</b><br/>'"
            "+'Bidrag: <b>'+s+' po\\u00e4ng</b><br/>'"
            "+'<span style=\"color:'+dc+'\">'+dir+'</span>';}"
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
        "formatter": _js(
            "function(p){"
            "var ind=" + ind_js + ";"
            "var v=p.value||[];"
            "var nm=p.seriesName||p.name||'';"
            "var o='<b>'+nm+'</b><br/>';"
            "for(var i=0;i<ind.length;i++){"
            "var val=typeof v[i]==='number'?v[i]:0;"
            "var s=(val>=0?'+':'')+val.toFixed(2).replace('.',',');"
            "var c=val>0.5?'#B94A48':val<-0.5?'#2E7D5B':'#D4A03C';"
            "if(nm==='Rikssnitt')c='#9CA3AF';"
            "o+='<span style=\"color:#6B7280\">'+ind[i]+'</span> '"
            "+'<b style=\"color:'+c+'\">'+s+'</b><br/>';}"
            "return o;}"
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
        "formatter": _js(
            "function(p){"
            "if(!p||!p.length)return '';"
            "var o='<b>\\u00c5r '+p[0].axisValue+'</b><br/>';"
            "for(var i=0;i<p.length;i++){"
            "var v=typeof p[i].value==='number'?p[i].value:null;"
            "if(v===null||isNaN(v))continue;"
            "var s=v.toFixed(2).replace('.',',');"
            "var z=v<-0.6745?'L\\u00e5g':v>0.6745?'H\\u00f6g':'Medel';"
            "var c=v<-0.6745?'#2E7D5B':v>0.6745?'#B94A48':'#D4A03C';"
            "o+='<span style=\"color:'+p[i].color+'\">\\u25cf</span> '"
            "+p[i].seriesName+': <b>'+s+'</b> '"
            "+'<span style=\"color:'+c+';font-size:11px\">('+z+')</span><br/>';}"
            "return o;}"
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
        "formatter": _js(
            "function(p){"
            "if(!p||!p.length)return '';"
            "var o='<b>'+p[0].axisValue+'</b><br/>',t=0;"
            "for(var i=0;i<p.length;i++){"
            "var v=typeof p[i].value==='number'?p[i].value:0;t+=v;"
            "var s=(v>=0?'+':'')+v.toFixed(3).replace('.',',');"
            "o+='<span style=\"color:'+p[i].color+'\">\\u25a0</span> '"
            "+p[i].seriesName+': <b>'+s+'</b><br/>';}"
            "o+='<br/><b>KRI totalt: '+(t>=0?'+':'')+t.toFixed(2).replace('.',',')+'</b>';"
            "return o;}"
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
        "formatter": _js(
            "function(p){"
            "var v=p.value||[];"
            "var kri=v[2]!=null?Number(v[2]).toFixed(2).replace('.',','):'-';"
            "var rk=v[4]||'-';"
            "var rc=rk==='H\\u00f6g'?'#B94A48':rk==='Medel'?'#D4A03C':'#2E7D5B';"
            "var debt=v[5]!=null?Math.round(v[5]).toLocaleString('sv-SE')+' kr':'-';"
            "var unemp=v[6]!=null?Number(v[6]).toFixed(1).replace('.',',')+' %':'-';"
            "return '<b>'+p.name+'</b><br/>'"
            "+'<span style=\"background:'+rc+';color:#fff;border-radius:3px;padding:1px 6px;font-size:10px\">'+rk+'</span>'"
            "+' Rang '+(v[3]||'-')+' / 290<br/><br/>'"
            "+'KRI: <b>'+kri+'</b><br/>'"
            "+'Skuld: '+debt+'<br/>'"
            "+'Arbetsl\\u00f6shet: '+unemp;}"
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
        "formatter": _js(
            "function(p){"
            "var e=" + edges_js + ";"
            "if(!p||!p.length)return '';"
            "var x=p[0],i=x.dataIndex;"
            "var lo=e[i],hi=e[i+1];"
            "var f=function(v){if(Math.abs(v)>=1e6)return(v/1e6).toFixed(1).replace('.',',')+' M';"
            "if(Math.abs(v)>=1e3)return Math.round(v/1e3)+'k';return v.toFixed(0);};"
            "var d=x.data,n=(d&&typeof d==='object'&&'value' in d)?d.value:(typeof x.value==='number'?x.value:0);"
            "var pct=(n/290*100).toFixed(1).replace('.',',');"
            "return '<b>" + label + ": '+f(lo)+' \\u2013 '+f(hi)+' " + unit + "</b><br/>'"
            "+'Antal: <b>'+n+'</b> / 290 ('+pct+'\\u202f%)';}"
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
