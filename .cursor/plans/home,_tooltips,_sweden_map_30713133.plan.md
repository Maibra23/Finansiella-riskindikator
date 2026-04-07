---
name: Home, tooltips, Sweden map
overview: Add "Startsida" to sidebar nav, standardize all ECharts tooltips for readability, and prepare a full choropleth map implementation (to be done on a new branch).
todos:
  - id: sidebar-startsida
    content: Add Startsida link to sidebar nav in main.py and all page files
    status: pending
  - id: tooltip-constants
    content: Add tooltip CSS helper constants and unify formatter styles in charts.py
    status: pending
  - id: tooltip-fontsize
    content: Increase tooltip base font size in theme.py get_tooltip_style
    status: pending
  - id: branch-choropleth
    content: Create new branch and implement Folium choropleth in sweden_choropleth.py
    status: pending
  - id: integrate-choropleth
    content: Replace scatter map with choropleth in riksoversikt.py and update requirements.txt
    status: pending
isProject: false
---

# Home link, unified tooltips, choropleth map

## 1. Add "Startsida" to sidebar navigation

### Problem
The landing page (`app/main.py`) is not listed in the sidebar nav. Users who navigate away have no easy way to return.

### Solution
Insert a `st.sidebar.page_link` for the entry point at the top of the nav list (before Riksoversikt).

Files to update:
- [`app/main.py`](app/main.py) around line 81: add `("00", "main.py", "Startsida")` (or use `st.switch_page` approach) and link to `"main.py"` directly since it is not under `pages/`.
- [`app/pages/riksoversikt.py`](app/pages/riksoversikt.py), [`app/pages/riskdekomposition.py`](app/pages/riskdekomposition.py), [`app/pages/kommunanalys.py`](app/pages/kommunanalys.py): each mirrors the nav list; add the same entry and point to `"../main.py"` (relative from pages folder).

Note: Streamlit's `st.sidebar.page_link` for a file outside `pages/` needs path `"main.py"` (from root) when running from `app/main.py`.

## 2. Unified readable tooltips across all graphs

### Current state
Tooltips are defined per chart via JavaScript `formatter` strings inside [`app/components/charts.py`](app/components/charts.py). They are already Swedish and detailed, but can be refined for:
- Consistent structure (header, metrics rows, footer context)
- Larger font sizes (currently 10-11px; bump to 11-12px for body)
- Uniform colour scheme
- Clear numeric formatting (Swedish decimal comma, thin space thousands)

### Tooltip template structure (apply to all formatters)

```
+-------------------------------------+
| <b>Header (item/series name)</b>   |
|-------------------------------------|
| Metric 1 label          Value       |
| Metric 2 label          Value       |
| ...                                 |
|-------------------------------------|
| <muted> Context / hint </muted>     |
+-------------------------------------+
```

### Charts to audit

| Chart | Function | Current | Action |
|-------|----------|---------|--------|
| KRI histogram | `build_distribution_histogram` | Good | Minor: enlarge, consistent header style |
| Contribution bar | `build_horizontal_contribution_bar` | Good | Minor: spacing |
| Radar | `build_radar` | Good | No change needed |
| Trend line | `build_line_trend` | Good | Year header already present |
| Grouped bars | `build_grouped_bars_comparison` | Good | No change |
| Geo scatter | `build_sweden_geo_scatter` | Good | Will be replaced by choropleth |
| Raw histogram | `build_raw_indicator_histogram` | Good | Minor: spacing |

All tooltips already follow the pattern; the main improvement is a central helper that returns consistent CSS/structure and then each formatter reuses it. This keeps maintenance easier.

### Implementation approach
1. Add a small helper constant `_TOOLTIP_HEADER_CSS` and `_TOOLTIP_ROW_CSS` at top of `charts.py`.
2. Refactor each formatter to use these constants so styling is uniform.
3. Increase base font sizes in `get_tooltip_style()` inside [`app/styles/theme.py`](app/styles/theme.py) from 11 to 12px (or 11.5).

## 3. Full choropleth map of Sweden (new branch)

### Goal
Replace the scatter plot of municipality centroids with an actual shape-based choropleth where each kommun polygon is filled by KRI colour.

### Technical requirements

1. **GeoJSON**: Already present at `data/geo/kommuner.geojson`. Verify that each feature has `id` = `municipality_code` (or properties.id).

2. **ECharts map registration**: ECharts requires explicit registration of a custom map via `echarts.registerMap(name, geojson)`. With `streamlit-echarts`, this must be done **before** rendering:
   - Option A: Pass `map=geojson_dict` into `st_echarts` (supported but limited).
   - Option B: Use a custom component or inject JS.
   - Option C: Use `pydeck` or `folium` instead of ECharts for true geo.

   Recommended: **Folium + streamlit-folium** because it natively supports GeoJSON choropleth, tooltips, and is well-tested for Sweden-scale maps. ECharts map registration in Streamlit is fragile.

3. **Implementation steps (on new branch)**
   1. `pip install folium streamlit-folium` (add to requirements.txt).
   2. Create `app/components/sweden_choropleth.py` with `render_choropleth(kri_df, year)`.
   3. Load GeoJSON, merge KRI scores by code, colour by KRI using a diverging colormap (same green-yellow-red).
   4. Configure tooltip with all metrics (kommun, KRI, rang, skuld, arbetslöshet, etc.).
   5. Replace `render_sweden_map` call in [`app/pages/riksoversikt.py`](app/pages/riksoversikt.py) with `render_choropleth`.
   6. Adjust card header text from "Punktkarta" to "Karta" or "Kommunkartor".
   7. Test performance (290 polygons should be fine).

### Fallback
If Folium is too slow or heavy, we can try `st.pydeck_chart` with a `GeoJsonLayer`. Both are more reliable than ECharts for true geographic maps in Streamlit.

## Files to touch

| File | Changes |
|------|---------|
| `app/main.py` | Add Startsida link |
| `app/pages/riksoversikt.py` | Add Startsida link; later swap map component |
| `app/pages/riskdekomposition.py` | Add Startsida link |
| `app/pages/kommunanalys.py` | Add Startsida link |
| `app/styles/theme.py` | Tooltip base font size tweak |
| `app/components/charts.py` | Minor tooltip CSS constants |
| `app/components/sweden_choropleth.py` (new) | Full choropleth with Folium |
| `requirements.txt` | Add `folium`, `streamlit-folium` |

## Verification

- After nav changes: click every sidebar link and confirm navigation works from any page.
- After tooltip changes: hover each chart type and confirm consistent styling.
- After choropleth: visually confirm all 290 kommuner render, colours match KRI, tooltips display correctly.
