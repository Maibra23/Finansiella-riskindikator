"""
Data cleaning and transformation module for KRI.

This module provides the DataCleaner class for cleaning raw API data,
computing derived variables, merging datasets, and validating data quality.

All variable names, comments, and docstrings in English.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.config import (
    MUNICIPALITIES,
    SPECIAL_CASES,
    START_YEAR,
    END_YEAR,
    YEARS,
    PROCESSED_DIR,
    BALANCE_SHEET_POSTS,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataCleaner:
    """
    Data cleaning and transformation pipeline for KRI computation.

    Takes raw DataFrames from SCB and Kolada APIs and produces a clean,
    merged dataset ready for index computation.

    Attributes:
        processed_dir: Directory for saving processed data
    """

    def __init__(self, processed_dir: str = PROCESSED_DIR):
        """
        Initialize the data cleaner.

        Args:
            processed_dir: Directory path for processed data files
        """
        self.processed_dir = Path(processed_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        # Store validation issues
        self.validation_issues: List[Dict[str, Any]] = []

    def clean_balance_sheet(
        self,
        df: pd.DataFrame,
        population_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Clean balance sheet data and compute debt per capita.

        Extracts long-term liabilities and converts from tkr to kr per capita.

        Args:
            df: Raw balance sheet DataFrame from SCB
            population_df: Population DataFrame for per-capita calculation

        Returns:
            DataFrame with columns: municipality_code, municipality_name, year, debt_per_capita
        """
        logger.info("Cleaning balance sheet data...")

        # Filter for long-term liabilities only
        # The balanspost column contains Swedish labels, we need to match "Långfristiga skulder"
        df_debt = df[df["balanspost"].str.contains("Långfristiga skulder", case=False, na=False)].copy()

        if df_debt.empty:
            # Try matching by code if label matching fails
            logger.warning("Could not find 'Långfristiga skulder' by name, checking available posts...")
            logger.info(f"Available balance posts: {df['balanspost'].unique()}")
            # Fall back to all data if specific post not found
            df_debt = df.copy()

        # Aggregate to get total long-term debt per municipality per year
        df_debt = df_debt.groupby(
            ["municipality_code", "municipality_name", "year"],
            as_index=False
        )["value"].sum()

        # Rename value column
        df_debt = df_debt.rename(columns={"value": "debt_tkr"})

        # Get total population per municipality per year
        pop_total = self._compute_total_population(population_df)

        # Merge debt with population
        df_debt = df_debt.merge(
            pop_total[["municipality_code", "year", "total_population"]],
            on=["municipality_code", "year"],
            how="left"
        )

        # Compute debt per capita (tkr * 1000 = kr, then divide by population)
        df_debt["debt_per_capita"] = (df_debt["debt_tkr"] * 1000) / df_debt["total_population"]

        # Handle Gotland special case (65% municipal share)
        gotland_mask = df_debt["municipality_code"] == "0980"
        if gotland_mask.any():
            adjustment = SPECIAL_CASES["0980"]["adjustment_factor"]
            df_debt.loc[gotland_mask, "debt_per_capita"] *= adjustment
            logger.info(f"Applied Gotland adjustment factor ({adjustment}) to debt")

        # Select final columns
        result = df_debt[[
            "municipality_code", "municipality_name", "year", "debt_per_capita"
        ]].copy()

        logger.info(f"Cleaned balance sheet: {len(result)} rows, "
                   f"{result['municipality_code'].nunique()} municipalities")

        return result

    def _compute_total_population(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute total population per municipality per year.

        Args:
            df: Population by age DataFrame

        Returns:
            DataFrame with total population per municipality per year
        """
        # Sum all age groups to get total population
        pop_total = df.groupby(
            ["municipality_code", "municipality_name", "year"],
            as_index=False
        )["value"].sum()

        pop_total = pop_total.rename(columns={"value": "total_population"})

        return pop_total

    def compute_dependency_ratio(
        self,
        population_df: pd.DataFrame,
        working_age_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Compute dependency ratio from working-age population percentage.

        If working_age_df is provided (from Kolada), use it directly.
        Otherwise, fall back to computing from SCB population data.

        Dependency ratio = (100 - working_age_pct) / working_age_pct * 100

        Args:
            population_df: Population by age DataFrame from SCB (fallback)
            working_age_df: Working-age population percentage from Kolada (preferred)

        Returns:
            DataFrame with columns: municipality_code, municipality_name, year, dependency_ratio
        """
        logger.info("Computing dependency ratio...")

        # Prefer Kolada working-age data if available
        if working_age_df is not None and not working_age_df.empty:
            logger.info("Using Kolada working-age percentage data")

            df = working_age_df.copy()

            # Compute dependency ratio from working-age percentage
            # working_age_pct is the percentage of population aged 20-64
            # dependency_ratio = (non-working / working) * 100
            df["dependency_ratio"] = (100 - df["working_age_pct"]) / df["working_age_pct"] * 100

            # Handle edge cases
            df["dependency_ratio"] = df["dependency_ratio"].replace([np.inf, -np.inf], np.nan)

            # Ensure municipality_name exists
            if "municipality_name" not in df.columns or df["municipality_name"].isna().all():
                df["municipality_name"] = df["municipality_code"].map(MUNICIPALITIES)

            # Select final columns
            result = df[[
                "municipality_code", "municipality_name", "year", "dependency_ratio"
            ]].copy()

            # Filter to analysis period
            result = result[(result["year"] >= START_YEAR) & (result["year"] <= END_YEAR)]

            logger.info(f"Computed dependency ratio: {len(result)} rows, "
                       f"mean ratio: {result['dependency_ratio'].mean():.3f}")

            return result

        # Fallback: compute from SCB population data
        logger.warning("Working-age data not available, falling back to SCB population data")
        return self._compute_dependency_ratio_from_scb(population_df)

    def _compute_dependency_ratio_from_scb(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute dependency ratio from SCB population by age data (fallback method).

        Args:
            df: Population by age DataFrame from SCB

        Returns:
            DataFrame with dependency ratio
        """
        df = df.copy()

        # Create age group categories based on the age column content
        def categorize_age(age_str: str) -> str:
            """Categorize age string into young, working, or old."""
            if pd.isna(age_str):
                return "unknown"

            age_str = str(age_str).lower()

            if "totalt" in age_str or "total" in age_str or age_str == "tot":
                return "total"

            # Extract numbers from string
            import re
            numbers = re.findall(r'\d+', age_str)

            if not numbers:
                return "unknown"

            lower_age = int(numbers[0])

            if lower_age < 20:
                return "young"
            elif lower_age < 65:
                return "working"
            else:
                return "old"

        df["age_category"] = df["age"].apply(categorize_age)

        # Aggregate by age category
        pop_by_category = df[df["age_category"].isin(["young", "working", "old"])].groupby(
            ["municipality_code", "municipality_name", "year", "age_category"],
            as_index=False
        )["value"].sum()

        if pop_by_category.empty:
            logger.warning("No age-specific data found in SCB population data")
            return pd.DataFrame(columns=[
                "municipality_code", "municipality_name", "year", "dependency_ratio"
            ])

        # Pivot to get columns for each category
        pop_pivot = pop_by_category.pivot_table(
            index=["municipality_code", "municipality_name", "year"],
            columns="age_category",
            values="value",
            fill_value=0
        ).reset_index()

        for col in ["young", "working", "old"]:
            if col not in pop_pivot.columns:
                pop_pivot[col] = 0

        pop_pivot["dependency_ratio"] = (
            (pop_pivot["young"] + pop_pivot["old"]) / pop_pivot["working"]
        )

        pop_pivot["dependency_ratio"] = pop_pivot["dependency_ratio"].replace(
            [np.inf, -np.inf], np.nan
        )

        result = pop_pivot[[
            "municipality_code", "municipality_name", "year", "dependency_ratio"
        ]].copy()

        result = result[result["year"] >= START_YEAR]

        logger.info(f"Computed dependency ratio (SCB fallback): {len(result)} rows")

        return result

    def compute_population_growth(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute 5-year rolling population growth.

        Growth = ((pop_t / pop_{t-5}) - 1) * 100

        Args:
            df: Population by age DataFrame (must include data from 2005 for 2010 calculation)

        Returns:
            DataFrame with columns: municipality_code, municipality_name, year, population_growth
        """
        logger.info("Computing population growth...")

        # Get total population per municipality per year
        pop_total = self._compute_total_population(df)

        # Sort by municipality and year
        pop_total = pop_total.sort_values(["municipality_code", "year"])

        # Create lagged population (5 years prior)
        pop_total["pop_lag5"] = pop_total.groupby("municipality_code")["total_population"].shift(5)

        # Compute 5-year growth rate
        pop_total["population_growth"] = (
            (pop_total["total_population"] / pop_total["pop_lag5"]) - 1
        ) * 100

        # Filter to analysis period (need lag data, so start from START_YEAR)
        result = pop_total[pop_total["year"] >= START_YEAR][[
            "municipality_code", "municipality_name", "year", "population_growth"
        ]].copy()

        logger.info(f"Computed population growth: {len(result)} rows, "
                   f"mean growth: {result['population_growth'].mean():.2f}%")

        return result

    def clean_tax_base(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean tax base data (share of national average).

        Args:
            df: Tax base DataFrame from SCB

        Returns:
            DataFrame with columns: municipality_code, municipality_name, year, tax_base_relative
        """
        logger.info("Cleaning tax base data...")

        df = df.copy()

        # The value is already "share of national average" in percent
        df = df.rename(columns={"value": "tax_base_relative"})

        # Select final columns
        result = df[[
            "municipality_code", "municipality_name", "year", "tax_base_relative"
        ]].copy()

        # Remove duplicates if any
        result = result.drop_duplicates(
            subset=["municipality_code", "year"],
            keep="first"
        )

        logger.info(f"Cleaned tax base: {len(result)} rows, "
                   f"mean tax base: {result['tax_base_relative'].mean():.1f}%")

        return result

    def clean_unemployment(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean unemployment data from Kolada.

        Args:
            df: Unemployment DataFrame from Kolada

        Returns:
            DataFrame with columns: municipality_code, municipality_name, year, unemployment
        """
        logger.info("Cleaning unemployment data...")

        df = df.copy()

        # Rename column
        if "unemployment_pct" in df.columns:
            df = df.rename(columns={"unemployment_pct": "unemployment"})
        elif "value" in df.columns:
            df = df.rename(columns={"value": "unemployment"})

        # Ensure municipality_name exists
        if "municipality_name" not in df.columns or df["municipality_name"].isna().all():
            df["municipality_name"] = df["municipality_code"].map(MUNICIPALITIES)

        # Select final columns
        result = df[[
            "municipality_code", "municipality_name", "year", "unemployment"
        ]].copy()

        # Remove duplicates
        result = result.drop_duplicates(
            subset=["municipality_code", "year"],
            keep="first"
        )

        logger.info(f"Cleaned unemployment: {len(result)} rows, "
                   f"mean unemployment: {result['unemployment'].mean():.2f}%")

        return result

    def merge_all(
        self,
        debt_df: pd.DataFrame,
        unemployment_df: pd.DataFrame,
        dependency_df: pd.DataFrame,
        population_df: pd.DataFrame,
        tax_base_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Merge all cleaned data into a single analysis DataFrame.

        Args:
            debt_df: Cleaned debt per capita data
            unemployment_df: Cleaned unemployment data
            dependency_df: Cleaned dependency ratio data
            population_df: Cleaned population growth data
            tax_base_df: Cleaned tax base data

        Returns:
            Merged DataFrame with all variables
        """
        logger.info("Merging all datasets...")

        # Start with debt data as base
        result = debt_df.copy()

        # Merge unemployment
        result = result.merge(
            unemployment_df[["municipality_code", "year", "unemployment"]],
            on=["municipality_code", "year"],
            how="outer"
        )

        # Merge dependency ratio
        result = result.merge(
            dependency_df[["municipality_code", "year", "dependency_ratio"]],
            on=["municipality_code", "year"],
            how="outer"
        )

        # Merge population growth
        result = result.merge(
            population_df[["municipality_code", "year", "population_growth"]],
            on=["municipality_code", "year"],
            how="outer"
        )

        # Merge tax base
        result = result.merge(
            tax_base_df[["municipality_code", "year", "tax_base_relative"]],
            on=["municipality_code", "year"],
            how="outer"
        )

        # Fill municipality names where missing
        name_map = {**MUNICIPALITIES}
        # Also build from the data
        for df in [debt_df, unemployment_df, dependency_df, population_df, tax_base_df]:
            if "municipality_name" in df.columns:
                for _, row in df[["municipality_code", "municipality_name"]].drop_duplicates().iterrows():
                    if pd.notna(row["municipality_name"]):
                        name_map[row["municipality_code"]] = row["municipality_name"]

        result["municipality_name"] = result["municipality_code"].map(name_map)

        # Filter to valid municipalities and years
        result = result[
            result["municipality_code"].isin(MUNICIPALITIES.keys()) &
            (result["year"] >= START_YEAR) &
            (result["year"] <= END_YEAR)
        ]

        # Sort
        result = result.sort_values(["municipality_code", "year"])

        logger.info(f"Merged dataset: {len(result)} rows, "
                   f"{result['municipality_code'].nunique()} municipalities, "
                   f"{result['year'].nunique()} years")

        return result

    def validate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate the merged dataset for completeness and quality.

        Args:
            df: Merged analysis DataFrame

        Returns:
            Validation report dictionary with:
            - total_rows: Total number of rows
            - municipalities: Number of unique municipalities
            - years: Number of years
            - missing_by_variable: Count of missing values per variable
            - missing_by_municipality: Municipalities with most missing data
            - completeness_rate: Overall data completeness percentage
            - flagged_municipalities: List of municipalities with issues
        """
        logger.info("Validating merged dataset...")

        self.validation_issues = []

        variables = [
            "debt_per_capita", "unemployment", "dependency_ratio",
            "population_growth", "tax_base_relative"
        ]

        # Basic counts
        total_rows = len(df)
        n_municipalities = df["municipality_code"].nunique()
        n_years = df["year"].nunique()

        # Missing values by variable
        missing_by_variable = {}
        for var in variables:
            if var in df.columns:
                missing_count = df[var].isna().sum()
                missing_pct = (missing_count / total_rows) * 100
                missing_by_variable[var] = {
                    "missing_count": int(missing_count),
                    "missing_percent": round(missing_pct, 2)
                }

        # Missing values by municipality
        df["missing_count"] = df[variables].isna().sum(axis=1)
        missing_by_muni = df.groupby("municipality_code")["missing_count"].sum()
        worst_municipalities = missing_by_muni.nlargest(10).to_dict()

        # Completeness rate
        total_cells = total_rows * len(variables)
        total_missing = sum(v["missing_count"] for v in missing_by_variable.values())
        completeness_rate = ((total_cells - total_missing) / total_cells) * 100

        # Flagged municipalities
        flagged = []

        # Check special cases
        for code, info in SPECIAL_CASES.items():
            if code in df["municipality_code"].values:
                flagged.append({
                    "municipality_code": code,
                    "municipality_name": info["name"],
                    "flag": info["note"]
                })

        # Check for municipalities with high missing data (>20% missing)
        muni_missing_pct = (
            df.groupby("municipality_code")[variables]
            .apply(lambda x: x.isna().sum().sum() / (len(x) * len(variables)) * 100)
        )
        high_missing = muni_missing_pct[muni_missing_pct > 20]
        for code, pct in high_missing.items():
            flagged.append({
                "municipality_code": code,
                "municipality_name": MUNICIPALITIES.get(code, "Unknown"),
                "flag": f"High missing data: {pct:.1f}% of values missing"
            })

        # Expected vs actual municipalities
        expected_rows = len(MUNICIPALITIES) * len(YEARS)
        actual_municipalities = set(df["municipality_code"].unique())
        missing_municipalities = set(MUNICIPALITIES.keys()) - actual_municipalities

        validation_report = {
            "total_rows": total_rows,
            "expected_rows": expected_rows,
            "municipalities": n_municipalities,
            "expected_municipalities": len(MUNICIPALITIES),
            "years": n_years,
            "expected_years": len(YEARS),
            "missing_by_variable": missing_by_variable,
            "worst_municipalities": worst_municipalities,
            "completeness_rate": round(completeness_rate, 2),
            "flagged_municipalities": flagged,
            "missing_municipalities": list(missing_municipalities),
        }

        # Log summary
        logger.info(f"Validation complete:")
        logger.info(f"  Rows: {total_rows} / {expected_rows} expected")
        logger.info(f"  Municipalities: {n_municipalities} / {len(MUNICIPALITIES)}")
        logger.info(f"  Completeness: {completeness_rate:.1f}%")
        logger.info(f"  Flagged municipalities: {len(flagged)}")

        for var, stats in missing_by_variable.items():
            if stats["missing_count"] > 0:
                logger.warning(f"  {var}: {stats['missing_count']} missing ({stats['missing_percent']:.1f}%)")

        return validation_report

    def handle_missing_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Handle missing data using interpolation and extrapolation.

        Strategy:
        - Single missing years: Linear interpolation
        - Missing at start: Forward fill from first available
        - Missing at end: Backward fill from last available
        - More than 3 consecutive missing: Leave as NaN (flagged)

        Args:
            df: DataFrame with potential missing values

        Returns:
            DataFrame with missing values handled where possible
        """
        logger.info("Handling missing data...")

        df = df.copy()

        variables = [
            "debt_per_capita", "unemployment", "dependency_ratio",
            "population_growth", "tax_base_relative"
        ]

        # Process each municipality separately
        for code in df["municipality_code"].unique():
            mask = df["municipality_code"] == code

            for var in variables:
                if var not in df.columns:
                    continue

                # Get the series for this municipality
                series = df.loc[mask, var].copy()

                if series.isna().all():
                    continue

                # Count consecutive NaNs
                # Interpolate only if gap is <= 2 years
                interpolated = series.interpolate(method="linear", limit=2)

                # Forward fill for start (limit 2)
                interpolated = interpolated.ffill(limit=2)

                # Backward fill for end (limit 2)
                interpolated = interpolated.bfill(limit=2)

                df.loc[mask, var] = interpolated

        # Log results
        for var in variables:
            if var in df.columns:
                remaining_missing = df[var].isna().sum()
                if remaining_missing > 0:
                    logger.info(f"  {var}: {remaining_missing} values still missing after interpolation")

        return df

    def run_pipeline(
        self,
        raw_data: Dict[str, pd.DataFrame],
        save_output: bool = True
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Run the complete data cleaning pipeline.

        Args:
            raw_data: Dictionary of raw DataFrames from data fetchers
            save_output: Whether to save the output to parquet

        Returns:
            Tuple of (cleaned DataFrame, validation report)
        """
        logger.info("=" * 60)
        logger.info("Starting data cleaning pipeline...")
        logger.info("=" * 60)

        # Clean balance sheet (debt per capita)
        debt_df = self.clean_balance_sheet(
            raw_data["balance_sheet"],
            raw_data["population"]
        )

        # Clean unemployment
        unemployment_df = self.clean_unemployment(raw_data["unemployment"])

        # Compute dependency ratio (prefer Kolada working_age data if available)
        working_age_df = raw_data.get("working_age")
        dependency_df = self.compute_dependency_ratio(
            raw_data["population"],
            working_age_df
        )

        # Compute population growth
        population_df = self.compute_population_growth(raw_data["population"])

        # Clean tax base
        tax_base_df = self.clean_tax_base(raw_data["tax_base"])

        # Merge all
        merged_df = self.merge_all(
            debt_df, unemployment_df, dependency_df, population_df, tax_base_df
        )

        # Handle missing data
        merged_df = self.handle_missing_data(merged_df)

        # Validate
        validation_report = self.validate(merged_df)

        # Save output
        if save_output:
            output_path = self.processed_dir / "kri_base_data.parquet"
            merged_df.to_parquet(output_path, index=False)
            logger.info(f"Saved cleaned data to: {output_path}")

        logger.info("=" * 60)
        logger.info("Data cleaning pipeline complete!")
        logger.info("=" * 60)

        return merged_df, validation_report


def clean_data(raw_data: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Convenience function to run the data cleaning pipeline.

    Args:
        raw_data: Dictionary of raw DataFrames from fetch_all_data()

    Returns:
        Tuple of (cleaned DataFrame, validation report)
    """
    cleaner = DataCleaner()
    return cleaner.run_pipeline(raw_data)


if __name__ == "__main__":
    # Test the data cleaner with cached data
    from src.data_fetcher import fetch_all_data

    print("Testing data cleaner...")
    print("-" * 50)

    # Fetch data (will use cache if available)
    raw_data = fetch_all_data(use_cache=True)

    # Run cleaning pipeline
    cleaner = DataCleaner()
    df, report = cleaner.run_pipeline(raw_data)

    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    print(f"\nDataset shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nSample data:")
    print(df.head(10).to_string())

    print(f"\nValidation report:")
    print(f"  Completeness: {report['completeness_rate']}%")
    print(f"  Flagged municipalities: {len(report['flagged_municipalities'])}")

    print("\n" + "=" * 50)
    print("Test complete!")
