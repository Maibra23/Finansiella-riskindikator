"""Single source of truth for the KRI colour/zone scale used by every chart.

Why this module exists
----------------------
The composite KRI is a *weighted mean* of five z-scores.  Averaging imperfectly
correlated standard-normal variables shrinks the spread well below 1σ, in
practice ≈0.60 in 2010 falling to ≈0.47 in 2024, with the full range staying
within ±2.2.  The dashboard originally assumed the composite was itself
standard normal and hardcoded the standard-normal quartiles (±0.6745) as risk
boundaries, with axes spanning ±2.5.

That produced two visible defects:

* charts painted only ~17 municipalities red while the tables and KPI cards
  labelled 73 as *Hög risk*, 111 of 290 municipalities (38 %) were shown in a
  different zone by the charts than by the rest of the dashboard;
* every municipality was squeezed into the middle half of each axis.

``index_builder`` assigns ``risk_class`` from the **empirical** 25th/75th
percentiles of the given year.  ``RiskScale`` reproduces exactly that rule so
charts, map and tables cannot drift apart again.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

# Quantiles that define the risk classes.  Must stay in sync with
# src/index_builder.py, which assigns risk_class from these same cut points.
LOW_QUANTILE = 0.25
HIGH_QUANTILE = 0.75

# Axis half-width is rounded outward to this resolution so tick labels stay tidy.
EXTENT_ROUNDING = 0.1

# Used only when a caller passes an empty or degenerate series (e.g. a filter
# that matched nothing).  Keeps the UI rendering instead of crashing.
FALLBACK_EXTENT = 1.0
FALLBACK_CUTOFF = 0.25


@dataclass(frozen=True)
class RiskScale:
    """Immutable description of where the risk zones sit on the KRI axis.

    Attributes
    ----------
    low:
        Upper bound of the *Låg risk* zone (the 25th percentile).  Negative.
    high:
        Lower bound of the *Hög risk* zone (the 75th percentile).  Positive.
    extent:
        Half-width of a symmetric axis that comfortably contains the data.
    """

    low: float
    high: float
    extent: float

    def __post_init__(self) -> None:
        if not self.low < 0.0 < self.high:
            raise ValueError(f"risk zone bounds must straddle zero, got {self.low}/{self.high}")
        if self.extent <= self.high or -self.extent >= self.low:
            raise ValueError(f"extent {self.extent} does not contain bounds {self.low}/{self.high}")

    @classmethod
    def from_scores(cls, scores: pd.Series | list[float]) -> RiskScale:
        """Derive the scale from a set of KRI scores.

        Pass the *unfiltered* scores for the period on display: the zone
        boundaries must match the ``risk_class`` labels shown elsewhere, and
        those are computed from the full population, not a filtered subset.
        """
        series = pd.Series(scores, dtype="float64").dropna()
        if series.empty:
            return cls(low=-FALLBACK_CUTOFF, high=FALLBACK_CUTOFF, extent=FALLBACK_EXTENT)

        low = float(series.quantile(LOW_QUANTILE))
        high = float(series.quantile(HIGH_QUANTILE))
        raw_extent = max(abs(float(series.min())), abs(float(series.max())))
        extent = math.ceil(raw_extent / EXTENT_ROUNDING) * EXTENT_ROUNDING

        # A degenerate spread (single municipality, or a filter leaving one
        # distinct value) can collapse the bounds onto zero.  Fall back rather
        # than emit a scale that cannot be drawn.
        if not low < 0.0 < high:
            low, high = -FALLBACK_CUTOFF, FALLBACK_CUTOFF
        extent = max(extent, high + EXTENT_ROUNDING, -low + EXTENT_ROUNDING)
        return cls(low=low, high=high, extent=extent)

    @classmethod
    def for_year(cls, kri_df: pd.DataFrame, year: int) -> RiskScale:
        """Scale for a single analysis year, matches that year's risk classes."""
        return cls.from_scores(kri_df.loc[kri_df["year"] == year, "kri_score"])

    @classmethod
    def pooled(cls, kri_df: pd.DataFrame) -> RiskScale:
        """Scale pooled over every year in *kri_df*.

        Trend charts draw one set of horizontal zone bands across the whole
        period, but the per-year boundaries drift (the composite's spread
        narrows over time).  Pooling is the honest single-line approximation.
        """
        return cls.from_scores(kri_df["kri_score"])

    def classify(self, value: float) -> str:
        """Swedish risk class for *value*, using the same rule as index_builder."""
        if value < self.low:
            return "Låg"
        if value > self.high:
            return "Hög"
        return "Medel"
