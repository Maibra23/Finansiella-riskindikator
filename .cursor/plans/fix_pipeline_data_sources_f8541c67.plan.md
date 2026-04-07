---
name: Fix pipeline data sources
overview: Fix ONLY the two broken variables (unemployment and dependency ratio) that lack complete coverage. The three SCB-based variables (debt_per_capita, population_growth, tax_base_relative) already have 100% coverage and are NOT touched.
todos:
  - id: update-config
    content: "Update src/config.py: change KOLADA_UNEMPLOYMENT_KPIS to [N03937, N03938], remove KOLADA_WORKING_AGE_KPI (no longer needed)"
    status: completed
  - id: update-fetcher-unemployment
    content: "Update data_fetcher.py: Change KoladaFetcher unemployment KPIs to N03937 (full 2010-2024 coverage)"
    status: completed
  - id: update-fetcher-dependency
    content: "Update data_fetcher.py: Add SCBFetcher.fetch_population_by_age_groups() to request ages 0-19, 20-64, 65+ from BefolkningNy for dependency ratio"
    status: completed
  - id: update-fetcher-flow
    content: "Update data_fetcher.py: Remove fetch_working_age_population(), update fetch_all_data() to pass age-group data instead of working_age"
    status: completed
  - id: update-cleaner
    content: "Update data_cleaner.py: Make SCB age-group dependency ratio the primary path, remove Kolada working_age dependency"
    status: completed
  - id: update-pipeline
    content: "Update run_pipeline.py: Remove known-limitations text about Kolada gaps"
    status: completed
  - id: update-methodology
    content: "Update docs/methodology.md: Update sections 7.1 and 7.3 to reflect fixed coverage for unemployment and dependency ratio only"
    status: completed
  - id: run-verify
    content: Run pipeline with --no-cache, verify unemployment and dependency_ratio now show 100% coverage, confirm debt/population/tax_base unchanged
    status: completed
  - id: cleanup-scripts
    content: Delete debug/test scripts created for Kolada KPI search (find_unemployment_kpi*.py, check_kolada*.py, etc.)
    status: completed
isProject: false
---

# Fix Pipeline: Unemployment and Dependency Ratio Coverage

## Scope -- ONLY Fix Broken Variables

Only two variables need changes. The three working variables are left completely untouched:

| Variable          | Current Coverage | Action       |
|-------------------|------------------|--------------|
| debt_per_capita   | 100%             | NO CHANGE    |
| population_growth | 100%             | NO CHANGE    |
| tax_base_relative | 100%             | NO CHANGE    |
| unemployment      | 53% (broken)     | FIX          |
| dependency_ratio  | 40% (broken)     | FIX          |

## Root Cause

- **Unemployment**: Current Kolada KPIs (N03935, N00708) only have 2-4 years of data
- **Dependency ratio**: Current Kolada KPI (N01961 working-age %) only has 2010-2011 data

## Fix 1: Unemployment -- Switch to Kolada N03937

- **KPI**: `N03937` -- "Oppet arbetslosa av befolkningen, 18-65 ar, andel (%)"
- **Source**: Arbetsformedlingen + SCB (via Kolada)
- **Coverage**: 2010-2024, ALL 15 years, all 290 municipalities
- **Definition**: Openly unemployed persons aged 18-65 as share of population 18-65
- Verified: Stockholm (0180) has all 15 years (2.8-4.7%), Dorotea (2425) all years present

Note: The SCB AKU table from the user's link (NAKUArblosaTUtbnivAr) is national-level only (no Region variable), so it cannot be used for municipality-level data. N03937 is the correct alternative.

## Fix 2: Dependency Ratio -- Use SCB Age-Specific Population

The SCB `BefolkningNy` table has single-year ages (0-100+) for all 290 municipalities, 1968-2024. The current fetcher only requests "tot" (total). By requesting specific ages we compute dependency ratio directly:
- Young (0-19) + Old (65+) / Working (20-64)
- 100% coverage for 2010-2024

## Changes Required (Minimal -- Only What's Broken)

### [src/config.py](src/config.py)
- Change `KOLADA_UNEMPLOYMENT_KPIS` from `["N03935", "N00708"]` to `["N03937", "N03938"]`
- Remove `KOLADA_WORKING_AGE_KPI` (no longer needed)

### [src/data_fetcher.py](src/data_fetcher.py)
- Add `fetch_population_by_age_groups()` to SCBFetcher for age-specific population data (dependency ratio)
- Remove `fetch_working_age_population()` from KoladaFetcher
- Update `fetch_all_data()`: remove `working_age` fetch, add `population_by_age` fetch
- Existing methods for balance_sheet, population (total), tax_base, income_statement, tax_rate: NO CHANGES

### [src/data_cleaner.py](src/data_cleaner.py)
- Update `compute_dependency_ratio()` to use SCB age-group data as primary path
- Existing methods for debt, population growth, tax base, unemployment cleaning: NO CHANGES

### [scripts/run_pipeline.py](scripts/run_pipeline.py)
- Update known-limitations text at bottom (remove Kolada gap references)

### [docs/methodology.md](docs/methodology.md)
- Update Section 7.1 and 7.3 to reflect fixed coverage for unemployment and dependency ratio

## Expected Outcome

All 5 variables at 100% coverage. Overall completeness ~100%.

## Verification

1. Run pipeline with `--no-cache --clear-cache`
2. Confirm unemployment and dependency_ratio now show 100%
3. Confirm debt_per_capita, population_growth, tax_base_relative are UNCHANGED
4. Spot-check Stockholm/Dorotea values
5. Clean up old debug scripts
