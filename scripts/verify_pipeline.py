"""Verify pipeline output completeness and sanity checks."""
import os
import sys

import pandas as pd

df = pd.read_parquet('data/processed/kri_base_data.parquet')

print('=== PARQUET FILE VALIDATION ===')
print(f'Shape: {df.shape}')
print(f'Columns: {list(df.columns)}')
print(f'Municipalities: {df["municipality_code"].nunique()} (expected 290)')
print(f'Years: {sorted(df["year"].unique())}')

print()
print('=== COMPLETENESS CHECK ===')
vars_ = ['debt_per_capita', 'unemployment', 'dependency_ratio', 'population_growth', 'tax_base_relative']
errors = []
for v in vars_:
    missing = df[v].isna().sum()
    pct = missing / len(df) * 100
    status = 'OK' if missing == 0 else 'FAIL'
    print(f'  {v}: {missing} missing ({pct:.1f}%) [{status}]')
    if missing > 0:
        errors.append(f'{v} has {missing} missing values')

print()
print('=== SANITY CHECKS ===')

u = df['unemployment'].dropna()
print(f'Unemployment range: {u.min():.2f}% - {u.max():.2f}% (mean: {u.mean():.2f}%)')
if not (0 < u.min() and u.max() < 30):
    errors.append(f'Unemployment out of expected range: {u.min():.2f}-{u.max():.2f}')

d = df['dependency_ratio'].dropna()
print(f'Dependency ratio range: {d.min():.3f} - {d.max():.3f} (mean: {d.mean():.3f})')
if not (0.2 < d.min() and d.max() < 1.5):
    errors.append(f'Dependency ratio out of expected range: {d.min():.3f}-{d.max():.3f}')

debt = df['debt_per_capita'].dropna()
print(f'Debt per capita range: {debt.min():,.0f} - {debt.max():,.0f} SEK (mean: {debt.mean():,.0f})')

pg = df['population_growth'].dropna()
print(f'Population growth range: {pg.min():.2f}% - {pg.max():.2f}%')

tb = df['tax_base_relative'].dropna()
print(f'Tax base range: {tb.min():.0f}% - {tb.max():.0f}% (national avg = 100%)')

print()
print('=== REFERENCE MUNICIPALITY CHECKS ===')

danderyd = df[(df['municipality_code'] == '0162') & (df['year'] == 2023)]
if not danderyd.empty:
    u_val = danderyd['unemployment'].values[0]
    tb_val = danderyd['tax_base_relative'].values[0]
    print(f'Danderyd 2023: unemployment={u_val:.2f}%, tax_base={tb_val:.0f}%')
    if not (u_val < 4 and tb_val > 130):
        errors.append(f'Danderyd sanity failed: u={u_val:.2f}%, tb={tb_val:.0f}%')

dorotea = df[(df['municipality_code'] == '2425') & (df['year'] == 2023)]
if not dorotea.empty:
    u_val = dorotea['unemployment'].values[0]
    pg_val = dorotea['population_growth'].values[0]
    print(f'Dorotea 2023: unemployment={u_val:.2f}%, pop_growth={pg_val:.2f}%')

sthlm = df[(df['municipality_code'] == '0180') & (df['year'] == 2023)]
if not sthlm.empty:
    d_val = sthlm['debt_per_capita'].values[0]
    u_val = sthlm['unemployment'].values[0]
    print(f'Stockholm 2023: debt={d_val:,.0f} SEK, unemployment={u_val:.2f}%')

print()
print('=== WEIGHT SENSITIVITY LAYER ===')

_sens_path = 'data/processed/kri_sensitivity.parquet'
if not os.path.exists(_sens_path):
    print('kri_sensitivity.parquet missing - optional layer, dashboard degrades cleanly')
    print('  build it with: python scripts/run_sensitivity.py')
else:
    _sens = pd.read_parquet(_sens_path)
    _merged = df.merge(_sens, on=['municipality_code', 'year'], how='left', indicator=True)
    _unmatched = int((_merged['_merge'] != 'both').sum())
    print(f'kri_sensitivity.parquet: {len(_sens)} rows, {_unmatched} unmatched on join')
    if _unmatched:
        errors.append(f'Sensitivity layer does not join cleanly: {_unmatched} unmatched rows')
    if len(_sens) != len(df):
        errors.append(f'Sensitivity row count {len(_sens)} != results row count {len(df)}')

print()
if errors:
    print('VERIFICATION FAILED:')
    for e in errors:
        print(f'  - {e}')
    sys.exit(1)
else:
    print('ALL CHECKS PASSED - Pipeline ready for Day 2 tasks')
