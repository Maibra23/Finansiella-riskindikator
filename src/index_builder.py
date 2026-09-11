"""
KRI Index Builder: Computes Kommunal Finansiell Riskindikator scores.

Reads cleaned base data, performs cross-sectional z-score normalization,
applies direction correction, computes weighted composite score,
and classifies municipalities into risk categories.

All variable names and comments in English.
User-facing strings (risk class labels) in Swedish.
"""

import logging
import pandas as pd
import numpy as np
from pathlib import Path

from src.config import WEIGHTS, VARIABLE_DIRECTION, PROCESSED_DIR, START_YEAR, END_YEAR

logger = logging.getLogger(__name__)

# Column mapping: variable key -> base data column name
VARIABLE_COLUMNS = {
    "debt": "debt_per_capita",
    "unemployment": "unemployment",
    "dependency_ratio": "dependency_ratio",
    "population_growth": "population_growth",
    "tax_base": "tax_base_relative",
}

# Z-score output column names
Z_COLUMNS = {
    "debt": "z_debt",
    "unemployment": "z_unemployment",
    "dependency_ratio": "z_dependency",
    "population_growth": "z_population",
    "tax_base": "z_tax_base",
}

# Contribution column names (weight * z_score)
CONTRIBUTION_COLUMNS = {
    "debt": "contribution_debt",
    "unemployment": "contribution_unemployment",
    "dependency_ratio": "contribution_dependency",
    "population_growth": "contribution_population",
    "tax_base": "contribution_tax_base",
}


class KRIBuilder:
    """Builds the KRI composite risk index for all municipalities and years."""

    def __init__(self):
        # Validate weights at construction time
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights must sum to 1.0, got {total}"
        logger.info("KRIBuilder initialized. Weights sum: %.4f", total)

    # ------------------------------------------------------------------
    # Step 1: Cross-sectional z-score normalization for a single year
    # ------------------------------------------------------------------

    def normalize(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """
        Compute cross-sectional z-scores for each variable within a given year.

        Parameters
        ----------
        df : DataFrame with base data for a single year.
        year : The year being processed (used only for logging).

        Returns
        -------
        DataFrame with added z_* columns.
        """
        result = df.copy()

        for key, col in VARIABLE_COLUMNS.items():
            z_col = Z_COLUMNS[key]
            series = result[col]
            mean = series.mean(skipna=True)
            std = series.std(skipna=True, ddof=1)

            if std == 0 or np.isnan(std):
                logger.warning(
                    "Year %d: std=0 for %s: setting z-scores to 0", year, col
                )
                result[z_col] = 0.0
            else:
                result[z_col] = (series - mean) / std

        return result

    # ------------------------------------------------------------------
    # Step 2: Direction correction
    # ------------------------------------------------------------------

    def correct_direction(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Invert z-scores for variables where high value = LOW risk.

        Variables where high = high risk (keep as-is): debt, unemployment, dependency_ratio
        Variables where high = low risk (multiply by -1): population_growth, tax_base
        """
        result = df.copy()

        for key, z_col in Z_COLUMNS.items():
            if not VARIABLE_DIRECTION[key]:  # False = high value = low risk
                result[z_col] = result[z_col] * -1
                logger.debug("Inverted z-scores for %s (high=low risk)", key)

        return result

    # ------------------------------------------------------------------
    # Step 3: Compute KRI score and contributions
    # ------------------------------------------------------------------

    def compute_kri(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute KRI = weighted sum of direction-corrected z-scores.

        Also computes per-variable contributions (weight_k * z_k).

        Returns DataFrame with columns:
            municipality_code, municipality_name, year,
            kri_score,
            z_debt, z_unemployment, z_dependency, z_population, z_tax_base,
            contribution_debt, contribution_unemployment, contribution_dependency,
            contribution_population, contribution_tax_base
        """
        result = df.copy()

        # Compute contributions and accumulate KRI score
        result["kri_score"] = 0.0
        for key in WEIGHTS:
            z_col = Z_COLUMNS[key]
            contrib_col = CONTRIBUTION_COLUMNS[key]
            weight = WEIGHTS[key]
            result[contrib_col] = result[z_col] * weight
            result["kri_score"] += result[contrib_col]

        return result

    # ------------------------------------------------------------------
    # Step 4: Classify into risk categories and rank
    # ------------------------------------------------------------------

    def classify(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add risk_class and rank columns per year.

        risk_class:
            'Låg' , below 25th percentile (lower KRI = lower risk)
            'Hög' , above 75th percentile
            'Medel', in between

        rank: 1 = highest KRI (highest risk), ascending.
        """
        result = df.copy()
        result["risk_class"] = "Medel"
        result["rank"] = 0

        for year in result["year"].unique():
            mask = result["year"] == year
            scores = result.loc[mask, "kri_score"]

            p25 = scores.quantile(0.25)
            p75 = scores.quantile(0.75)

            result.loc[mask & (result["kri_score"] < p25), "risk_class"] = "Låg"
            result.loc[mask & (result["kri_score"] > p75), "risk_class"] = "Hög"

            # Rank: highest KRI score gets rank 1
            result.loc[mask, "rank"] = (
                scores.rank(ascending=False, method="min").astype(int)
            )

            logger.debug(
                "Year %d: p25=%.3f p75=%.3f | Låg=%d Medel=%d Hög=%d",
                year,
                p25,
                p75,
                (result.loc[mask, "risk_class"] == "Låg").sum(),
                (result.loc[mask, "risk_class"] == "Medel").sum(),
                (result.loc[mask, "risk_class"] == "Hög").sum(),
            )

        return result

    # ------------------------------------------------------------------
    # Step 5: Process all years
    # ------------------------------------------------------------------

    def compute_all_years(self, base_df: pd.DataFrame) -> pd.DataFrame:
        """
        Run normalize -> correct_direction -> compute_kri for each year.

        Returns a complete DataFrame with all years concatenated.
        """
        year_frames = []
        years = sorted(base_df["year"].unique())
        logger.info("Processing %d years: %d to %d", len(years), years[0], years[-1])

        for year in years:
            year_df = base_df[base_df["year"] == year].copy()
            logger.info("Year %d: %d municipalities", year, len(year_df))

            year_df = self.normalize(year_df, year)
            year_df = self.correct_direction(year_df)
            year_df = self.compute_kri(year_df)
            year_frames.append(year_df)

        combined = pd.concat(year_frames, ignore_index=True)
        logger.info("compute_all_years complete. Total rows: %d", len(combined))
        return combined

    # ------------------------------------------------------------------
    # Step 6: Validation
    # ------------------------------------------------------------------

    def _validate(self, df: pd.DataFrame) -> None:
        """Run basic sanity checks on z-scores and weights."""
        logger.info("Running validation checks...")

        # Weights sum
        weight_total = sum(WEIGHTS.values())
        assert abs(weight_total - 1.0) < 0.001, f"Weights sum is {weight_total}"
        logger.info("  [OK] Weights sum to %.4f", weight_total)

        # Z-score properties per year (should be near mean=0, std=1)
        for year in df["year"].unique():
            year_df = df[df["year"] == year]
            for key, z_col in Z_COLUMNS.items():
                z = year_df[z_col]
                mean_z = z.mean()
                std_z = z.std(ddof=1)
                if abs(mean_z) > 0.05:
                    logger.warning(
                        "Year %d, %s: z-score mean=%.4f (expected ~0)", year, z_col, mean_z
                    )
                if abs(std_z - 1.0) > 0.1:
                    logger.warning(
                        "Year %d, %s: z-score std=%.4f (expected ~1)", year, z_col, std_z
                    )

        # Classification distribution check (latest year)
        latest_year = df["year"].max()
        latest = df[df["year"] == latest_year]
        total = len(latest)
        lag = (latest["risk_class"] == "Låg").sum()
        hog = (latest["risk_class"] == "Hög").sum()
        med = (latest["risk_class"] == "Medel").sum()
        logger.info(
            "  [OK] %d classification for year %d: Låg: %d (%.0f%%), Medel: %d (%.0f%%), Hög: %d (%.0f%%)",
            total, latest_year,
            lag, 100 * lag / total,
            med, 100 * med / total,
            hog, 100 * hog / total,
        )

    # ------------------------------------------------------------------
    # Main orchestrator
    # ------------------------------------------------------------------

    def build(self) -> pd.DataFrame:
        """
        Full pipeline:
          1. Read kri_base_data.parquet
          2. compute_all_years (normalize + correct_direction + compute_kri)
          3. classify
          4. validate
          5. Save kri_results.parquet
          6. Return DataFrame
        """
        input_path = Path(PROCESSED_DIR) / "kri_base_data.parquet"
        output_path = Path(PROCESSED_DIR) / "kri_results.parquet"

        logger.info("Reading base data from %s", input_path)
        base_df = pd.read_parquet(input_path)
        logger.info("Base data shape: %s", base_df.shape)

        # Compute KRI for all years
        kri_df = self.compute_all_years(base_df)

        # Classify into risk categories and rank
        logger.info("Classifying municipalities into risk categories...")
        kri_df = self.classify(kri_df)

        # Validation
        self._validate(kri_df)

        # Select and order final columns
        output_columns = [
            "municipality_code", "municipality_name", "year",
            "kri_score",
            "z_debt", "z_unemployment", "z_dependency", "z_population", "z_tax_base",
            "contribution_debt", "contribution_unemployment", "contribution_dependency",
            "contribution_population", "contribution_tax_base",
            "risk_class", "rank",
            # Keep raw inputs for downstream use
            "debt_per_capita", "unemployment", "dependency_ratio",
            "population_growth", "tax_base_relative",
        ]
        kri_df = kri_df[output_columns]

        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        kri_df.to_parquet(output_path, index=False)
        logger.info("KRI results saved to %s (%d rows)", output_path, len(kri_df))

        return kri_df
