"""Regression tests for the Sweden choropleth component.

Guards two defects found in the published dashboard:
  1. CARTO withdrew anonymous basemap access, so cartocdn tiles render with an
     "API KEY REQUIRED" watermark. The map must not reference that host.
  2. The composite KRI has a spread well below one standard deviation, so a
     fixed +-2.5 colour domain compressed every municipality into one shade.
"""

from pathlib import Path

import pandas as pd
import pytest

from app.components.sweden_choropleth import _build_colormap, build_choropleth_map
from src.config import MAP_TILES

RESULTS_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "kri_results.parquet"


@pytest.fixture(scope="module")
def kri_df() -> pd.DataFrame:
    if not RESULTS_PATH.exists():
        pytest.skip("kri_results.parquet not built")
    return pd.read_parquet(RESULTS_PATH)


@pytest.fixture(scope="module")
def latest_year(kri_df: pd.DataFrame) -> int:
    return int(kri_df["year"].max())


@pytest.mark.unit
class TestBasemap:
    def test_tile_url_is_keyless(self) -> None:
        assert "cartocdn" not in MAP_TILES["url"]
        assert "{apikey}" not in MAP_TILES["url"].lower()
        assert "access_token" not in MAP_TILES["url"].lower()

    def test_tile_url_is_attributed(self) -> None:
        assert MAP_TILES["attribution"].strip(), "Tile provider requires attribution"

    def test_rendered_map_never_requests_carto_tiles(
        self, kri_df: pd.DataFrame, latest_year: int
    ) -> None:
        html = build_choropleth_map(kri_df, latest_year).get_root().render()
        assert "cartocdn" not in html
        assert MAP_TILES["url"] in html


@pytest.mark.unit
class TestColormap:
    def test_stops_are_strictly_increasing(self, kri_df: pd.DataFrame) -> None:
        for year in sorted(kri_df["year"].unique()):
            stops = _build_colormap(kri_df[kri_df["year"] == year]["kri_score"].astype(float)).index
            assert all(b > a for a, b in zip(stops, stops[1:])), f"non-monotone stops for {year}"

    def test_neutral_colour_sits_at_zero(self, kri_df: pd.DataFrame, latest_year: int) -> None:
        stops = _build_colormap(kri_df[kri_df["year"] == latest_year]["kri_score"].astype(float)).index
        assert 0.0 in stops, "the average municipality must map to the neutral colour"

    def test_domain_tracks_actual_spread(self, kri_df: pd.DataFrame, latest_year: int) -> None:
        scores = kri_df[kri_df["year"] == latest_year]["kri_score"].astype(float)
        stops = _build_colormap(scores).index
        extent = max(abs(scores.min()), abs(scores.max()))
        assert stops[0] == pytest.approx(-extent)
        assert stops[-1] == pytest.approx(extent)

    def test_breakpoints_match_risk_class_quartiles(
        self, kri_df: pd.DataFrame, latest_year: int
    ) -> None:
        scores = kri_df[kri_df["year"] == latest_year]["kri_score"].astype(float)
        stops = _build_colormap(scores).index
        assert stops[1] == pytest.approx(scores.quantile(0.25))
        assert stops[3] == pytest.approx(scores.quantile(0.75))

    def test_degenerate_spread_does_not_crash(self, kri_df: pd.DataFrame, latest_year: int) -> None:
        one = kri_df[kri_df["year"] == latest_year]["kri_score"].astype(float).head(1)
        stops = _build_colormap(one).index
        assert all(b > a for a, b in zip(stops, stops[1:]))


@pytest.mark.unit
def test_all_290_municipalities_are_drawn(kri_df: pd.DataFrame, latest_year: int) -> None:
    html = build_choropleth_map(kri_df, latest_year).get_root().render()
    assert html.count('"_kri"') == 290
