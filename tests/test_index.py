"""
Validation tests for KRI index computation (Task 2.3) and clustering (Task 2.2).

Covers:
  1. test_weights_sum               - Weights sum to 1.0
  2. test_zscore_properties         - z-scores have mean ≈ 0, std ≈ 1 per year
  3. test_known_municipalities      - Danderyd low, Dorotea high, Stockholm low-medium
  4. test_classification_distribution - ~25% Low, ~50% Medium, ~25% High
  5. test_temporal_stability        - year-over-year KRI correlation > 0.85
  6. test_kmeans_classification     - k-means returns only valid Swedish labels
  7. test_peer_municipalities       - peer finder returns n unique, finite-distance rows
  8. test_risk_transitions          - transitions DataFrame has correct columns and directions
  9. test_distribution_stats        - stats dict has all required keys and sane values
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Make sure src/ is importable when running from project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import WEIGHTS
from src.index_builder import KRIBuilder
from src.clustering import (
    kmeans_classification,
    get_peer_municipalities,
    compute_risk_transitions,
    compute_distribution_stats,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROCESSED_DIR = ROOT / "data" / "processed"


@pytest.fixture(scope="session")
def kri_df() -> pd.DataFrame:
    """Load pre-built KRI results (requires the pipeline to have been run first)."""
    path = PROCESSED_DIR / "kri_results.parquet"
    if not path.exists():
        pytest.skip(f"kri_results.parquet not found at {path}. Run the pipeline first.")
    return pd.read_parquet(path)


@pytest.fixture(scope="session")
def base_df() -> pd.DataFrame:
    """Load cleaned base data."""
    path = PROCESSED_DIR / "kri_base_data.parquet"
    if not path.exists():
        pytest.skip(f"kri_base_data.parquet not found at {path}. Run the pipeline first.")
    return pd.read_parquet(path)


# ---------------------------------------------------------------------------
# Task 2.1 tests
# ---------------------------------------------------------------------------

class TestWeightsSum:
    """1. Weights must sum exactly to 1.0."""

    def test_weights_sum(self):
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"

    def test_all_weights_positive(self):
        for key, w in WEIGHTS.items():
            assert w > 0, f"Weight for '{key}' is not positive: {w}"


class TestZscoreProperties:
    """2. Cross-sectional z-scores should have mean ≈ 0 and std ≈ 1 per year."""

    Z_COLS = ["z_debt", "z_unemployment", "z_dependency", "z_population", "z_tax_base"]
    MEAN_TOL = 0.05   # absolute tolerance on mean
    STD_TOL  = 0.10   # absolute tolerance on std deviation from 1

    def test_zscore_mean_near_zero(self, kri_df):
        for year in kri_df["year"].unique():
            year_df = kri_df[kri_df["year"] == year]
            for col in self.Z_COLS:
                mean_val = year_df[col].mean()
                assert abs(mean_val) < self.MEAN_TOL, (
                    f"Year {year}, {col}: mean={mean_val:.4f} (expected ≈ 0)"
                )

    def test_zscore_std_near_one(self, kri_df):
        for year in kri_df["year"].unique():
            year_df = kri_df[kri_df["year"] == year]
            for col in self.Z_COLS:
                std_val = year_df[col].std(ddof=1)
                assert abs(std_val - 1.0) < self.STD_TOL, (
                    f"Year {year}, {col}: std={std_val:.4f} (expected ≈ 1)"
                )


class TestKnownMunicipalities:
    """3. Sanity-check KRI scores against known municipalities."""

    LATEST_YEAR = 2024

    def _latest(self, kri_df, code):
        row = kri_df[
            (kri_df["municipality_code"] == code) &
            (kri_df["year"] == self.LATEST_YEAR)
        ]
        assert len(row) == 1, f"Municipality {code} not found for year {self.LATEST_YEAR}"
        return row.iloc[0]

    def test_danderyd_low_risk(self, kri_df):
        """Danderyd (0162): wealthy suburb, should be low risk."""
        row = self._latest(kri_df, "0162")
        median = kri_df[kri_df["year"] == self.LATEST_YEAR]["kri_score"].median()
        assert row["kri_score"] < median, (
            f"Danderyd KRI={row['kri_score']:.3f} is not below median={median:.3f}"
        )

    def test_dorotea_high_risk(self, kri_df):
        """Dorotea (2425): remote inland municipality, should be high risk."""
        row = self._latest(kri_df, "2425")
        p75 = kri_df[kri_df["year"] == self.LATEST_YEAR]["kri_score"].quantile(0.75)
        assert row["kri_score"] > p75, (
            f"Dorotea KRI={row['kri_score']:.3f} is not above p75={p75:.3f}"
        )

    def test_stockholm_low_medium_risk(self, kri_df):
        """Stockholm (0180): large city with strong tax base, medium or low risk."""
        row = self._latest(kri_df, "0180")
        assert row["risk_class"] in ("Låg", "Medel"), (
            f"Stockholm risk_class='{row['risk_class']}' (expected Låg or Medel)"
        )


class TestClassificationDistribution:
    """4. Risk class distribution should approximate 25% / 50% / 25%."""

    TOLERANCE = 0.08  # allow ±8 pp from target proportions

    def test_distribution_all_years(self, kri_df):
        for year in kri_df["year"].unique():
            year_df = kri_df[kri_df["year"] == year]
            total = len(year_df)
            for label, target in [("Låg", 0.25), ("Medel", 0.50), ("Hög", 0.25)]:
                pct = (year_df["risk_class"] == label).sum() / total
                assert abs(pct - target) < self.TOLERANCE, (
                    f"Year {year}: '{label}' proportion={pct:.2%} (target≈{target:.0%} ±{self.TOLERANCE:.0%})"
                )


class TestTemporalStability:
    """5. Year-over-year KRI score correlation should exceed 0.85."""

    MIN_CORRELATION = 0.85

    def test_year_over_year_correlation(self, kri_df):
        years = sorted(kri_df["year"].unique())
        for y_from, y_to in zip(years[:-1], years[1:]):
            df_from = kri_df[kri_df["year"] == y_from][["municipality_code", "kri_score"]].rename(
                columns={"kri_score": "score_from"}
            )
            df_to = kri_df[kri_df["year"] == y_to][["municipality_code", "kri_score"]].rename(
                columns={"kri_score": "score_to"}
            )
            merged = df_from.merge(df_to, on="municipality_code", how="inner").dropna()
            corr = merged["score_from"].corr(merged["score_to"])
            assert corr > self.MIN_CORRELATION, (
                f"Correlation {y_from}->{y_to}: {corr:.3f} < {self.MIN_CORRELATION}"
            )


# ---------------------------------------------------------------------------
# Task 2.2 tests
# ---------------------------------------------------------------------------

class TestKmeansClassification:
    """6. k-means classification returns valid risk labels for all municipalities."""

    VALID_LABELS = {"Låg", "Medel", "Hög"}

    def test_returns_valid_labels(self, kri_df):
        result = kmeans_classification(kri_df, k=3)
        assert "kmeans_risk_class" in result.columns
        non_empty = result[result["kmeans_risk_class"] != ""]["kmeans_risk_class"]
        assert set(non_empty.unique()).issubset(self.VALID_LABELS), (
            f"Unexpected k-means labels: {set(non_empty.unique()) - self.VALID_LABELS}"
        )

    def test_all_municipalities_labelled(self, kri_df):
        result = kmeans_classification(kri_df, k=3)
        missing = result[result["kmeans_risk_class"] == ""]
        assert len(missing) == 0, f"{len(missing)} rows have empty kmeans_risk_class"

    def test_roughly_balanced_distribution(self, kri_df):
        result = kmeans_classification(kri_df, k=3)
        latest = result[result["year"] == result["year"].max()]
        total = len(latest)
        for label in self.VALID_LABELS:
            pct = (latest["kmeans_risk_class"] == label).sum() / total
            assert pct > 0.10, f"k-means class '{label}' has only {pct:.1%} in latest year"


class TestPeerMunicipalities:
    """7. Peer finder returns correct number of unique, finite-distance municipalities."""

    def test_returns_n_peers(self, kri_df):
        peers = get_peer_municipalities("0180", kri_df, n=10)
        assert len(peers) == 10, f"Expected 10 peers, got {len(peers)}"

    def test_reference_not_in_peers(self, kri_df):
        peers = get_peer_municipalities("0180", kri_df, n=10)
        assert "0180" not in peers["municipality_code"].values, (
            "Reference municipality should not appear in its own peer group"
        )

    def test_distances_finite_and_positive(self, kri_df):
        peers = get_peer_municipalities("0162", kri_df, n=10)
        assert peers["distance"].notna().all(), "Some distances are NaN"
        assert (peers["distance"] > 0).all(), "Some distances are zero or negative"

    def test_sorted_ascending(self, kri_df):
        peers = get_peer_municipalities("2425", kri_df, n=10)
        assert peers["distance"].is_monotonic_increasing, (
            "Peer municipalities are not sorted by distance (ascending)"
        )

    def test_invalid_code_raises(self, kri_df):
        with pytest.raises(ValueError):
            get_peer_municipalities("XXXX", kri_df, n=10)


class TestRiskTransitions:
    """8. Risk transition DataFrame has correct schema and logical content."""

    EXPECTED_COLS = {
        "municipality_code", "municipality_name",
        "year_from", "year_to",
        "risk_class_from", "risk_class_to",
        "transition_direction", "significant",
    }

    def test_columns_present(self, kri_df):
        df = compute_risk_transitions(kri_df)
        assert self.EXPECTED_COLS.issubset(df.columns), (
            f"Missing columns: {self.EXPECTED_COLS - set(df.columns)}"
        )

    def test_direction_values(self, kri_df):
        df = compute_risk_transitions(kri_df)
        assert set(df["transition_direction"].unique()).issubset(
            {"same", "improved", "deteriorated"}
        )

    def test_significant_is_boolean(self, kri_df):
        df = compute_risk_transitions(kri_df)
        assert df["significant"].dtype == bool

    def test_significant_only_for_extreme_jumps(self, kri_df):
        df = compute_risk_transitions(kri_df)
        sig = df[df["significant"]]
        for _, row in sig.iterrows():
            pair = (row["risk_class_from"], row["risk_class_to"])
            assert pair in [("Låg", "Hög"), ("Hög", "Låg")], (
                f"Unexpected significant transition: {pair}"
            )

    def test_year_ordering(self, kri_df):
        df = compute_risk_transitions(kri_df)
        assert (df["year_to"] > df["year_from"]).all(), "year_to must be greater than year_from"


class TestDistributionStats:
    """9. Distribution stats dict has all required keys and numerically sane values."""

    REQUIRED_KEYS = {"year", "n", "mean", "median", "std", "skewness", "kurt",
                     "p10", "p25", "p50", "p75", "p90", "min", "max"}

    def test_all_keys_present(self, kri_df):
        stats = compute_distribution_stats(kri_df, year=2024)
        assert self.REQUIRED_KEYS == set(stats.keys()), (
            f"Missing keys: {self.REQUIRED_KEYS - set(stats.keys())}"
        )

    def test_n_is_290(self, kri_df):
        stats = compute_distribution_stats(kri_df, year=2024)
        assert stats["n"] == 290, f"Expected 290 municipalities, got {stats['n']}"

    def test_percentile_ordering(self, kri_df):
        stats = compute_distribution_stats(kri_df, year=2024)
        assert stats["p10"] <= stats["p25"] <= stats["p50"] <= stats["p75"] <= stats["p90"], (
            "Percentiles are not in ascending order"
        )

    def test_min_max_bounds(self, kri_df):
        stats = compute_distribution_stats(kri_df, year=2024)
        assert stats["min"] <= stats["p10"]
        assert stats["max"] >= stats["p90"]

    def test_std_positive(self, kri_df):
        stats = compute_distribution_stats(kri_df, year=2024)
        assert stats["std"] > 0, "Standard deviation should be positive"

    def test_invalid_year_raises(self, kri_df):
        with pytest.raises(ValueError):
            compute_distribution_stats(kri_df, year=1900)


@pytest.mark.unit
class TestReportClaims:
    """Guards factual claims in the generated PDF against the data.

    Two claims were wrong before this was added: that the share of high-risk
    municipalities rose during the pandemic (impossible, the classes are
    quartiles, so the share is fixed at 25% by construction), and that debt and
    unemployment explain 50% of KRI variance (that is the sum of their weights;
    the actual variance share is about 40%).
    """

    def test_risk_class_share_is_fixed_by_construction(self, kri_df):
        """Any narrative about the share of Hög risk changing over time is false."""
        shares = kri_df.groupby("year")["risk_class"].apply(lambda s: (s == "Hög").mean())
        assert shares.max() - shares.min() < 0.01, (
            "Quartile classification must hold the share constant; a varying share "
            "would mean classify() no longer uses per-year quantiles."
        )

    def test_report_makes_no_claim_about_a_changing_high_risk_share(self):
        src = (Path(__file__).resolve().parent.parent / "src" / "report_gen.py").read_text(
            encoding="utf-8"
        )
        for banned in ("högrisk ökade", "andelen kommuner med högrisk ökade"):
            assert banned not in src, f"report claims a fixed quantity changed: {banned!r}"

    def test_report_does_not_confuse_weight_with_variance_explained(self):
        src = (Path(__file__).resolve().parent.parent / "src" / "report_gen.py").read_text(
            encoding="utf-8"
        )
        assert "50 % av variansen" not in src

    def test_debt_and_unemployment_variance_share(self, kri_df):
        """The corrected figure the report now quotes must match the data."""
        latest = kri_df[kri_df["year"] == kri_df["year"].max()]
        cols = [c for c in kri_df.columns if c.startswith("contribution_")]
        cov = latest[cols].cov()
        total = latest["kri_score"].var()
        share = (
            cov["contribution_debt"].sum() + cov["contribution_unemployment"].sum()
        ) / total
        assert 0.30 < share < 0.45, f"variance share moved to {share:.1%}; update the report"


@pytest.mark.unit
def test_swedish_ui_check_passes():
    """The project's own Swedish-copy check must stay green.

    It was failing before the weight-sensitivity work landed; keeping a test on
    it stops the 9 violations from quietly coming back.
    """
    import subprocess

    root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "scripts/verify_swedish_ui.py"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
