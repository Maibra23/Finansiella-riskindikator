"""Weight-sensitivity analysis for the KRI composite index.

The KRI weights (0.25 debt, 0.25 unemployment, 0.20 dependency, 0.15 population,
0.15 tax base) are argued from public-finance theory rather than estimated.  The
standard objection is that they are therefore arbitrary.

Deriving them from the data instead — PCA on the five z-scores — is not a valid
answer here: PC1 loads *negatively* on debt in every year 2010-2024, so it would
rank Sweden's most indebted municipalities among its safest, and PC1 carries only
~44 % of variance with a second component above the Kaiser threshold.  See
docs/methodology.md.

This module answers the objection the other way, following the OECD/JRC
*Handbook on Constructing Composite Indicators*: treat the weights as an
uncertain input and propagate that uncertainty to the output.  Each weight is
drawn uniformly within ±delta of its nominal value, the vector is renormalised
to sum to 1, and the index is recomputed.  For each municipality and year we
record how far its rank moves and how often it keeps its published risk class.

The layer is strictly additive.  It never recomputes ``kri_score``, never
reassigns ``risk_class`` and never touches ``rank``; it reads them and reports
how well they hold up.  Delete ``kri_sensitivity.parquet`` and the dashboard
renders exactly as it did before this module existed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.config import SENSITIVITY, WEIGHT_ORDER, WEIGHTS

# Direction-corrected z-score columns, in the same order as WEIGHT_ORDER.
Z_COLUMNS = ["z_debt", "z_unemployment", "z_dependency", "z_population", "z_tax_base"]

# Risk classes ordered low -> high, matching index_builder.classify().
RISK_CLASSES = np.array(["Låg", "Medel", "Hög"])

# Quantiles that define the classes. Must match src/risk_scale.py and
# index_builder.classify(), which is asserted in tests/test_sensitivity.py.
LOW_QUANTILE = 0.25
HIGH_QUANTILE = 0.75

SENSITIVITY_COLUMNS = [
    "municipality_code",
    "year",
    "rank_p05",
    "rank_median",
    "rank_p95",
    "class_stability",
    "modal_class",
    "is_robust",
]


@dataclass(frozen=True)
class SensitivityConfig:
    """Parameters of the Monte Carlo. Immutable so a run cannot drift mid-flight.

    Defaults come from ``config.SENSITIVITY`` and are quoted verbatim in the UI,
    so a caller overriding them is producing a different published claim.
    """

    n_draws: int = int(SENSITIVITY["n_draws"])
    delta: float = float(SENSITIVITY["delta"])
    robust_threshold: float = float(SENSITIVITY["robust_threshold"])
    seed: int = int(SENSITIVITY["seed"])
    nominal: np.ndarray = field(
        default_factory=lambda: np.array([WEIGHTS[k] for k in WEIGHT_ORDER], dtype="float64")
    )

    def __post_init__(self) -> None:
        if self.n_draws < 1:
            raise ValueError(f"n_draws must be at least 1, got {self.n_draws}")
        if not 0.0 < self.delta < float(min(WEIGHTS.values())):
            raise ValueError(
                f"delta must be positive and smaller than the smallest weight "
                f"({min(WEIGHTS.values())}), got {self.delta}"
            )
        if not 0.5 <= self.robust_threshold <= 1.0:
            raise ValueError(f"robust_threshold must be in [0.5, 1.0], got {self.robust_threshold}")


def sample_weights(config: SensitivityConfig | None = None) -> np.ndarray:
    """Draw ``n_draws`` plausible weight vectors.

    Each weight is drawn uniformly from ``[w - delta, w + delta]``, then the
    vector is renormalised to sum to 1.  The renormalisation is what makes the
    draw honest: weights must still sum to one, so raising debt necessarily
    lowers something else — which is exactly the trade-off a critic is pointing
    at.  Uniform rather than Dirichlet because "each weight may move up to five
    percentage points" can be explained in a caption, and a reader who disagrees
    with delta can reason about what a different delta would do.

    Renormalising can itself push a weight past delta (a vector whose raw draws
    all landed low gets scaled up), so draws that break the bound are rejected
    rather than kept.  About 84 % survive, the accepted draws stay centred on
    the nominal weights, and the claim made in the UI — no weight ever moves
    more than delta — becomes literally true instead of approximately true.

    Returns an ``(n_draws, 5)`` array whose columns follow ``WEIGHT_ORDER``.
    """
    config = config or SensitivityConfig()
    rng = np.random.default_rng(config.seed)
    n_vars = len(config.nominal)

    accepted: list[np.ndarray] = []
    collected = 0
    # Oversample by the observed rejection rate plus headroom, so the common
    # case needs a single batch and the loop stays deterministic either way.
    batch = max(int(config.n_draws * 1.3), 64)
    while collected < config.n_draws:
        draws = rng.uniform(
            config.nominal - config.delta,
            config.nominal + config.delta,
            size=(batch, n_vars),
        )
        draws = np.clip(draws, 0.0, None)
        draws /= draws.sum(axis=1, keepdims=True)
        keep = draws[np.abs(draws - config.nominal).max(axis=1) <= config.delta]
        accepted.append(keep)
        collected += len(keep)

    return np.concatenate(accepted)[: config.n_draws]


def _summarise_year(
    year_df: pd.DataFrame,
    weights: np.ndarray,
    config: SensitivityConfig,
) -> pd.DataFrame:
    """Propagate the weight draws through one analysis year."""
    scores = year_df[Z_COLUMNS].to_numpy(dtype="float64") @ weights.T  # (n_muni, n_draws)

    # Rank 1 = highest KRI = highest risk, matching index_builder.
    ranks = (-scores).argsort(axis=0).argsort(axis=0) + 1

    # Cut points are recomputed *inside* each draw. Holding them fixed at the
    # published p25/p75 would measure score movement only, and the question is
    # class movement — so this reproduces what classify() would have done had
    # those been the real weights.
    low_cut = np.quantile(scores, LOW_QUANTILE, axis=0)
    high_cut = np.quantile(scores, HIGH_QUANTILE, axis=0)
    drawn_class = np.where(scores < low_cut, 0, np.where(scores > high_cut, 2, 1))

    published = year_df["risk_class"].map({c: i for i, c in enumerate(RISK_CLASSES)}).to_numpy()
    stability = (drawn_class == published[:, None]).mean(axis=1)

    counts = np.stack([(drawn_class == i).sum(axis=1) for i in range(len(RISK_CLASSES))], axis=1)

    return pd.DataFrame(
        {
            "municipality_code": year_df["municipality_code"].to_numpy(),
            "year": year_df["year"].to_numpy(),
            "rank_p05": np.percentile(ranks, 5, axis=1).round().astype("int32"),
            "rank_median": np.median(ranks, axis=1).round().astype("int32"),
            "rank_p95": np.percentile(ranks, 95, axis=1).round().astype("int32"),
            "class_stability": stability.round(4),
            "modal_class": RISK_CLASSES[counts.argmax(axis=1)],
            "is_robust": stability >= config.robust_threshold,
        }
    )


def compute_sensitivity(
    kri_df: pd.DataFrame,
    config: SensitivityConfig | None = None,
) -> pd.DataFrame:
    """Return one sensitivity row per (municipality, year).

    *kri_df* is never mutated.  Output is sorted by (year, municipality_code) so
    two runs on differently-ordered inputs produce byte-identical parquet — a
    band that shifts between pipeline runs would undermine trust in the whole
    dashboard.
    """
    config = config or SensitivityConfig()

    missing = [c for c in [*Z_COLUMNS, "risk_class", "municipality_code", "year"] if c not in kri_df]
    if missing:
        raise ValueError(f"kri_df is missing required columns: {missing}")

    weights = sample_weights(config)
    frames = [
        _summarise_year(
            kri_df[kri_df["year"] == year].sort_values("municipality_code").reset_index(drop=True),
            weights,
            config,
        )
        for year in sorted(kri_df["year"].unique())
    ]
    result = pd.concat(frames, ignore_index=True)
    return result[SENSITIVITY_COLUMNS]


def summarise(kri_df: pd.DataFrame, sensitivity_df: pd.DataFrame, year: int) -> dict[str, float]:
    """Headline figures for one year, for the CLI and the Källor page."""
    merged = kri_df.merge(sensitivity_df, on=["municipality_code", "year"])
    sub = merged[merged["year"] == year]
    return {
        "n": len(sub),
        "robust": int(sub["is_robust"].sum()),
        "fragile": int((~sub["is_robust"]).sum()),
        "modal_disagreements": int((sub["modal_class"] != sub["risk_class"]).sum()),
        "median_band": float((sub["rank_p95"] - sub["rank_p05"]).median()),
    }
