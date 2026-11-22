"""Tests for the shared UI components, chart conventions and the map filter."""

from pathlib import Path

import pandas as pd
import pytest

from app.components.charts import (
    build_distribution_histogram,
    build_grouped_bars_comparison,
    build_horizontal_contribution_bar,
    build_line_trend,
    build_radar,
    build_raw_indicator_histogram,
)
from app.ui.components import delta_color_for, indicator_delta
from src.config import COLORS, INDICATOR_COLORS

RESULTS_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "kri_results.parquet"


@pytest.mark.unit
class TestDeltaRule:
    def test_higher_is_worse_maps_to_inverse(self) -> None:
        assert delta_color_for("lower") == "inverse"

    def test_higher_is_better_maps_to_normal(self) -> None:
        assert delta_color_for("higher") == "normal"

    def test_no_comparison_is_grey(self) -> None:
        assert delta_color_for(None) == "off"
        assert delta_color_for("lower", has_delta=False) == "off"

    def test_delta_text_carries_sign_and_unit(self) -> None:
        assert indicator_delta(1.07, 1.02, nd=2) == "+0,05"
        assert indicator_delta(277, 279, nd=0, unit=" platser") == "-2 platser"
        assert indicator_delta(2.1, 1.6, nd=1, unit=" p.e.") == "+0,5 p.e."

    def test_unchanged_and_missing(self) -> None:
        assert indicator_delta(98.0, 98.0, nd=1) == "Oförändrat"
        assert indicator_delta(1.0, None, nd=2) is None
        assert indicator_delta(1.0, float("nan"), nd=2) is None


@pytest.mark.unit
class TestChartConventions:
    def _all_builders(self) -> list[dict]:
        return [
            build_distribution_histogram([-0.5, 0.0, 0.4, 0.9], 0.2),
            build_horizontal_contribution_bar({"Skuld": 0.3, "Skattekraft": -0.2}),
            build_radar([0.5, -0.5], [0.0, 0.0], ["Skuld", "Skattekraft"]),
            build_line_trend([2023, 2024], {"Ale": [0.1, 0.2], "Rikssnitt": [0.0, 0.0]}),
            build_grouped_bars_comparison(["Ale", "Bjuv"], {"Skuld": [0.1, 0.2]}),
            build_raw_indicator_histogram([1000.0, 2000.0, 3000.0], "Skuld per capita", "kr"),
        ]

    def test_every_chart_has_screen_reader_description(self) -> None:
        for opts in self._all_builders():
            assert opts["aria"]["enabled"] is True

    def test_annual_lines_are_not_smoothed(self) -> None:
        opts = build_line_trend([2023, 2024], {"Ale": [0.1, 0.2]})
        assert all(s["smooth"] is False for s in opts["series"])

    def test_contribution_colour_follows_sign(self) -> None:
        opts = build_horizontal_contribution_bar({"Upp": 0.3, "Ned": -0.2, "Noll": 0.0})
        colours = {opts["yAxis"]["data"][i]: d["itemStyle"]["color"]
                   for i, d in enumerate(opts["series"][0]["data"])}
        assert colours == {
            "Upp": COLORS["high_risk"],
            "Ned": COLORS["low_risk"],
            "Noll": COLORS["text_tertiary"],
        }

    def test_grouped_bars_use_indicator_palette(self) -> None:
        opts = build_grouped_bars_comparison(["Ale"], {"Skuld": [0.1], "Arbetslöshet": [0.2]})
        assert opts["series"][0]["itemStyle"]["color"] == INDICATOR_COLORS["debt"]
        assert opts["series"][1]["itemStyle"]["color"] == INDICATOR_COLORS["unemployment"]

    def test_histogram_denominator_is_the_plotted_count(self) -> None:
        opts = build_distribution_histogram([-0.5, 0.0, 0.4], 0.0)
        assert "var tot=3;" in opts["tooltip"]["formatter"]

    def test_no_point_decimals_in_formatters(self) -> None:
        """Tooltips format numbers through the Swedish helper, never raw toFixed()."""
        for opts in self._all_builders():
            text = str(opts)
            assert ".toFixed(2).replace" not in text


@pytest.mark.integration
def test_map_filter_keeps_scale_and_greys_out_excluded() -> None:
    if not RESULTS_PATH.exists():
        pytest.skip("kri_results.parquet not built")
    from app.components.sweden_choropleth import OUTSIDE_FILTER, build_choropleth_map

    df = pd.read_parquet(RESULTS_PATH)
    year = int(df["year"].max())
    sub = df[df["year"] == year]
    hog = set(sub[sub["risk_class"] == "Hög"]["municipality_code"].astype(str).str.zfill(4))

    full = build_choropleth_map(df, year)
    filtered = build_choropleth_map(df, year, include_codes=hog)
    if full is None or filtered is None:
        pytest.skip("GeoJSON not available")

    def _parts(m):
        cmap = next(c for c in m._children.values() if type(c).__name__ == "LinearColormap")
        gj = next(c for c in m._children.values() if type(c).__name__ == "GeoJson")
        return cmap, gj

    cmap_full, _ = _parts(full)
    cmap_filt, gj = _parts(filtered)
    assert list(cmap_full.index) == list(cmap_filt.index), "risk filter must not move the colour scale"

    feats = gj.data["features"]
    excluded = [f for f in feats if f["properties"]["_excluded"]]
    assert excluded and all(f["properties"]["Riskklass"] == OUTSIDE_FILTER for f in excluded)
    assert gj.style_function(excluded[0])["fillColor"] == COLORS["border"]
    included = [f for f in feats if not f["properties"]["_excluded"]]
    assert len(included) == len(hog)
