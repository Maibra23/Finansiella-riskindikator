"""
Data quality validation for KRI municipalities.

Checks completeness, flags special cases, and summarises quality per municipality.
All status strings and flag messages are in Swedish.
All code identifiers, comments, and docstrings are in English.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Special-case municipality flags (Swedish messages)
# ---------------------------------------------------------------------------

_SPECIAL_FLAGS: dict[str, list[str]] = {
    "0980": [
        "Gotland: Delad redovisning kommun/region (65%/35%): skuld justerad med faktor 0,65."
    ],
    "0330": [
        "Knivsta: Kommun bildad 2003, begränsad historik före 2010."
    ],
    "0331": [
        "Heby: Bytte från Uppsala till Västmanlands län 2007, tidsserie helt konsekvent från 2010."
    ],
}

# Variables that must be present for every municipality-year
_REQUIRED_VARIABLES = [
    "debt_per_capita",
    "unemployment",
    "dependency_ratio",
    "population_growth",
    "tax_base_relative",
]

# Status labels in Swedish
STATUS_OK = "OK"
STATUS_INTERPOLATED = "Interpolerad"
STATUS_MISSING = "Saknas"
STATUS_FLAGGED = "Flaggad"


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def validate_completeness(df: pd.DataFrame) -> pd.DataFrame:
    """Check every municipality-variable-year cell for data presence.

    Parameters
    ----------
    df:
        DataFrame with at least columns: municipality_code, year,
        and the five required variables.

    Returns
    -------
    DataFrame with columns: municipality_code, variable, year, status
        status is one of 'OK', 'Interpolerad', 'Saknas', 'Flaggad'
    """
    records: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        code = str(row["municipality_code"]).zfill(4)
        year = int(row["year"])
        is_special = code in _SPECIAL_FLAGS

        for var in _REQUIRED_VARIABLES:
            val = row.get(var)
            if pd.isna(val):
                status = STATUS_MISSING
            elif is_special and var == "debt_per_capita":
                status = STATUS_FLAGGED
            else:
                status = STATUS_OK
            records.append(
                {
                    "municipality_code": code,
                    "variable": var,
                    "year": year,
                    "status": status,
                }
            )

    return pd.DataFrame(records)


def get_municipality_flags(municipality_code: str) -> list[str]:
    """Return a list of Swedish warning strings for a given municipality.

    Parameters
    ----------
    municipality_code:
        4-digit SCB municipality code (e.g. '0980').

    Returns
    -------
    list of Swedish flag strings, empty if no known issues.
    """
    code = str(municipality_code).zfill(4)
    return list(_SPECIAL_FLAGS.get(code, []))


def get_data_quality_summary(df: pd.DataFrame | None = None) -> dict[str, Any]:
    """Compute a high-level data quality summary.

    Parameters
    ----------
    df:
        KRI base data DataFrame.  If None, loads from data/processed/kri_base_data.parquet.

    Returns
    -------
    dict with keys:
        total_municipalities, complete, interpolated_or_flagged, missing,
        most_problematic (list of municipality codes), coverage_pct
    """
    if df is None:
        p = PROJECT_ROOT / "data" / "processed" / "kri_base_data.parquet"
        if not p.exists():
            return {
                "total_municipalities": 0,
                "complete": 0,
                "interpolated_or_flagged": 0,
                "missing": 0,
                "most_problematic": [],
                "coverage_pct": 0.0,
            }
        df = pd.read_parquet(p)

    completeness = validate_completeness(df)

    total_codes = df["municipality_code"].nunique()

    # Per municipality: any missing?
    missing_mask = completeness["status"] == STATUS_MISSING
    codes_with_missing = completeness.loc[missing_mask, "municipality_code"].unique().tolist()

    flagged_mask = completeness["status"].isin([STATUS_FLAGGED, STATUS_INTERPOLATED])
    codes_flagged = completeness.loc[flagged_mask, "municipality_code"].unique().tolist()

    codes_with_issues = list(set(codes_with_missing) | set(codes_flagged))
    complete_count = total_codes - len(set(codes_with_missing))

    # Most problematic = most missing cells
    if codes_with_missing:
        miss_counts = (
            completeness[missing_mask]
            .groupby("municipality_code")
            .size()
            .sort_values(ascending=False)
        )
        most_problematic = miss_counts.head(10).index.tolist()
    else:
        most_problematic = []

    coverage_pct = round(complete_count / total_codes * 100, 1) if total_codes else 0.0

    return {
        "total_municipalities": total_codes,
        "complete": complete_count,
        "interpolated_or_flagged": len(set(codes_flagged) - set(codes_with_missing)),
        "missing": len(codes_with_missing),
        "most_problematic": most_problematic,
        "coverage_pct": coverage_pct,
    }
