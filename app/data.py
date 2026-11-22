"""
app/data.py
-----------
Single data-access layer for every page: cached loaders for the KRI results and
the optional weight-sensitivity layer, plus small shared helpers.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = PROJECT_ROOT / "data" / "processed" / "kri_results.parquet"
SENSITIVITY_PATH = PROJECT_ROOT / "data" / "processed" / "kri_sensitivity.parquet"


@st.cache_data(show_spinner="Laddar data...")
def _read_results() -> pd.DataFrame | None:
    if not RESULTS_PATH.exists():
        return None
    df = pd.read_parquet(RESULTS_PATH)
    df["year"] = df["year"].astype(int)
    return df


def load_kri_data() -> pd.DataFrame:
    """KRI results for all municipalities and years; stops the page if missing."""
    df = _read_results()
    if df is None:
        st.error(
            "Datafilen saknas. Kör datapipelinen (scripts/run_pipeline.py) "
            "för att generera kri_results.parquet."
        )
        st.stop()
    return df


@st.cache_data(show_spinner=False)
def load_sensitivity() -> pd.DataFrame | None:
    """Weight-sensitivity band, or None when the optional layer is not built.

    Every consumer is guarded on this: without the file a page renders exactly
    as it did before the layer existed, with no placeholder and no warning.
    """
    if not SENSITIVITY_PATH.exists():
        return None
    try:
        df = pd.read_parquet(SENSITIVITY_PATH)
        df["year"] = df["year"].astype(int)
        return df
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def modal_agreement(year: int) -> int | None:
    """How many municipalities keep their published class as the modal class."""
    sens = load_sensitivity()
    kri = _read_results()
    if sens is None or kri is None:
        return None
    merged = kri[["municipality_code", "year", "risk_class"]].merge(
        sens, on=["municipality_code", "year"]
    )
    sub = merged[merged["year"] == year]
    return int((sub["modal_class"] == sub["risk_class"]).sum())


def year_slice(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Rows for one year (copy)."""
    return df[df["year"] == year].copy()


def kommun_history(df: pd.DataFrame, code: str) -> pd.DataFrame:
    """All years for one municipality, oldest first (copy)."""
    return df[df["municipality_code"] == code].sort_values("year").copy()


def year_range(df: pd.DataFrame) -> tuple[int, int]:
    """First and last year in the data."""
    return int(df["year"].min()), int(df["year"].max())


@st.cache_data(show_spinner=False)
def cached_pdf(year: int) -> bytes:
    """National PDF report for *year*, generated once per year and session cache."""
    from src.report_gen import generate_report

    return generate_report(kri_df=load_kri_data(), report_year=year)
