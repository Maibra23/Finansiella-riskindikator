"""Tests for RiskScale and the chart builders that consume it.

Regression guard for the defect where charts hardcoded the standard-normal
quartiles (±0.6745) while risk_class came from empirical percentiles, putting
111 of 290 municipalities in a different zone in the charts than in the tables.
"""

from pathlib import Path

import pandas as pd
import pytest

from app.components.charts import (
    RADAR_MIN_EXTENT,
    _bin_color,
    build_distribution_histogram,
    build_line_trend,
    build_radar,
)
from src.config import COLORS
from src.risk_scale import FALLBACK_CUTOFF, RiskScale

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
class TestRiskScale:
    def test_bounds_straddle_zero(self, kri_df: pd.DataFrame) -> None:
        for year in sorted(kri_df["year"].unique()):
            scale = RiskScale.for_year(kri_df, int(year))
            assert scale.low < 0.0 < scale.high

    def test_extent_contains_all_scores(self, kri_df: pd.DataFrame) -> None:
        for year in sorted(kri_df["year"].unique()):
            scores = kri_df.loc[kri_df["year"] == year, "kri_score"]
            scale = RiskScale.for_year(kri_df, int(year))
            assert scale.extent >= scores.abs().max()

    def test_bounds_are_the_empirical_quartiles(self, kri_df: pd.DataFrame, latest_year: int) -> None:
        scores = kri_df.loc[kri_df["year"] == latest_year, "kri_score"]
        scale = RiskScale.for_year(kri_df, latest_year)
        assert scale.low == pytest.approx(scores.quantile(0.25))
        assert scale.high == pytest.approx(scores.quantile(0.75))

    def test_classify_reproduces_stored_risk_class(self, kri_df: pd.DataFrame) -> None:
        """The whole point: charts and tables must never disagree again."""
        for year in sorted(kri_df["year"].unique()):
            sub = kri_df[kri_df["year"] == year]
            scale = RiskScale.for_year(kri_df, int(year))
            derived = sub["kri_score"].map(scale.classify)
            mismatches = int((derived != sub["risk_class"]).sum())
            assert mismatches == 0, f"{mismatches} mismatches in {year}"

    def test_empty_input_falls_back_instead_of_crashing(self) -> None:
        scale = RiskScale.from_scores([])
        assert scale.low == -FALLBACK_CUTOFF
        assert scale.high == FALLBACK_CUTOFF

    def test_degenerate_input_falls_back(self) -> None:
        assert RiskScale.from_scores([0.4]).low < 0.0 < RiskScale.from_scores([0.4]).high
        assert RiskScale.from_scores([0.0] * 10).low < 0.0

    def test_is_immutable(self, kri_df: pd.DataFrame, latest_year: int) -> None:
        scale = RiskScale.for_year(kri_df, latest_year)
        with pytest.raises(Exception):
            scale.low = 0.5  # type: ignore[misc]

    def test_rejects_bounds_that_do_not_straddle_zero(self) -> None:
        with pytest.raises(ValueError):
            RiskScale(low=0.1, high=0.5, extent=2.0)

    def test_rejects_extent_narrower_than_bounds(self) -> None:
        with pytest.raises(ValueError):
            RiskScale(low=-0.3, high=0.4, extent=0.2)

    def test_pooled_covers_every_year(self, kri_df: pd.DataFrame) -> None:
        pooled = RiskScale.pooled(kri_df)
        assert pooled.extent >= kri_df["kri_score"].abs().max()


@pytest.mark.unit
class TestChartsUseTheScale:
    def test_bin_color_follows_scale_not_normal_quartiles(self, kri_df: pd.DataFrame, latest_year: int) -> None:
        scale = RiskScale.for_year(kri_df, latest_year)
        # 0.4 is above the empirical 75th percentile but below the old ±0.6745.
        assert scale.high < 0.4 < 0.6745
        assert _bin_color(0.4, scale) == COLORS["high_risk"]
        assert _bin_color(-0.4, scale) == COLORS["low_risk"]
        assert _bin_color(0.0, scale) == COLORS["medium_risk"]

    def test_histogram_axis_spans_the_scale(self, kri_df: pd.DataFrame, latest_year: int) -> None:
        scores = kri_df.loc[kri_df["year"] == latest_year, "kri_score"].tolist()
        scale = RiskScale.for_year(kri_df, latest_year)
        opts = build_distribution_histogram(scores, 0.0, scale)
        cats = [float(c) for c in opts["xAxis"]["data"]]
        assert cats[0] == pytest.approx(-scale.extent)
        assert max(cats) < scale.extent

    def test_histogram_bar_count_matches_input(self, kri_df: pd.DataFrame, latest_year: int) -> None:
        scores = kri_df.loc[kri_df["year"] == latest_year, "kri_score"].tolist()
        opts = build_distribution_histogram(scores, 0.0, RiskScale.for_year(kri_df, latest_year))
        assert sum(b["value"] for b in opts["series"][0]["data"]) == len(scores)

    def test_histogram_zone_counts_match_risk_class(self, kri_df: pd.DataFrame, latest_year: int) -> None:
        """Bars painted red must total the same as the 'Hög risk' KPI card."""
        sub = kri_df[kri_df["year"] == latest_year]
        scale = RiskScale.for_year(kri_df, latest_year)
        opts = build_distribution_histogram(sub["kri_score"].tolist(), 0.0, scale)
        red = sum(
            b["value"] for b in opts["series"][0]["data"]
            if b["itemStyle"]["color"] == COLORS["high_risk"]
        )
        labelled_high = int((sub["risk_class"] == "Hög").sum())
        # Binning puts the boundary bin wholly in one zone, so allow one bin of slack.
        assert abs(red - labelled_high) <= len(sub) / 24

    def test_histogram_categories_are_unique(self, kri_df: pd.DataFrame, latest_year: int) -> None:
        scores = kri_df.loc[kri_df["year"] == latest_year, "kri_score"].tolist()
        cats = build_distribution_histogram(
            scores, 0.0, RiskScale.for_year(kri_df, latest_year)
        )["xAxis"]["data"]
        assert len(set(cats)) == len(cats)

    def test_no_chart_hardcodes_the_normal_quartile(self) -> None:
        src = (Path(__file__).resolve().parent.parent / "app" / "components" / "charts.py").read_text(
            encoding="utf-8"
        )
        assert "0.6745" not in src, "charts must derive risk zones from RiskScale"

    def test_radar_frame_grows_to_fit_outliers(self) -> None:
        """z_tax_base reaches -7.5; a fixed ±2.5 frame clipped 39/290 in 2024."""
        opts = build_radar([0.1, -7.5], [0.0, 0.0], ["A", "B"])
        assert opts["radar"]["indicator"][0]["max"] >= 7.5

    def test_radar_frame_is_stable_for_typical_values(self) -> None:
        opts = build_radar([0.4, -1.1], [0.0, 0.0], ["A", "B"])
        assert opts["radar"]["indicator"][0]["max"] == RADAR_MIN_EXTENT

    def test_no_municipality_is_clipped_by_the_radar(self, kri_df: pd.DataFrame) -> None:
        z_cols = [c for c in kri_df.columns if c.startswith("z_")]
        for _, row in kri_df.iterrows():
            vals = [float(row[c]) for c in z_cols]
            axis_max = build_radar(vals, [0.0] * len(vals), z_cols)["radar"]["indicator"][0]["max"]
            assert axis_max >= max(abs(v) for v in vals)

    def test_trend_bands_sit_on_the_scale(self, kri_df: pd.DataFrame) -> None:
        scale = RiskScale.pooled(kri_df)
        years = sorted(kri_df["year"].unique().tolist())
        series = {"Rikssnitt": [0.0] * len(years)}
        opts = build_line_trend(years, series, scale)
        bands = opts["series"][0]["markArea"]["data"]
        assert bands[0][1]["yAxis"] == pytest.approx(scale.low)
        assert bands[2][0]["yAxis"] == pytest.approx(scale.high)

    def test_radar_axes_stay_symmetric(self) -> None:
        opts = build_radar([0.1, 0.2], [0.0, 0.0], ["A", "B"])
        for axis in opts["radar"]["indicator"]:
            assert axis["min"] == -axis["max"]
