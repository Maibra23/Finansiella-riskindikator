"""
Data-reality tests for the debt variable.

Unlike test_index.py, which checks internal consistency, these tests anchor the
debt figures to SCB's published totals so a wrong balance post cannot slip by.

Covers:
  1. clean_balance_sheet keeps only post 089 (long-term debt)
  2. clean_balance_sheet raises instead of falling back to other posts
  3. cached SCB data: national sum of post 089 matches SCB's published total
  4. cached SCB data: sum over municipalities equals SCB's own "Riket" row
  5. processed data: debt per capita reconstructs the published national total
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import BALANCE_SHEET_POSTS, SCB_NATIONAL_LONG_TERM_DEBT_BSEK
from src.data_cleaner import DataCleaner

CACHE_DIR = ROOT / "data" / "cache"
PROCESSED_DIR = ROOT / "data" / "processed"
DEBT_CODE = BALANCE_SHEET_POSTS["long_term_liabilities"]
TOLERANCE = 0.01  # 1 %


def _load(path: Path) -> pd.DataFrame:
    if not path.exists():
        pytest.skip(f"{path.name} not found. Run the pipeline first.")
    return pd.read_parquet(path)


def _synthetic_balance_sheet(posts):
    rows = []
    for post, value in posts.items():
        rows.append({"municipality_code": "0180", "municipality_name": "Stockholm",
                     "balanspost": post, "year": 2021, "value": value})
    return pd.DataFrame(rows)


def _synthetic_population(total=1000):
    return pd.DataFrame([{"municipality_code": "0180", "municipality_name": "Stockholm",
                          "year": 2021, "value": total}])


class TestCleanBalanceSheet:
    """clean_balance_sheet must use post 089 and nothing else."""

    def test_uses_only_long_term_debt(self, tmp_path):
        bs = _synthetic_balance_sheet({"089": 500, "088": 200, "050": 9_000, "100": 90_000})
        out = DataCleaner(processed_dir=tmp_path).clean_balance_sheet(bs, _synthetic_population())
        # 500 tkr / 1000 inhabitants = 500 kr per capita
        assert out["debt_per_capita"].iloc[0] == pytest.approx(500.0)

    def test_missing_debt_post_raises(self, tmp_path):
        bs = _synthetic_balance_sheet({"050": 9_000, "100": 90_000})
        with pytest.raises(ValueError, match="089"):
            DataCleaner(processed_dir=tmp_path).clean_balance_sheet(bs, _synthetic_population())


class TestNationalDebtTotal:
    """National totals must match SCB's published long-term debt."""

    @pytest.fixture(scope="class")
    def balance_sheet(self):
        return _load(CACHE_DIR / "balance_sheet.parquet")

    @pytest.mark.parametrize("year,expected_bsek", SCB_NATIONAL_LONG_TERM_DEBT_BSEK.items())
    def test_cached_sum_matches_published_total(self, balance_sheet, year, expected_bsek):
        d = balance_sheet
        mask = (d["balanspost"] == DEBT_CODE) & (d["year"] == year) & (d["municipality_code"].str.len() == 4)
        total_bsek = d.loc[mask, "value"].sum() / 1e6  # tkr -> billion SEK
        assert total_bsek == pytest.approx(expected_bsek, rel=TOLERANCE)

    def test_municipal_sum_equals_riket_row(self, balance_sheet):
        d = balance_sheet[balance_sheet["balanspost"] == DEBT_CODE]
        munis = d[d["municipality_code"].str.len() == 4].groupby("year")["value"].sum()
        riket = d[d["municipality_code"] == "00"].set_index("year")["value"]
        pd.testing.assert_series_equal(munis.sort_index(), riket.sort_index(),
                                       check_names=False, check_dtype=False, rtol=1e-6)

    @pytest.mark.parametrize("year,expected_bsek", SCB_NATIONAL_LONG_TERM_DEBT_BSEK.items())
    def test_processed_per_capita_reconstructs_total(self, year, expected_bsek):
        base = _load(PROCESSED_DIR / "kri_base_data.parquet")
        pop = _load(CACHE_DIR / "population.parquet")
        pop = pop[pop["year"] == year].groupby("municipality_code")["value"].sum()
        b = base[base["year"] == year].set_index("municipality_code")["debt_per_capita"].copy()
        b.loc["0980"] /= 0.65  # undo Gotland municipal-share adjustment
        total_bsek = (b * pop.reindex(b.index)).sum() / 1e9
        assert total_bsek == pytest.approx(expected_bsek, rel=TOLERANCE)
