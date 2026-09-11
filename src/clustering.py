"""
Cluster analysis and peer group analysis for KRI municipalities.

Provides k-means classification as an alternative to quantile classification,
Euclidean-distance-based peer group finding, risk transition analysis,
and distribution statistics.

All variable names and comments in English.
User-facing strings (risk class labels) in Swedish.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from scipy.stats import kurtosis, skew
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# The 5 z-score variables used for distance-based comparisons
Z_SCORE_COLUMNS = [
    "z_debt",
    "z_unemployment",
    "z_dependency",
    "z_population",
    "z_tax_base",
]

# Risk class labels (Swedish), ordered low -> high risk
RISK_LABELS = ["Låg", "Medel", "Hög"]


# ---------------------------------------------------------------------------
# 1. K-means classification
# ---------------------------------------------------------------------------

def kmeans_classification(kri_df: pd.DataFrame, k: int = 3) -> pd.DataFrame:
    """
    Classify municipalities into risk groups using k-means clustering.

    Runs k-means on the 5 z-score variables per year, then maps cluster IDs
    to risk labels ('Låg', 'Medel', 'Hög') by ordering clusters on their
    centroid mean (i.e. the cluster with the lowest average score across all
    5 z-score dimensions gets label 'Låg').

    Parameters
    ----------
    kri_df : DataFrame produced by KRIBuilder (must contain z_* columns and 'year').
    k : Number of clusters (default 3 matches the three quantile classes).

    Returns
    -------
    DataFrame with an additional 'kmeans_risk_class' column.
    """
    result = kri_df.copy()
    result["kmeans_risk_class"] = ""

    years = sorted(result["year"].unique())
    logger.info("Running k-means (k=%d) for %d years", k, len(years))

    for year in years:
        mask = result["year"] == year
        year_df = result.loc[mask, Z_SCORE_COLUMNS].copy()

        # Drop rows with any NaN; they will be labelled as NaN downstream
        valid_mask = year_df.notna().all(axis=1)
        X = year_df.loc[valid_mask].values

        if len(X) < k:
            logger.warning("Year %d: fewer than k=%d municipalities: skipping k-means", year, k)
            continue

        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        cluster_ids = km.fit_predict(X)

        # Map cluster id -> risk label based on mean centroid value
        # Higher centroid mean = higher risk
        centroid_means = km.cluster_centers_.mean(axis=1)
        order = np.argsort(centroid_means)  # ascending: index 0 = lowest centroid
        label_map = {int(order[i]): RISK_LABELS[i] for i in range(k)}

        labels = pd.Series(cluster_ids, index=year_df.loc[valid_mask].index).map(label_map)
        result.loc[labels.index, "kmeans_risk_class"] = labels

        logger.debug(
            "Year %d: Låg: %d  Medel: %d  Hög: %d",
            year,
            (labels == "Låg").sum(),
            (labels == "Medel").sum(),
            (labels == "Hög").sum(),
        )

    return result


# ---------------------------------------------------------------------------
# 2. Peer municipality finder
# ---------------------------------------------------------------------------

def get_peer_municipalities(
    municipality_code: str,
    kri_df: pd.DataFrame,
    n: int = 10,
    year: Optional[int] = None,
) -> pd.DataFrame:
    """
    Find the n most similar municipalities using Euclidean distance on z-scores.

    Similarity is measured over the 5 direction-corrected z-score variables
    (z_debt, z_unemployment, z_dependency, z_population, z_tax_base).

    Parameters
    ----------
    municipality_code : The reference municipality (4-digit string code).
    kri_df : Full KRI DataFrame (must contain z_* columns, 'year', 'municipality_code',
             'municipality_name').
    n : Number of peer municipalities to return (excluding the reference itself).
    year : If given, use that year's data. If None, uses the latest available year.

    Returns
    -------
    DataFrame with columns [municipality_code, municipality_name, year, distance,
    kri_score, risk_class] sorted ascending by distance (closest first).
    """
    if year is None:
        year = int(kri_df["year"].max())

    year_df = kri_df[kri_df["year"] == year].copy()

    if municipality_code not in year_df["municipality_code"].values:
        raise ValueError(
            f"Municipality '{municipality_code}' not found in year {year}."
        )

    valid_df = year_df.dropna(subset=Z_SCORE_COLUMNS)
    ref_row = valid_df[valid_df["municipality_code"] == municipality_code]

    if ref_row.empty:
        raise ValueError(
            f"Municipality '{municipality_code}' has missing z-score data for year {year}."
        )

    ref_vec = ref_row[Z_SCORE_COLUMNS].values  # shape (1, 5)
    all_vecs = valid_df[Z_SCORE_COLUMNS].values  # shape (N, 5)

    distances = cdist(ref_vec, all_vecs, metric="euclidean").flatten()

    valid_df = valid_df.copy()
    valid_df["distance"] = distances

    # Exclude the reference municipality itself
    peers = (
        valid_df[valid_df["municipality_code"] != municipality_code]
        .sort_values("distance")
        .head(n)
        [["municipality_code", "municipality_name", "year", "distance", "kri_score", "risk_class"]]
        .reset_index(drop=True)
    )

    logger.info(
        "Peer group for %s (year %d): found %d peers (top-%d)",
        municipality_code, year, len(peers), n,
    )
    return peers


# ---------------------------------------------------------------------------
# 3. Risk transition analysis
# ---------------------------------------------------------------------------

def compute_risk_transitions(kri_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyse how municipalities move between risk classes over consecutive years.

    For each municipality and each pair of consecutive years, records whether
    the risk class stayed the same, improved, or deteriorated.  Marks
    significant transitions:
        - 'deteriorated': moved from 'Låg' to 'Hög' (worst jump)
        - 'improved':     moved from 'Hög' to 'Låg' (best jump)

    Parameters
    ----------
    kri_df : Full KRI DataFrame with columns [municipality_code, municipality_name,
             year, risk_class].

    Returns
    -------
    DataFrame with columns:
        municipality_code, municipality_name,
        year_from, year_to,
        risk_class_from, risk_class_to,
        transition_direction  ('same' | 'improved' | 'deteriorated'),
        significant           (True if Low->High or High->Low)
    """
    _rank = {"Låg": 0, "Medel": 1, "Hög": 2}

    pivot = (
        kri_df[["municipality_code", "municipality_name", "year", "risk_class"]]
        .sort_values(["municipality_code", "year"])
        .copy()
    )

    pivot["risk_rank"] = pivot["risk_class"].map(_rank)

    rows = []
    for mcode, grp in pivot.groupby("municipality_code"):
        grp = grp.sort_values("year").reset_index(drop=True)
        mname = grp["municipality_name"].iloc[0]
        for i in range(len(grp) - 1):
            r_from = grp.loc[i, "risk_rank"]
            r_to = grp.loc[i + 1, "risk_rank"]
            c_from = grp.loc[i, "risk_class"]
            c_to = grp.loc[i + 1, "risk_class"]
            y_from = int(grp.loc[i, "year"])
            y_to = int(grp.loc[i + 1, "year"])

            if pd.isna(r_from) or pd.isna(r_to):
                continue

            if r_to > r_from:
                direction = "deteriorated"
            elif r_to < r_from:
                direction = "improved"
            else:
                direction = "same"

            significant = (c_from == "Låg" and c_to == "Hög") or (
                c_from == "Hög" and c_to == "Låg"
            )

            rows.append(
                {
                    "municipality_code": mcode,
                    "municipality_name": mname,
                    "year_from": y_from,
                    "year_to": y_to,
                    "risk_class_from": c_from,
                    "risk_class_to": c_to,
                    "transition_direction": direction,
                    "significant": significant,
                }
            )

    transitions = pd.DataFrame(rows)

    n_sig = transitions["significant"].sum() if len(transitions) else 0
    logger.info(
        "Risk transitions computed: %d rows, %d significant (Low<->High)",
        len(transitions), n_sig,
    )
    return transitions


# ---------------------------------------------------------------------------
# 4. Distribution statistics
# ---------------------------------------------------------------------------

def compute_distribution_stats(kri_df: pd.DataFrame, year: int) -> dict:
    """
    Compute distribution statistics for KRI scores in a given year.

    Parameters
    ----------
    kri_df : Full KRI DataFrame with columns [year, kri_score].
    year : The year to compute statistics for.

    Returns
    -------
    dict with keys:
        year, n,
        mean, median, std, skewness, kurt,
        p10, p25, p50, p75, p90,
        min, max
    """
    year_scores = kri_df.loc[kri_df["year"] == year, "kri_score"].dropna()

    if year_scores.empty:
        raise ValueError(f"No KRI data found for year {year}.")

    vals = year_scores.values

    stats = {
        "year": year,
        "n": int(len(vals)),
        "mean": float(np.mean(vals)),
        "median": float(np.median(vals)),
        "std": float(np.std(vals, ddof=1)),
        "skewness": float(skew(vals)),
        "kurt": float(kurtosis(vals)),
        "p10": float(np.percentile(vals, 10)),
        "p25": float(np.percentile(vals, 25)),
        "p50": float(np.percentile(vals, 50)),
        "p75": float(np.percentile(vals, 75)),
        "p90": float(np.percentile(vals, 90)),
        "min": float(np.min(vals)),
        "max": float(np.max(vals)),
    }

    logger.info(
        "Distribution stats year %d: n=%d  mean=%.3f  std=%.3f  skew=%.3f",
        year, stats["n"], stats["mean"], stats["std"], stats["skewness"],
    )
    return stats
