"""
Pipeline runner script for KRI data processing.

This script fetches all data from SCB and Kolada APIs,
runs the data cleaning pipeline, and outputs summary statistics.

Usage:
    python scripts/run_pipeline.py [--no-cache]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data_fetcher import fetch_all_data, SCBFetcher, KoladaFetcher
from src.data_cleaner import DataCleaner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main(use_cache: bool = True):
    """
    Run the complete data pipeline.

    Args:
        use_cache: Whether to use cached API responses
    """
    print("=" * 70)
    print("KOMMUNAL FINANSIELL RISKINDIKATOR - Data Pipeline")
    print("=" * 70)
    print()

    # Step 1: Fetch all data
    print("STEP 1: Fetching data from APIs...")
    print("-" * 70)

    try:
        raw_data = fetch_all_data(use_cache=use_cache)
        print("\nData fetched successfully!")
        print("\nRaw data summary:")
        for name, df in raw_data.items():
            print(f"  {name:20s}: {len(df):>6} rows, {df['municipality_code'].nunique():>3} municipalities")
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        raise

    print()

    # Step 2: Clean and transform data
    print("STEP 2: Cleaning and transforming data...")
    print("-" * 70)

    cleaner = DataCleaner()
    df, validation_report = cleaner.run_pipeline(raw_data)

    print()

    # Step 3: Print summary statistics
    print("STEP 3: Summary Statistics")
    print("-" * 70)

    print(f"\nDataset dimensions:")
    print(f"  Total rows:         {len(df)}")
    print(f"  Municipalities:     {df['municipality_code'].nunique()}")
    print(f"  Years:              {df['year'].min()} - {df['year'].max()}")

    print(f"\nVariable statistics:")
    variables = ["debt_per_capita", "unemployment", "dependency_ratio", "population_growth", "tax_base_relative"]

    for var in variables:
        if var in df.columns:
            stats = df[var].describe()
            missing = df[var].isna().sum()
            print(f"\n  {var}:")
            print(f"    Min:     {stats['min']:>12.2f}")
            print(f"    Max:     {stats['max']:>12.2f}")
            print(f"    Mean:    {stats['mean']:>12.2f}")
            print(f"    Median:  {stats['50%']:>12.2f}")
            print(f"    Missing: {missing:>12} ({missing/len(df)*100:.1f}%)")

    print()

    # Step 4: Data quality report
    print("STEP 4: Data Quality Report")
    print("-" * 70)

    print(f"\nCompleteness rate: {validation_report['completeness_rate']}%")

    if validation_report['missing_municipalities']:
        print(f"\nMissing municipalities ({len(validation_report['missing_municipalities'])}):")
        for code in validation_report['missing_municipalities'][:10]:
            print(f"  - {code}")
        if len(validation_report['missing_municipalities']) > 10:
            print(f"  ... and {len(validation_report['missing_municipalities']) - 10} more")

    if validation_report['flagged_municipalities']:
        print(f"\nFlagged municipalities ({len(validation_report['flagged_municipalities'])}):")
        for flag in validation_report['flagged_municipalities']:
            print(f"  - {flag['municipality_code']} {flag['municipality_name']}: {flag['flag']}")

    print()

    # Step 5: Sample data
    print("STEP 5: Sample Data (Stockholm, 2024)")
    print("-" * 70)

    stockholm = df[(df["municipality_code"] == "0180") & (df["year"] == 2024)]
    if not stockholm.empty:
        print(stockholm.to_string(index=False))
    else:
        # Try latest available year for Stockholm
        stockholm = df[df["municipality_code"] == "0180"].sort_values("year", ascending=False).head(1)
        if not stockholm.empty:
            print(f"(Latest available year: {stockholm['year'].values[0]})")
            print(stockholm.to_string(index=False))

    print()
    print("=" * 70)
    print("Pipeline complete! Data saved to: data/processed/kri_base_data.parquet")
    print("=" * 70)

    return df, validation_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run KRI data pipeline")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Fetch fresh data from APIs (ignore cache)"
    )
    args = parser.parse_args()

    main(use_cache=not args.no_cache)
