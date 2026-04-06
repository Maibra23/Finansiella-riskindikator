"""Test the data pipeline with fixed KPIs."""
import sys
sys.path.insert(0, '.')

from src.data_fetcher import fetch_all_data
from src.data_cleaner import clean_data

print('Fetching all data (fresh, no cache)...')
raw_data = fetch_all_data(use_cache=False)

print('\nRunning data cleaning pipeline...')
df, report = clean_data(raw_data)

print('\n' + '='*60)
print('RESULTS SUMMARY')
print('='*60)
print(f'Total rows: {len(df)}')
print(f'Municipalities: {df["municipality_code"].nunique()}')
print(f'Years: {sorted(df["year"].unique())}')
print(f'Completeness rate: {report["completeness_rate"]}%')

print('\nMissing values by variable:')
for var, stats in report['missing_by_variable'].items():
    pct = stats['missing_percent']
    status = 'OK' if pct == 0 else ('WARNING' if pct < 10 else 'ERROR')
    print(f'  {var}: {stats["missing_count"]} missing ({pct}%) [{status}]')

print('\nSample Stockholm data (2020):')
sthlm = df[(df['municipality_code'] == '0180') & (df['year'] == 2020)]
if not sthlm.empty:
    for col in ['debt_per_capita', 'unemployment', 'dependency_ratio', 'population_growth', 'tax_base_relative']:
        val = sthlm[col].values[0] if col in sthlm.columns else 'N/A'
        print(f'  {col}: {val}')
