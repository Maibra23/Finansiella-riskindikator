"""
Full Data Audit for Kommunal Finansiell Riskindikator (KRI) pipeline.

Checks:
  1.  File integrity       - load parquet, verify columns/dtypes/shape
  2.  Completeness         - zero NaN across all variables, municipalities, years
  3.  Municipality coverage - all 290 codes from config.MUNICIPALITIES present
  4.  Year coverage         - exactly 2010-2024 (15 years)
  5.  Value range checks    - per-variable bounds
  6.  Cross-variable consistency - impossible value combinations
  7.  Temporal consistency  - no single-year jumps > 3 SD
  8.  Known benchmarks      - spot-check vs published SCB/AF data
  9.  Duplicate check       - no (municipality_code, year) duplicates
  10. Data types            - year=int, numerics=float
  11. Cache file existence  - all 7 expected cache parquets present
"""

import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "kri_base_data.parquet")

CACHE_FILES = {
    "balance_sheet":       os.path.join(PROJECT_ROOT, "data", "cache", "balance_sheet.parquet"),
    "population":          os.path.join(PROJECT_ROOT, "data", "cache", "population.parquet"),
    "tax_base":            os.path.join(PROJECT_ROOT, "data", "cache", "tax_base.parquet"),
    "income_statement":    os.path.join(PROJECT_ROOT, "data", "cache", "income_statement.parquet"),
    "tax_rate":            os.path.join(PROJECT_ROOT, "data", "cache", "tax_rate.parquet"),
    "population_by_age":   os.path.join(PROJECT_ROOT, "data", "cache", "population_by_age.parquet"),
    "kolada_unemployment": os.path.join(PROJECT_ROOT, "data", "cache", "kolada_unemployment.parquet"),
}

# ---------------------------------------------------------------------------
# Import config MUNICIPALITIES dict (add project root to sys.path)
# ---------------------------------------------------------------------------
sys.path.insert(0, PROJECT_ROOT)
try:
    from src.config import MUNICIPALITIES
    CONFIG_LOADED = True
except Exception as exc:
    print(f"  [WARNING] Could not import src.config: {exc}")
    MUNICIPALITIES = {}
    CONFIG_LOADED = False

# ---------------------------------------------------------------------------
# Expected schema
# ---------------------------------------------------------------------------
EXPECTED_COLUMNS = [
    "municipality_code",
    "year",
    "debt_per_capita",
    "unemployment",
    "dependency_ratio",
    "population_growth",
    "tax_base_relative",
]

NUMERIC_COLS = [
    "debt_per_capita",
    "unemployment",
    "dependency_ratio",
    "population_growth",
    "tax_base_relative",
]

EXPECTED_YEARS = list(range(2010, 2025))   # 2010..2024 inclusive
EXPECTED_N_MUNICIPALITIES = 290
EXPECTED_N_YEARS = 15
EXPECTED_ROWS = EXPECTED_N_MUNICIPALITIES * EXPECTED_N_YEARS  # 4 350

# Value range specs  (min_ok, max_ok, label)
VALUE_RANGES = {
    "debt_per_capita":    (-1_000,  200_000, "SEK/capita"),  # long-term debt (post 089); SCB reports 0 for some municipalities
    "unemployment":       (0,       15,      "%"),
    "dependency_ratio":   (0.3,     1.5,     "ratio"),
    "population_growth":  (-20,     30,      "%"),
    "tax_base_relative":  (50,      220,     "%"),
}

# Variables to check for temporal jumps (> 3 SD year-over-year per municipality)
TEMPORAL_VARS = ["debt_per_capita", "unemployment", "dependency_ratio"]

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"

results: list[dict] = []

def record(check_id: int, name: str, status: str, detail: str) -> None:
    tag = f"[{status}]"
    results.append({"id": check_id, "name": name, "status": status, "detail": detail})
    print(f"  {tag:<8} {name}")
    if detail:
        for line in detail.strip().splitlines():
            print(f"           {line}")

def section(title: str) -> None:
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
section("CHECK 1, File Integrity")

try:
    df = pd.read_parquet(PARQUET_PATH)
    file_ok = True
    record(1, "Parquet loads without error", PASS,
           f"Path: {PARQUET_PATH}")
except Exception as exc:
    record(1, "Parquet loads without error", FAIL, str(exc))
    print("\nCannot continue, parquet failed to load.")
    sys.exit(1)

# Columns
missing_cols = [c for c in EXPECTED_COLUMNS if c not in df.columns]
extra_cols   = [c for c in df.columns if c not in EXPECTED_COLUMNS]
if missing_cols:
    record(1, "Expected columns present", FAIL,
           f"Missing: {missing_cols}\nExtra: {extra_cols}\nActual: {list(df.columns)}")
else:
    detail = f"Shape: {df.shape}  |  Columns: {list(df.columns)}"
    if extra_cols:
        detail += f"\n  Extra (non-breaking) columns: {extra_cols}"
    record(1, "Expected columns present", PASS, detail)

# Shape
shape_ok = df.shape[0] == EXPECTED_ROWS
record(1, f"Row count == {EXPECTED_ROWS} (290 muni × 15 years)",
       PASS if shape_ok else WARN,
       f"Actual rows: {df.shape[0]}  |  Expected: {EXPECTED_ROWS}")

# ---------------------------------------------------------------------------
section("CHECK 2, Completeness (zero NaN)")
# ---------------------------------------------------------------------------

any_nan_fail = False
for col in EXPECTED_COLUMNS:
    if col not in df.columns:
        record(2, f"NaN check: {col}", FAIL, "Column not present, skipped")
        continue
    n_nan = int(df[col].isna().sum())
    pct   = n_nan / len(df) * 100
    if n_nan == 0:
        record(2, f"NaN check: {col}", PASS, "0 missing values")
    else:
        any_nan_fail = True
        # Show which muni/years are affected
        bad = df[df[col].isna()][["municipality_code", "year"]].head(10)
        record(2, f"NaN check: {col}", FAIL,
               f"{n_nan} missing ({pct:.2f}%)\nSample affected rows:\n{bad.to_string(index=False)}")

# ---------------------------------------------------------------------------
section("CHECK 3, Municipality Coverage (290 codes from config)")
# ---------------------------------------------------------------------------

actual_codes  = set(df["municipality_code"].unique())
config_codes  = set(MUNICIPALITIES.keys())

if not CONFIG_LOADED:
    record(3, "Config MUNICIPALITIES imported", WARN,
           "src.config not importable, skipping coverage diff")
else:
    record(3, "Config MUNICIPALITIES imported", PASS,
           f"{len(config_codes)} codes in config")

    missing_in_data  = config_codes - actual_codes
    extra_in_data    = actual_codes - config_codes

    if missing_in_data:
        record(3, "All 290 config codes present in data", FAIL,
               f"{len(missing_in_data)} codes missing: {sorted(missing_in_data)}")
    else:
        record(3, "All 290 config codes present in data", PASS, "")

    if extra_in_data:
        record(3, "No unexpected codes in data", WARN,
               f"{len(extra_in_data)} unexpected codes: {sorted(extra_in_data)}")
    else:
        record(3, "No unexpected codes in data", PASS, "")

n_actual = df["municipality_code"].nunique()
record(3, f"Unique municipality count == {EXPECTED_N_MUNICIPALITIES}",
       PASS if n_actual == EXPECTED_N_MUNICIPALITIES else FAIL,
       f"Actual unique codes: {n_actual}")

# ---------------------------------------------------------------------------
section("CHECK 4: Year Coverage (2010-2024, exactly 15 years)")
# ---------------------------------------------------------------------------

actual_years = sorted(df["year"].unique().tolist())
missing_years = [y for y in EXPECTED_YEARS if y not in actual_years]
extra_years   = [y for y in actual_years if y not in EXPECTED_YEARS]

record(4, "All 15 years present (2010-2024)",
       PASS if not missing_years else FAIL,
       f"Actual years: {actual_years}"
       + (f"\nMissing: {missing_years}" if missing_years else ""))

if extra_years:
    record(4, "No unexpected years in data", WARN,
           f"Extra years found: {extra_years}")
else:
    record(4, "No unexpected years in data", PASS, "")

record(4, f"Year count == {EXPECTED_N_YEARS}",
       PASS if len(actual_years) == EXPECTED_N_YEARS else FAIL,
       f"Unique years: {len(actual_years)}")

# ---------------------------------------------------------------------------
section("CHECK 5, Value Range Checks")
# ---------------------------------------------------------------------------

for col, (lo, hi, unit) in VALUE_RANGES.items():
    if col not in df.columns:
        record(5, f"Range check: {col}", FAIL, "Column missing")
        continue
    series = df[col].dropna()
    n_low  = int((series < lo).sum())
    n_high = int((series > hi).sum())
    total_out = n_low + n_high

    summary = (f"Range [{lo:,}: {hi:,}] {unit}  |  "
               f"Data min={series.min():.4g}  max={series.max():.4g}  "
               f"mean={series.mean():.4g}  median={series.median():.4g}")

    if total_out == 0:
        record(5, f"Range check: {col}", PASS, summary)
    else:
        # Show worst outliers
        outliers = df[(df[col] < lo) | (df[col] > hi)][
            ["municipality_code", "year", col]
        ].copy()
        outliers["direction"] = np.where(
            outliers[col] < lo, f"<{lo}", f">{hi}"
        )
        outliers = outliers.sort_values(col).head(15)
        record(5, f"Range check: {col}", WARN,
               f"{n_low} below {lo}, {n_high} above {hi}\n{summary}\n"
               f"Worst outliers (up to 15):\n{outliers.to_string(index=False)}")

# ---------------------------------------------------------------------------
section("CHECK 6, Cross-Variable Consistency")
# ---------------------------------------------------------------------------

# Flag municipalities where BOTH debt_per_capita AND tax_base_relative are
# simultaneously in the top-decile (nationally, per year), unusual but not
# impossible.  We look for year-level decile overlap and flag if > 5 % of
# municipality-year pairs show this.
if all(c in df.columns for c in ["debt_per_capita", "tax_base_relative"]):
    df["_debt_pct"]  = df.groupby("year")["debt_per_capita"].transform(
        lambda s: s.rank(pct=True))
    df["_tax_pct"]   = df.groupby("year")["tax_base_relative"].transform(
        lambda s: s.rank(pct=True))
    both_top = df[(df["_debt_pct"] >= 0.90) & (df["_tax_pct"] >= 0.90)]
    pct_flagged = len(both_top) / len(df) * 100
    if len(both_top) == 0:
        record(6, "High-debt + high-tax-base co-occurrence", PASS,
               "No municipality-years in top decile of BOTH debt and tax base")
    else:
        record(6, "High-debt + high-tax-base co-occurrence", WARN,
               f"{len(both_top)} muni-year pairs ({pct_flagged:.2f}%) have "
               f"top-decile debt AND top-decile tax base\n"
               f"{both_top[['municipality_code','year','debt_per_capita','tax_base_relative']].head(10).to_string(index=False)}")
    df.drop(columns=["_debt_pct", "_tax_pct"], inplace=True)
else:
    record(6, "High-debt + high-tax-base co-occurrence", WARN,
           "Required columns missing, skipped")

# Flag impossibly negative dependency_ratio or unemployment
if "dependency_ratio" in df.columns:
    neg_dr = int((df["dependency_ratio"] < 0).sum())
    record(6, "No negative dependency_ratio values",
           PASS if neg_dr == 0 else FAIL,
           f"Negative count: {neg_dr}")

if "unemployment" in df.columns:
    neg_u = int((df["unemployment"] < 0).sum())
    record(6, "No negative unemployment values",
           PASS if neg_u == 0 else FAIL,
           f"Negative count: {neg_u}")

# Flag municipalities with unemployment > 10% AND dependency_ratio < 0.5
# (extremely unusual, very high jobless but almost no dependents)
if all(c in df.columns for c in ["unemployment", "dependency_ratio"]):
    paradox = df[(df["unemployment"] > 10) & (df["dependency_ratio"] < 0.5)]
    record(6, "High-unemployment + low-dependency paradox",
           PASS if paradox.empty else WARN,
           f"{len(paradox)} rows flagged"
           + (f"\n{paradox[['municipality_code','year','unemployment','dependency_ratio']].head(10).to_string(index=False)}"
              if not paradox.empty else ""))

# ---------------------------------------------------------------------------
section("CHECK 7, Temporal Consistency (no > 3 SD single-year jumps)")
# ---------------------------------------------------------------------------

jump_issues: dict[str, list] = {v: [] for v in TEMPORAL_VARS}

for col in TEMPORAL_VARS:
    if col not in df.columns:
        record(7, f"Temporal jump check: {col}", FAIL, "Column missing")
        continue

    tmp = df[["municipality_code", "year", col]].sort_values(
        ["municipality_code", "year"]
    ).copy()
    tmp["_diff"] = tmp.groupby("municipality_code")[col].diff()

    # Compute global SD of all year-over-year changes
    global_sd = tmp["_diff"].std()
    threshold  = 3.0 * global_sd

    big_jumps = tmp[tmp["_diff"].abs() > threshold].copy()
    big_jumps["_sd_multiple"] = (big_jumps["_diff"].abs() / global_sd).round(2)

    if big_jumps.empty:
        record(7, f"Temporal jump check: {col}", PASS,
               f"Global SD of YoY change = {global_sd:.4g}  |  Threshold = {threshold:.4g}")
    else:
        sample = big_jumps[["municipality_code", "year", col, "_diff", "_sd_multiple"]].head(20)
        record(7, f"Temporal jump check: {col}", WARN,
               f"{len(big_jumps)} single-year jumps > 3 SD ({threshold:.4g})  "
               f"|  Global SD = {global_sd:.4g}\n"
               f"Largest jumps (up to 20):\n{sample.to_string(index=False)}")
    tmp.drop(columns=["_diff"], inplace=True)

# ---------------------------------------------------------------------------
section("CHECK 8, Known Benchmarks (spot checks vs SCB/AF published data)")
# ---------------------------------------------------------------------------

benchmarks = [
    # (label, muni_code, year, column, lo, hi)
    ("Stockholm (0180) debt_per_capita 2023",
     "0180", 2023, "debt_per_capita", 62_000, 63_500),  # SCB Kr/invånare, post 089: 62,670
    ("Stockholm (0180) unemployment 2023",
     "0180", 2023, "unemployment", 2.0, 4.0),
    ("Danderyd (0162) tax_base_relative 2023",
     "0162", 2023, "tax_base_relative", 150, 999),
]

for label, code, year, col, lo, hi in benchmarks:
    if col not in df.columns:
        record(8, label, FAIL, f"Column '{col}' missing")
        continue
    row = df[(df["municipality_code"] == code) & (df["year"] == year)]
    if row.empty:
        record(8, label, FAIL, f"No row for municipality {code}, year {year}")
        continue
    val = float(row[col].iloc[0])
    ok  = lo <= val <= hi
    record(8, label,
           PASS if ok else WARN,
           f"Value = {val:,.4g}  |  Expected range [{lo:,}: {hi:,}]")

# National mean unemployment 2023
if "unemployment" in df.columns:
    nat_u_2023 = float(df[df["year"] == 2023]["unemployment"].mean())
    ok = 2.5 <= nat_u_2023 <= 3.5
    record(8, "National mean unemployment 2023",
           PASS if ok else WARN,
           f"Computed mean = {nat_u_2023:.3f}%  |  Expected 2.5-3.5%")

# National mean dependency_ratio (all years)
if "dependency_ratio" in df.columns:
    nat_dr = float(df["dependency_ratio"].mean())
    ok = 0.75 <= nat_dr <= 0.90
    record(8, "National mean dependency_ratio (all years)",
           PASS if ok else WARN,
           f"Computed mean = {nat_dr:.4f}  |  Expected 0.75-0.90")

# ---------------------------------------------------------------------------
section("CHECK 9: Duplicate (municipality_code, year) Pairs")
# ---------------------------------------------------------------------------

dup_count = int(df.duplicated(subset=["municipality_code", "year"]).sum())
if dup_count == 0:
    record(9, "No duplicate (muni_code, year) pairs", PASS, "")
else:
    dups = df[df.duplicated(subset=["municipality_code", "year"], keep=False)]
    record(9, "No duplicate (muni_code, year) pairs", FAIL,
           f"{dup_count} duplicate rows\n"
           f"{dups[['municipality_code','year']].head(20).to_string(index=False)}")

# ---------------------------------------------------------------------------
section("CHECK 10, Data Types")
# ---------------------------------------------------------------------------

def _is_integer_dtype(dtype) -> bool:
    """Return True for both numpy int types and pandas nullable Int64Dtype."""
    try:
        return np.issubdtype(dtype, np.integer)
    except TypeError:
        # pandas ExtensionDtype such as Int64Dtype
        return hasattr(dtype, "numpy_dtype") and np.issubdtype(dtype.numpy_dtype, np.integer)

def _is_float_dtype(dtype) -> bool:
    """Return True for both numpy float types and pandas nullable Float64Dtype."""
    try:
        return np.issubdtype(dtype, np.floating)
    except TypeError:
        return hasattr(dtype, "numpy_dtype") and np.issubdtype(dtype.numpy_dtype, np.floating)

if "year" in df.columns:
    year_dtype = df["year"].dtype
    is_int = _is_integer_dtype(year_dtype)
    record(10, "year column is integer dtype",
           PASS if is_int else FAIL,
           f"Actual dtype: {year_dtype}")

for col in NUMERIC_COLS:
    if col not in df.columns:
        record(10, f"Dtype check: {col}", FAIL, "Column missing")
        continue
    dt = df[col].dtype
    is_float = _is_float_dtype(dt)
    record(10, f"Dtype check: {col} is float",
           PASS if is_float else WARN,
           f"Actual dtype: {dt}")

# ---------------------------------------------------------------------------
section("CHECK 11, Cache File Existence")
# ---------------------------------------------------------------------------

for name, path in CACHE_FILES.items():
    exists = os.path.isfile(path)
    if exists:
        size_mb = os.path.getsize(path) / 1_048_576
        try:
            tmp = pd.read_parquet(path)
            record(11, f"Cache: {name}.parquet", PASS,
                   f"Size: {size_mb:.2f} MB  |  Shape: {tmp.shape}  |  "
                   f"Columns: {list(tmp.columns)[:8]}{'...' if len(tmp.columns) > 8 else ''}")
        except Exception as exc:
            record(11, f"Cache: {name}.parquet", FAIL,
                   f"Exists but cannot be read: {exc}")
    else:
        record(11, f"Cache: {name}.parquet", FAIL,
               f"NOT FOUND at {path}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
section("AUDIT SUMMARY")

counts = {"PASS": 0, "FAIL": 0, "WARN": 0}
for r in results:
    counts[r["status"]] += 1

print(f"  Total checks : {len(results)}")
print(f"  PASS         : {counts['PASS']}")
print(f"  WARN         : {counts['WARN']}")
print(f"  FAIL         : {counts['FAIL']}")
print()

fail_items = [r for r in results if r["status"] == FAIL]
warn_items = [r for r in results if r["status"] == WARN]

if fail_items:
    print("  --- FAILURES ---")
    for r in fail_items:
        print(f"  Check {r['id']:>2}: {r['name']}")
        for line in r["detail"].strip().splitlines()[:3]:
            print(f"            {line}")
    print()

if warn_items:
    print("  --- WARNINGS ---")
    for r in warn_items:
        print(f"  Check {r['id']:>2}: {r['name']}")
        for line in r["detail"].strip().splitlines()[:2]:
            print(f"            {line}")
    print()

if counts["FAIL"] == 0 and counts["WARN"] == 0:
    print("  *** FULL AUDIT PASSED, data is clean and ready ***")
elif counts["FAIL"] == 0:
    print("  *** NO FAILURES: pipeline data is usable; review warnings above ***")
else:
    print("  *** AUDIT FAILED, see FAILURE items above for required fixes ***")

print()
