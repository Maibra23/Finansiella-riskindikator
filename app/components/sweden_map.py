# Choropleth would need GeoJSON registered via streamlit_echarts.Map.
# Current: Cartesian scatter (lon/lat) from kommuner.geojson / kommun_centroids.csv.

"""Sweden KRI scatter map (centroids) rendered with streamlit-echarts."""

from __future__ import annotations

import pandas as pd

from app.components.charts import build_sweden_geo_scatter


def render_sweden_map(kri_df: pd.DataFrame, year: int, height: str = "440px") -> None:
    """Render Sweden municipality map with KRI risk coloring using streamlit-echarts."""
    from streamlit_echarts import st_echarts

    options = build_sweden_geo_scatter(kri_df, year)
    st_echarts(options=options, height=height, key=f"sweden_map_{year}")
