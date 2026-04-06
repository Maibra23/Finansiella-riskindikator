"""Check all available years for key KPIs."""
import requests

base_url = 'https://api.kolada.se/v2/'

# KPIs to check
kpis = [
    ('N00708', 'Unemployment (Swedish-born 20-64)'),
    ('N03935', 'Youth unemployment (18-24)'),
    ('N03936', 'Youth unemployment rate (18-24)'),
    ('N01961', 'Working-age population %'),
]

# Generate all years from 2010-2024
years = ','.join(str(y) for y in range(2010, 2025))

for kpi_id, name in kpis:
    print(f"\n{kpi_id}: {name}")

    resp = requests.get(f'{base_url}data/kpi/{kpi_id}/year/{years}', timeout=60)
    data = resp.json().get('values', [])

    # Filter for 4-digit municipality codes
    muni_data = [d for d in data if len(d.get('municipality', '')) == 4]

    # Get all years with data
    all_years = sorted(set(d.get('period') for d in muni_data if d.get('period')))
    print(f"  Years with data: {all_years}")
    print(f"  Total records: {len(muni_data)}")

    # Get Stockholm values
    sthlm = [d for d in muni_data if d.get('municipality') == '0180']
    sthlm_by_year = {}
    for s in sthlm:
        year = s.get('period')
        val = s.get('values', [{}])[0].get('value')
        if val is not None:
            sthlm_by_year[year] = round(val, 2)
    print(f"  Stockholm: {sthlm_by_year}")

    # Check unique municipalities
    munis = set(d.get('municipality') for d in muni_data)
    print(f"  Unique municipalities: {len(munis)}")
