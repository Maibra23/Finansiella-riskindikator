"""
Data-reality tests for the debt variable.

Unlike test_index.py, which checks internal consistency, these tests anchor the
debt figures to SCB's published totals so a wrong balance post cannot slip by.

Debt is the municipality's total borrowing: the posts in config.BORROWING_POSTS.

Covers:
  1. clean_balance_sheet sums exactly the borrowing posts and nothing else
  2. a post SCB had not yet introduced counts as zero; any other gap raises
  3. clean_balance_sheet raises instead of falling back to other posts
  4. cached SCB data: national borrowing matches SCB's published total
  5. cached SCB data: sum over municipalities equals SCB's own "Riket" row
  6. processed data: debt per capita reconstructs the national total
  7. Gotland is not rescaled (SCB already reports the municipal part alone)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import BORROWING_POSTS, SCB_NATIONAL_BORROWING_BSEK
from src.data_cleaner import DataCleaner

CACHE_DIR = ROOT / "data" / "cache"
PROCESSED_DIR = ROOT / "data" / "processed"
TOLERANCE = 0.01  # 1 %


def _load(path: Path) -> pd.DataFrame:
    if not path.exists():
        pytest.skip(f"{path.name} not found. Run the pipeline first.")
    return pd.read_parquet(path)


def _synthetic_balance_sheet(posts, year=2021):
    return pd.DataFrame([
        {"municipality_code": "0180", "municipality_name": "Stockholm",
         "balanspost": post, "year": year, "value": value}
        for post, value in posts.items()
    ])


def _synthetic_population(total=1000, year=2021):
    return pd.DataFrame([{"municipality_code": "0180", "municipality_name": "Stockholm",
                          "year": year, "value": total}])


def _all_borrowing(value=100.0):
    return {post: value for post in BORROWING_POSTS}


@pytest.mark.unit
class TestCleanBalanceSheet:
    """clean_balance_sheet must sum the borrowing posts and nothing else."""

    def test_sums_borrowing_posts_only(self, tmp_path):
        posts = _all_borrowing(100.0) | {"087": 5_000, "088": 7_000, "089": 9_000, "050": 9_000, "100": 90_000}
        out = DataCleaner(processed_dir=tmp_path).clean_balance_sheet(
            _synthetic_balance_sheet(posts), _synthetic_population())
        # 7 posts x 100 tkr / 1000 inhabitants = 700 kr per capita
        assert out["debt_per_capita"].iloc[0] == pytest.approx(100.0 * len(BORROWING_POSTS))

    def test_post_before_introduction_counts_as_zero(self, tmp_path):
        posts = _all_borrowing(100.0)
        posts["136"] = np.nan  # bonds had no separate post before 2020
        out = DataCleaner(processed_dir=tmp_path).clean_balance_sheet(
            _synthetic_balance_sheet(posts, year=2015), _synthetic_population(year=2015))
        assert out["debt_per_capita"].iloc[0] == pytest.approx(100.0 * (len(BORROWING_POSTS) - 1))

    def test_gap_after_introduction_raises(self, tmp_path):
        posts = _all_borrowing(100.0)
        posts["081"] = np.nan
        with pytest.raises(ValueError, match="Missing borrowing values"):
            DataCleaner(processed_dir=tmp_path).clean_balance_sheet(
                _synthetic_balance_sheet(posts), _synthetic_population())

    def test_missing_post_raises(self, tmp_path):
        bs = _synthetic_balance_sheet({"089": 500, "050": 9_000, "100": 90_000})
        with pytest.raises(ValueError, match="Borrowing posts"):
            DataCleaner(processed_dir=tmp_path).clean_balance_sheet(bs, _synthetic_population())


def _borrowing_by_region(balance_sheet: pd.DataFrame) -> pd.Series:
    d = balance_sheet[balance_sheet["balanspost"].isin(BORROWING_POSTS)]
    return d.groupby(["municipality_code", "year"])["value"].sum(min_count=1)


@pytest.mark.unit
class TestNationalDebtTotal:
    """National totals must match SCB's published figures."""

    @pytest.fixture(scope="class")
    def borrowing(self):
        return _borrowing_by_region(_load(CACHE_DIR / "balance_sheet.parquet"))

    @pytest.mark.parametrize("year,expected_bsek", SCB_NATIONAL_BORROWING_BSEK.items())
    def test_cached_sum_matches_published_total(self, borrowing, year, expected_bsek):
        b = borrowing.xs(year, level="year")
        total_bsek = b[b.index.str.len() == 4].sum() / 1e6  # tkr -> billion SEK
        assert total_bsek == pytest.approx(expected_bsek, rel=TOLERANCE)

    def test_municipal_sum_equals_riket_row(self, borrowing):
        codes = borrowing.index.get_level_values("municipality_code")
        munis = borrowing[codes.str.len() == 4].groupby(level="year").sum()
        riket = borrowing.xs("00", level="municipality_code")
        pd.testing.assert_series_equal(munis.sort_index(), riket.sort_index(),
                                       check_names=False, check_dtype=False, rtol=1e-6)

    @pytest.mark.parametrize("year,expected_bsek", SCB_NATIONAL_BORROWING_BSEK.items())
    def test_processed_per_capita_reconstructs_total(self, year, expected_bsek):
        base = _load(PROCESSED_DIR / "kri_base_data.parquet")
        pop = _load(CACHE_DIR / "population.parquet")
        pop = pop[pop["year"] == year].groupby("municipality_code")["value"].sum()
        b = base[base["year"] == year].set_index("municipality_code")["debt_per_capita"]
        total_bsek = (b * pop.reindex(b.index)).sum() / 1e9
        assert total_bsek == pytest.approx(expected_bsek, rel=TOLERANCE)

    def test_gotland_is_not_rescaled(self, borrowing):
        """SCB's municipal table already holds only Gotland's municipal part."""
        base = _load(PROCESSED_DIR / "kri_base_data.parquet")
        pop = _load(CACHE_DIR / "population.parquet")
        year = int(base["year"].max())
        pop_g = pop[(pop["year"] == year) & (pop["municipality_code"] == "0980")]["value"].sum()
        expected = borrowing.loc[("0980", year)] * 1000 / pop_g
        got = base[(base["year"] == year) & (base["municipality_code"] == "0980")]["debt_per_capita"].iloc[0]
        assert got == pytest.approx(expected, rel=1e-9)
