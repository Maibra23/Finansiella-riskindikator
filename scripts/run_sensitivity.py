"""Compute the KRI weight-sensitivity band and write it to parquet.

Run from the project root, after the index has been built:

    python scripts/run_sensitivity.py

Writes data/processed/kri_sensitivity.parquet.  That file is committed to the
repository for the same reason kri_results.parquet is: Streamlit Cloud cannot
run the pipeline at request time.

The output is deterministic, the seed lives in config.SENSITIVITY, so re-running
this script on unchanged input rewrites an identical file.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.config import SENSITIVITY
from src.sensitivity import SensitivityConfig, compute_sensitivity, summarise

RESULTS_PATH = PROJECT_ROOT / "data" / "processed" / "kri_results.parquet"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "kri_sensitivity.parquet"


def main(output_path: Path = OUTPUT_PATH) -> int:
    if not RESULTS_PATH.exists():
        print(f"ERROR: {RESULTS_PATH} not found.", file=sys.stderr)
        print("       Build the index first: python -c "
              "\"from src.index_builder import KRIBuilder; KRIBuilder().build()\"", file=sys.stderr)
        return 1

    kri_df = pd.read_parquet(RESULTS_PATH)
    config = SensitivityConfig()

    print("=" * 70)
    print("  KRI WEIGHT SENSITIVITY")
    print("=" * 70)
    print(f"  draws            : {config.n_draws}")
    print(f"  delta            : +-{config.delta}")
    print(f"  robust threshold : {config.robust_threshold:.0%} of draws")
    print(f"  seed             : {config.seed}")

    sensitivity_df = compute_sensitivity(kri_df, config)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sensitivity_df.to_parquet(output_path, index=False)

    print(f"\n  wrote {len(sensitivity_df)} rows to {output_path.relative_to(PROJECT_ROOT)} "
          f"({output_path.stat().st_size / 1024:.0f} KB)")

    print("\n" + "-" * 70)
    print(f"  {'year':<6}{'robust':>9}{'gränsfall':>12}{'modal≠publ':>13}{'median band':>14}")
    print("-" * 70)
    for year in sorted(kri_df["year"].unique()):
        s = summarise(kri_df, sensitivity_df, int(year))
        print(f"  {year:<6}{s['robust']:>6}/{s['n']:<3}{s['fragile']:>11}"
              f"{s['modal_disagreements']:>13}{s['median_band']:>11.0f} platser")

    latest = int(kri_df["year"].max())
    s = summarise(kri_df, sensitivity_df, latest)
    print("-" * 70)
    if s["modal_disagreements"] > 5:
        print(f"\n  WARNING: the most frequent class differs from the published class for "
              f"{s['modal_disagreements']} municipalities in {latest}.")
        print("           That is a finding about the index, not about this script, "
              "investigate before publishing.")
    else:
        print(f"\n  {latest}: the published risk class is also the most frequent class for "
              f"{s['n'] - s['modal_disagreements']}/{s['n']} municipalities.")
        print("  The sensitivity analysis corroborates the index rather than contradicting it.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute the KRI weight-sensitivity band")
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Destination parquet (default: data/processed/kri_sensitivity.parquet)",
    )
    args = parser.parse_args()
    sys.exit(main(output_path=args.output))
