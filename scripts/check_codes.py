"""Check municipality code format in Kolada data."""
import pandas as pd

df = pd.read_parquet('data/cache/kolada_unemployment.parquet')
print('Unemployment data:')
print(f'Total rows: {len(df)}')
print(f'Unique municipality codes: {df["municipality_code"].nunique()}')
print(f'Sample codes: {df["municipality_code"].unique()[:15]}')
print(f'Stockholm (0180): {len(df[df["municipality_code"] == "0180"])} rows')

# Check if codes have leading zeros
sthlm = df[df['municipality_code'].str.contains('180', na=False)]
print(f'Codes containing 180: {sthlm["municipality_code"].unique()}')

# Check years
print(f'\nYears in data: {sorted(df["year"].dropna().unique())}')

# Check for 4-digit codes
df['code_len'] = df['municipality_code'].str.len()
print(f'\nCode lengths: {df["code_len"].value_counts().to_dict()}')
