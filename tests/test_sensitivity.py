"""Tests for the weight-sensitivity layer.

The layer exists to answer "your weights are subjective" with a measurement
rather than an argument.  Two properties make it trustworthy, and both are
asserted here:

  1. It is *additive*.  It never recomputes kri_score, risk_class or rank, it
     only reports how stable those already-published values are.
  2. It is *deterministic*.  A band that moves between pipeline runs is worse
     than no band at all, because a reader who re-runs and sees different
     numbers stops trusting the whole dashboard.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import SENSITIVITY
from src.sensitivity import (
    SENSITIVITY_COLUMNS,
    SensitivityConfig,
    compute_sensitivity,
    sample_weights,
)

RESULTS_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "kri_results.parquet"


@pytest.fixture(scope="module")
def kri_df() -> pd.DataFrame:
    if not RESULTS_PATH.exists():
        pytest.skip("kri_results.parquet not built")
    return pd.read_parquet(RESULTS_PATH)


@pytest.fixture(scope="module")
def sens(kri_df: pd.DataFrame) -> pd.DataFrame:
    return compute_sensitivity(kri_df)


@pytest.fixture(scope="module")
def latest_year(kri_df: pd.DataFrame) -> int:
    return int(kri_df["year"].max())


@pytest.mark.unit
class TestSampling:
    def test_weights_sum_to_one(self) -> None:
        W = sample_weights(SensitivityConfig())
        assert np.allclose(W.sum(axis=1), 1.0)

    def test_weights_are_non_negative(self) -> None:
        assert (sample_weights(SensitivityConfig()) >= 0).all()

    def test_shape_matches_config(self) -> None:
        cfg = SensitivityConfig(n_draws=37)
        assert sample_weights(cfg).shape == (37, 5)

    def test_draws_are_centred_on_the_nominal_weights(self) -> None:
        """Perturbation must be symmetric, it may not bias the index."""
        W = sample_weights(SensitivityConfig(n_draws=20000))
        assert np.allclose(W.mean(axis=0), SensitivityConfig().nominal, atol=0.005)

    def test_no_weight_ever_moves_more_than_delta(self) -> None:
        """The claim quoted in the UI must hold exactly, not approximately."""
        cfg = SensitivityConfig()
        W = sample_weights(cfg)
        assert np.abs(W - cfg.nominal).max() <= cfg.delta + 1e-12

    def test_rejection_does_not_bias_the_draws(self) -> None:
        """Rejecting out-of-bound vectors must not shift the centre."""
        cfg = SensitivityConfig(n_draws=20000)
        assert np.allclose(sample_weights(cfg).mean(axis=0), cfg.nominal, atol=0.005)

    def test_sampling_is_deterministic(self) -> None:
        assert np.array_equal(sample_weights(SensitivityConfig()), sample_weights(SensitivityConfig()))

    def test_different_seed_gives_different_draws(self) -> None:
        a = sample_weights(SensitivityConfig(seed=1))
        b = sample_weights(SensitivityConfig(seed=2))
        assert not np.array_equal(a, b)


@pytest.mark.unit
class TestOutputShape:
    def test_one_row_per_municipality_year(self, kri_df: pd.DataFrame, sens: pd.DataFrame) -> None:
        assert len(sens) == len(kri_df)
        assert len(sens) == 290 * kri_df["year"].nunique()

    def test_has_exactly_the_declared_columns(self, sens: pd.DataFrame) -> None:
        assert list(sens.columns) == SENSITIVITY_COLUMNS

    def test_joins_cleanly_on_code_and_year(self, kri_df: pd.DataFrame, sens: pd.DataFrame) -> None:
        merged = kri_df.merge(sens, on=["municipality_code", "year"], how="left", indicator=True)
        assert (merged["_merge"] == "both").all()
        assert len(merged) == len(kri_df)

    def test_no_missing_values(self, sens: pd.DataFrame) -> None:
        assert not sens.isna().any().any()


@pytest.mark.unit
class TestAdditivity:
    """The layer must not touch what it measures."""

    def test_input_frame_is_not_mutated(self, kri_df: pd.DataFrame) -> None:
        before = kri_df.copy(deep=True)
        compute_sensitivity(kri_df)
        pd.testing.assert_frame_equal(kri_df, before)

    def test_does_not_republish_score_class_or_rank(self, sens: pd.DataFrame) -> None:
        """Returning these would let the layer silently override the index."""
        for col in ("kri_score", "risk_class", "rank"):
            assert col not in sens.columns

    def test_published_parquet_schema_is_untouched(self, kri_df: pd.DataFrame) -> None:
        """Guards the promise that deleting the layer restores today's app."""
        expected = {
            "municipality_code", "municipality_name", "year", "kri_score",
            "z_debt", "z_unemployment", "z_dependency", "z_population", "z_tax_base",
            "contribution_debt", "contribution_unemployment", "contribution_dependency",
            "contribution_population", "contribution_tax_base",
            "risk_class", "rank", "debt_per_capita", "unemployment",
            "dependency_ratio", "population_growth", "tax_base_relative",
        }
        assert set(kri_df.columns) == expected


@pytest.mark.unit
class TestBounds:
    def test_rank_percentiles_are_ordered(self, sens: pd.DataFrame) -> None:
        assert (sens["rank_p05"] <= sens["rank_median"]).all()
        assert (sens["rank_median"] <= sens["rank_p95"]).all()

    def test_ranks_are_within_the_population(self, sens: pd.DataFrame) -> None:
        assert sens["rank_p05"].min() >= 1
        assert sens["rank_p95"].max() <= 290

    def test_stability_is_a_proportion(self, sens: pd.DataFrame) -> None:
        assert sens["class_stability"].between(0.0, 1.0).all()

    def test_is_robust_matches_the_threshold(self, sens: pd.DataFrame) -> None:
        expected = sens["class_stability"] >= SENSITIVITY["robust_threshold"]
        assert (sens["is_robust"] == expected).all()

    def test_modal_class_is_a_real_risk_class(self, sens: pd.DataFrame) -> None:
        assert set(sens["modal_class"].unique()) <= {"Låg", "Medel", "Hög"}


@pytest.mark.unit
class TestDeterminism:
    def test_two_runs_are_identical(self, kri_df: pd.DataFrame) -> None:
        pd.testing.assert_frame_equal(compute_sensitivity(kri_df), compute_sensitivity(kri_df))

    def test_row_order_is_stable(self, kri_df: pd.DataFrame, sens: pd.DataFrame) -> None:
        shuffled = kri_df.sample(frac=1.0, random_state=7).reset_index(drop=True)
        pd.testing.assert_frame_equal(compute_sensitivity(shuffled), sens)


@pytest.mark.unit
class TestSubstance:
    """The measurement has to say something true about this data."""

    def test_the_published_index_survives_its_own_sensitivity_check(
        self, kri_df: pd.DataFrame, sens: pd.DataFrame, latest_year: int
    ) -> None:
        """If the modal class disagreed often, the index itself would be in doubt."""
        merged = kri_df.merge(sens, on=["municipality_code", "year"])
        m = merged[merged["year"] == latest_year]
        disagreements = int((m["modal_class"] != m["risk_class"]).sum())
        assert disagreements <= 5, f"{disagreements}/290 modal-class disagreements"

    def test_most_municipalities_are_robust(self, sens: pd.DataFrame, latest_year: int) -> None:
        share = sens.loc[sens["year"] == latest_year, "is_robust"].mean()
        assert 0.6 < share < 0.98, f"robust share {share:.2f}, threshold is miscalibrated"

    def test_it_actually_discriminates(self, sens: pd.DataFrame, latest_year: int) -> None:
        """A band that flags nobody, or everybody, is decoration."""
        fragile = (~sens.loc[sens["year"] == latest_year, "is_robust"]).sum()
        assert 5 <= fragile <= 120

    def test_instability_concentrates_at_class_boundaries(
        self, kri_df: pd.DataFrame, sens: pd.DataFrame, latest_year: int
    ) -> None:
        """Class changes need a cut point nearby: the extremes and the middle of the
        Medel class are pinned by the data; kommuner within 10 ranks of a quartile
        boundary are the ones the weights can move."""
        merged = kri_df.merge(sens, on=["municipality_code", "year"])
        m = merged[merged["year"] == latest_year]
        upper = int((m["risk_class"] == "Hög").sum())        # last Hög rank
        lower = len(m) - int((m["risk_class"] == "Låg").sum())  # last Medel rank
        near = m[(m["rank"].sub(upper).abs() <= 10) | (m["rank"].sub(lower).abs() <= 10)]
        top10 = m.nsmallest(10, "rank")["class_stability"].mean()
        middle = m[m["rank"].between(120, 170)]["class_stability"].mean()
        boundary = near["class_stability"].mean()
        assert top10 > boundary
        assert middle > boundary


@pytest.mark.unit
class TestConfigContract:
    def test_config_exposes_the_documented_parameters(self) -> None:
        assert set(SENSITIVITY) == {"n_draws", "delta", "robust_threshold", "seed"}

    def test_defaults_come_from_config(self) -> None:
        cfg = SensitivityConfig()
        assert cfg.n_draws == SENSITIVITY["n_draws"]
        assert cfg.delta == SENSITIVITY["delta"]
        assert cfg.seed == SENSITIVITY["seed"]

    def test_config_is_immutable(self) -> None:
        with pytest.raises(Exception):
            SensitivityConfig().delta = 0.2  # type: ignore[misc]

    def test_rejects_a_delta_that_would_flip_a_weight_negative(self) -> None:
        with pytest.raises(ValueError):
            SensitivityConfig(delta=0.5)

    def test_rejects_a_nonsensical_draw_count(self) -> None:
        with pytest.raises(ValueError):
            SensitivityConfig(n_draws=0)


@pytest.mark.integration
class TestReportIntegration:
    """The exported PDF must carry the same caveats the screen does."""

    def test_risk_table_gains_a_column_only_when_data_is_supplied(self) -> None:
        from src.report_gen import _risk_table, _styles

        styles = _styles()
        rows = [(1, "Högsby", 1.17, "Hög"), (2, "Filipstad", 1.09, "Hög")]
        assert len(_risk_table(rows, styles)._argW) == 4
        assert len(_risk_table(rows, styles, uncertainty={1: "1-2", 2: "2-4"})._argW) == 5

    def test_uncertainty_map_covers_every_rank(self, kri_df: pd.DataFrame, latest_year: int) -> None:
        from src.report_gen import _load_sensitivity, _uncertainty_by_rank

        sens = _load_sensitivity()
        if sens is None:
            pytest.skip("sensitivity layer not built")
        mapping = _uncertainty_by_rank(kri_df, sens, latest_year)
        assert mapping is not None
        assert len(mapping) == 290
        assert set(mapping) == set(range(1, 291))

    def test_uncertainty_map_is_none_without_the_layer(
        self, kri_df: pd.DataFrame, latest_year: int
    ) -> None:
        from src.report_gen import _uncertainty_by_rank

        assert _uncertainty_by_rank(kri_df, None, latest_year) is None

    def test_generated_pdf_documents_the_method(self, tmp_path) -> None:
        from src.report_gen import _load_sensitivity, generate_report

        if _load_sensitivity() is None:
            pytest.skip("sensitivity layer not built")
        pytest.importorskip("pypdf")
        from pypdf import PdfReader

        out = tmp_path / "kri.pdf"
        generate_report(output_path=out)
        text = "\n".join(page.extract_text() for page in PdfReader(str(out)).pages)

        assert "Viktkänslighet" in text
        assert "Osäkerhet" in text
        # The rejected alternative belongs in the report, not only in the repo.
        assert "principalkomponent" in text
        # Swedish spelling, not an ASCII fallback.
        assert "gransfall" not in text


@pytest.mark.unit
class TestPagesDegradeWithoutTheLayer:
    """Deleting kri_sensitivity.parquet must restore the previous dashboard."""

    @pytest.mark.parametrize(
        "page", ["riksoversikt.py", "kommunanalys.py", "kallor.py"]
    )
    def test_every_consumer_is_guarded(self, page: str) -> None:
        src = (Path(__file__).resolve().parent.parent / "app" / "pages" / page).read_text(
            encoding="utf-8"
        )
        assert "_load_sensitivity" in src, f"{page} does not load the layer"
        assert "sens_df is not None" in src or "sens_row is not None" in src, (
            f"{page} uses the layer without a None guard"
        )

    def test_table_html_omits_the_column_without_data(self) -> None:
        """The header must disappear too, not render above empty cells."""
        src = (
            Path(__file__).resolve().parent.parent / "app" / "pages" / "riksoversikt.py"
        ).read_text(encoding="utf-8")
        assert 'show_uncertainty = "is_robust" in df.columns' in src
        assert "if show_uncertainty:" in src
