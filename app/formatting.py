"""
app/formatting.py
-----------------
Swedish number formatting for every user-facing value in the dashboard.

Pure functions, no Streamlit import, so they can be unit tested and reused by
pages, components and tooltips alike.

Project rules (enforced by scripts/verify_swedish_ui.py):
- decimal comma, thousands separator U+202F (narrow no-break space)
- ASCII hyphen-minus for negatives, never "-0,00"
- ranges as "3 - 9", counts as "73 av 290"
- missing values render as "Saknas"
"""

from __future__ import annotations

import math
from typing import Any

MISSING = "Saknas"
_THIN = " "


def _is_missing(v: Any) -> bool:
    if v is None:
        return True
    try:
        return math.isnan(float(v))
    except (TypeError, ValueError):
        return True


def _round_clean(v: float, nd: int) -> float:
    """Round and collapse signed zero, so -0.001 becomes 0.0 rather than -0.0."""
    r = round(float(v), nd)
    if abs(r) < 0.5 * 10 ** (-nd):
        r = 0.0
    return r


def _body(v: float, nd: int) -> str:
    """Absolute value with Swedish separators."""
    s = f"{abs(v):,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", _THIN)


def fmt_decimal(v: Any, nd: int = 2) -> str:
    """1.0734 -> "1,07"; -0.001 -> "0,00"; 12345.6 -> "12 345,60"."""
    if _is_missing(v):
        return MISSING
    r = _round_clean(v, nd)
    return ("-" if r < 0 else "") + _body(r, nd)


def fmt_int(v: Any) -> str:
    """121706.4 -> "121 706"."""
    return fmt_decimal(v, 0)


def fmt_signed(v: Any, nd: int = 2) -> str:
    """0.61 -> "+0,61"; -0.17 -> "-0,17"; 0 -> "0,00"."""
    if _is_missing(v):
        return MISSING
    r = _round_clean(v, nd)
    sign = "+" if r > 0 else ("-" if r < 0 else "")
    return sign + _body(r, nd)


def fmt_pct(v: Any, nd: int = 1) -> str:
    """4.12 -> "4,1 %" (narrow no-break space before %)."""
    if _is_missing(v):
        return MISSING
    return f"{fmt_decimal(v, nd)}{_THIN}%"


def fmt_pp(v: Any, nd: int = 1) -> str:
    """Change in percentage points: 0.3 -> "+0,3 p.e."."""
    if _is_missing(v):
        return MISSING
    return f"{fmt_signed(v, nd)} p.e."


def fmt_kr(v: Any) -> str:
    """121706 -> "121 706 kr"."""
    if _is_missing(v):
        return MISSING
    return f"{fmt_int(v)} kr"


def fmt_count_of(n: Any, total: Any) -> str:
    """73, 290 -> "73 av 290"."""
    if _is_missing(n) or _is_missing(total):
        return MISSING
    return f"{int(n)} av {int(total)}"


def fmt_range(a: Any, b: Any) -> str:
    """3, 9 -> "3 - 9"."""
    if _is_missing(a) or _is_missing(b):
        return MISSING
    return f"{int(a)} - {int(b)}"


def fmt_range_decimal(a: Any, b: Any, nd: int = 2) -> str:
    """-1.37, 1.17 -> "-1,37 - 1,17"."""
    if _is_missing(a) or _is_missing(b):
        return MISSING
    return f"{fmt_decimal(a, nd)} - {fmt_decimal(b, nd)}"
