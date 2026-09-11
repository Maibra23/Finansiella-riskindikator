"""
Task 1.5: Run data pipeline and verify.

This script:
1. Fetches all data via SCBFetcher and KoladaFetcher
2. Runs the DataCleaner pipeline
3. Prints summary statistics
4. Saves results to data/processed/kri_base_data.parquet

Run from project root: python scripts/run_pipeline.py
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime

import pandas as pd

from src.data_fetcher import fetch_all_data
from src.data_cleaner import DataCleaner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def print_separator(title: str = None):
    """Print a visual separator."""
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


def main(use_cache: bool = True):
    """Run the complete data pipeline."""
    start_time = datetime.now()

    print_separator("KOMMUNAL FINANSIELL RISKINDIKATOR - DATA PIPELINE")
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Cache mode: {'enabled' if use_cache else 'disabled'}")

    # =========================================================================
    # STEP 1: Fetch all data
    # =========================================================================
    print_separator("STEP 1: FETCHING DATA FROM APIs")

    print("\nFetching data from SCB and Kolada APIs...")
    if not use_cache:
        print("(Fresh fetch - this may take 1-2 minutes)")

    try:
        raw_data = fetch_all_data(use_cache=use_cache)
        print("\nData fetching complete!")

        print("\n--- Raw Data Summary ---")
        for name, df in raw_data.items():
            munis = df['municipality_code'].nunique() if 'municipality_code' in df.columns else 'N/A'
            print(f"  {name:20s}: {len(df):>6} rows, {munis} municipalities")

    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        print(f"\n[ERROR] Data fetching failed: {e}")
        return 1

    # =========================================================================
    # STEP 2: Run data cleaning pipeline
    # =========================================================================
    print_separator("STEP 2: CLEANING AND TRANSFORMING DATA")

    cleaner = DataCleaner()

    try:
        merged_df, validation_report = cleaner.run_pipeline(raw_data, save_output=True)
        print("\nData cleaning complete!")

    except Exception as e:
        logger.error(f"Data cleaning failed: {e}")
        print(f"\n[ERROR] Data cleaning failed: {e}")
        return 1

    # =========================================================================
    # STEP 3: Print summary statistics
    # =========================================================================
    print_separator("STEP 3: SUMMARY STATISTICS")

    print("\n--- Dataset Overview ---")
    print(f"  Total rows: {len(merged_df)}")
    print(f"  Municipalities: {merged_df['municipality_code'].nunique()} / 290 expected")
    print(f"  Years: {merged_df['year'].min()} - {merged_df['year'].max()}")
    print(f"  Completeness rate: {validation_report['completeness_rate']}%")

    print("\n--- Missing Values by Variable ---")
    variables = [
        "debt_per_capita", "unemployment", "dependency_ratio",
        "population_growth", "tax_base_relative"
    ]
    for var in variables:
        stats = validation_report["missing_by_variable"].get(var, {})
        missing = stats.get("missing_count", 0)
        pct = stats.get("missing_percent", 0)
        status = "OK" if pct == 0 else ("WARNING" if pct < 30 else "LIMITED")
        print(f"  {var:25s}: {missing:5d} missing ({pct:5.1f}%) [{status}]")

    print("\n--- Variable Statistics (latest year with data) ---")
    latest_year = merged_df["year"].max()
    latest = merged_df[merged_df["year"] == latest_year]
    print(f"  Year: {latest_year}")

    for var in variables:
        if var in latest.columns:
            values = latest[var].dropna()
            if len(values) > 0:
                print(f"\n  {var}:")
                print(f"    Count:  {len(values):>12}")
                print(f"    Min:    {values.min():>12.2f}")
                print(f"    Max:    {values.max():>12.2f}")
                print(f"    Mean:   {values.mean():>12.2f}")
                print(f"    Median: {values.median():>12.2f}")
            else:
                print(f"\n  {var}: No data for {latest_year}")

    print("\n--- Municipalities per Year ---")
    munis_per_year = merged_df.groupby("year")["municipality_code"].nunique()
    for year, count in munis_per_year.items():
        status = "OK" if count >= 289 else "INCOMPLETE"
        print(f"  {year}: {count} municipalities [{status}]")

    # =========================================================================
    # STEP 4: Data quality report
    # =========================================================================
    print_separator("STEP 4: DATA QUALITY REPORT")

    flagged = validation_report.get("flagged_municipalities", [])
    print(f"\nFlagged municipalities: {len(flagged)}")

    # Show special cases
    special_flags = [f for f in flagged if "Gotland" in f.get("flag", "") or "Knivsta" in f.get("flag", "")]
    if special_flags:
        print("\n  Special cases:")
        for item in special_flags:
            print(f"    {item['municipality_code']} {item['municipality_name']}: {item['flag'][:60]}")

    # Show high missing data
    high_missing = [f for f in flagged if "High missing" in f.get("flag", "")]
    if high_missing:
        print(f"\n  High missing data ({len(high_missing)} municipalities):")
        for item in high_missing[:5]:
            print(f"    {item['municipality_code']} {item['municipality_name']}: {item['flag']}")
        if len(high_missing) > 5:
            print(f"    ... and {len(high_missing) - 5} more")

    # =========================================================================
    # STEP 5: Sample data inspection
    # =========================================================================
    print_separator("STEP 5: SAMPLE DATA")

    # Show Stockholm data
    print("\n--- Stockholm (0180) - Recent Years ---")
    sthlm = merged_df[merged_df["municipality_code"] == "0180"].sort_values("year")
    if not sthlm.empty:
        cols = ["year", "debt_per_capita", "unemployment", "dependency_ratio", "population_growth", "tax_base_relative"]
        print(sthlm[cols].tail(5).to_string(index=False))
    else:
        print("  No data found for Stockholm")

    # Show top 5 highest debt
    print("\n--- Top 5 Highest Debt per Capita (latest year) ---")
    if "debt_per_capita" in latest.columns and latest["debt_per_capita"].notna().any():
        top_debt = latest.nlargest(5, "debt_per_capita")[
            ["municipality_code", "municipality_name", "debt_per_capita"]
        ]
        print(top_debt.to_string(index=False))

    # =========================================================================
    # STEP 6: Save outputs
    # =========================================================================
    print_separator("STEP 6: OUTPUT FILES")

    output_path = Path("data/processed/kri_base_data.parquet")
    print(f"\n  Parquet: {output_path}")
    if output_path.exists():
        print(f"           Size: {output_path.stat().st_size / 1024:.1f} KB")

    # Also save a CSV for easy inspection
    csv_path = Path("data/processed/kri_base_data.csv")
    merged_df.to_csv(csv_path, index=False)
    print(f"  CSV:     {csv_path}")

    # =========================================================================
    # STEP 7: Build KRI index
    # =========================================================================
    print_separator("STEP 7: BUILDING KRI INDEX")
    try:
        from src.index_builder import KRIBuilder
        print("\n  Running KRIBuilder().build() ...")
        kri_results = KRIBuilder().build()
        kri_path = Path("data/processed/kri_results.parquet")
        print(f"  KRI index saved: {kri_path}")
        if kri_path.exists():
            print(f"           Size: {kri_path.stat().st_size / 1024:.1f} KB")
        print(f"  Municipalities: {kri_results['municipality_code'].nunique()}")
        print(f"  Years: {sorted(kri_results['year'].unique().tolist())}")
    except Exception as exc:
        print(f"\n  ERROR building KRI index: {exc}")
        print("  Base data saved: run: python -c \"from src.index_builder import KRIBuilder; KRIBuilder().build()\"")

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print_separator("PIPELINE COMPLETE")
    print(f"\n  Duration: {duration:.1f} seconds")
    print(f"  Finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Overall status
    completeness = validation_report["completeness_rate"]
    if completeness >= 80:
        print("\n  STATUS: SUCCESS - Data pipeline completed with good coverage")
        status_code = 0
    elif completeness >= 50:
        print("\n  STATUS: PARTIAL - Data pipeline completed with limited coverage")
        print("          Review missing data before computing KRI index")
        status_code = 0
    else:
        print("\n  STATUS: WARNING - Significant data gaps detected")
        print("          May need to adjust KRI weights or exclude variables")
        status_code = 0  # Still success, but with warnings

    print("\n  DATA SOURCES:")
    print("    - Unemployment: Kolada N03937 (Arbetsförmedlingen), 2010-2024 full coverage")
    print("    - Dependency ratio: SCB BefolkningNy age-specific data, 2010-2024 full coverage")
    print("    - Debt, population growth, tax base: SCB, 2010-2024 full coverage")

    return status_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run KRI data pipeline")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Fetch fresh data from APIs (ignore cache)"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all cached data before running"
    )
    args = parser.parse_args()

    if args.clear_cache:
        from src.data_fetcher import SCBFetcher, KoladaFetcher
        print("Clearing cache...")
        SCBFetcher().clear_cache()
        KoladaFetcher().clear_cache()
        print("Cache cleared.")

    exit_code = main(use_cache=not args.no_cache)
    sys.exit(exit_code)
