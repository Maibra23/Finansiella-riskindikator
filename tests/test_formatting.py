"""Tests for app/formatting.py, the single source of Swedish number formatting."""

import math

import numpy as np
import pytest

from app.formatting import (
    MISSING,
    fmt_count_of,
    fmt_decimal,
    fmt_int,
    fmt_kr,
    fmt_pct,
    fmt_pp,
    fmt_range,
    fmt_range_decimal,
    fmt_signed,
)

T = " "


@pytest.mark.unit
class TestFormatting:
    def test_decimal_comma(self) -> None:
        assert fmt_decimal(1.0734) == "1,07"
        assert fmt_decimal(-0.41) == "-0,41"

    def test_signed_zero_never_shows_minus(self) -> None:
        assert fmt_decimal(-0.001) == "0,00"
        assert fmt_signed(-0.001) == "0,00"
        assert fmt_decimal(-0.0) == "0,00"

    def test_thousands_use_narrow_nbsp(self) -> None:
        assert fmt_decimal(12345.6, 1) == f"12{T}345,6"
        assert fmt_int(121706.4) == f"121{T}706"
        assert fmt_int(-1234567) == f"-1{T}234{T}567"

    def test_rounding(self) -> None:
        assert fmt_decimal(0.125, 2) in {"0,12", "0,13"}  # banker's vs half-up, both acceptable
        assert fmt_int(2.5) in {"2", "3"}
        assert fmt_decimal(9.999, 2) == "10,00"

    def test_signed(self) -> None:
        assert fmt_signed(0.61) == "+0,61"
        assert fmt_signed(-0.17) == "-0,17"
        assert fmt_signed(0) == "0,00"

    def test_units(self) -> None:
        assert fmt_pct(4.12) == f"4,1{T}%"
        assert fmt_pp(0.3) == "+0,3 p.e."
        assert fmt_pp(-0.25, 2) == "-0,25 p.e."
        assert fmt_kr(121706) == f"121{T}706 kr"

    def test_counts_and_ranges(self) -> None:
        assert fmt_count_of(73, 290) == "73 av 290"
        assert fmt_range(3, 9) == "3 - 9"
        assert fmt_range_decimal(-1.37, 1.17) == "-1,37 - 1,17"

    @pytest.mark.parametrize(
        "fn", [fmt_decimal, fmt_int, fmt_signed, fmt_pct, fmt_pp, fmt_kr]
    )
    def test_missing_values(self, fn) -> None:
        assert fn(None) == MISSING
        assert fn(float("nan")) == MISSING
        assert fn(np.nan) == MISSING

    def test_missing_in_pairs(self) -> None:
        assert fmt_count_of(None, 290) == MISSING
        assert fmt_range(1, math.nan) == MISSING
        assert fmt_range_decimal(None, 1.0) == MISSING

    def test_numpy_scalars(self) -> None:
        assert fmt_decimal(np.float64(1.234)) == "1,23"
        assert fmt_int(np.int64(290)) == "290"
        assert fmt_count_of(np.int64(73), np.int64(290)) == "73 av 290"
