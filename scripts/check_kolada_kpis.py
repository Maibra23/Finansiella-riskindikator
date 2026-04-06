"""Check Kolada KPI data availability."""
import requests

base_url = 'https://api.kolada.se/v2/'

# Test various unemployment KPIs
kpis_to_test = [
    'N00708',  # Arbetslöshet någon gång under året, inrikes födda
    'N03926',  # Långtidsarbetslösa
    'N00945',  # Total arbetslöshet (we know this has wrong values)
    'N00941',  # Öppet arbetslösa
    'N03935',  # Arbetslösa 18-24 år
]

print("=== TESTING UNEMPLOYMENT KPIs ===")
for kpi_id in kpis_to_test:
    # Get KPI info
    resp = requests.get(f'{base_url}kpi/{kpi_id}', timeout=30)
    if resp.status_code != 200:
        print(f"\n{kpi_id}: NOT FOUND")
        continue

    kpi_info = resp.json().get('values', [{}])[0]
    title = kpi_info.get('title', 'Unknown')[:60]

    # Get data for all years
    resp = requests.get(f'{base_url}data/kpi/{kpi_id}/year/2010,2015,2020,2024', timeout=30)
    data = resp.json().get('values', [])

    # Filter for 4-digit municipality codes only
    muni_data = [d for d in data if len(d.get('municipality', '')) == 4]

    # Get years available
    years = sorted(set(d.get('period') for d in muni_data if d.get('period')))

    # Get Stockholm value
    sthlm = [d for d in muni_data if d.get('municipality') == '0180']
    sthlm_values = []
    for s in sthlm:
        year = s.get('period')
        val = s.get('values', [{}])[0].get('value')
        if val is not None:
            sthlm_values.append(f"{year}: {val:.1f}%")

    print(f"\n{kpi_id}: {title}")
    print(f"  Years with data: {years}")
    print(f"  Municipality records: {len(muni_data)}")
    print(f"  Stockholm: {', '.join(sthlm_values) if sthlm_values else 'No data'}")

# Test working-age KPI
print("\n\n=== TESTING WORKING-AGE KPI ===")
kpi_id = 'N01961'
resp = requests.get(f'{base_url}kpi/{kpi_id}', timeout=30)
kpi_info = resp.json().get('values', [{}])[0]
title = kpi_info.get('title', 'Unknown')

resp = requests.get(f'{base_url}data/kpi/{kpi_id}/year/2010,2015,2020,2024', timeout=30)
data = resp.json().get('values', [])
muni_data = [d for d in data if len(d.get('municipality', '')) == 4]
years = sorted(set(d.get('period') for d in muni_data if d.get('period')))

print(f"{kpi_id}: {title}")
print(f"  Years with data: {years}")
print(f"  Municipality records: {len(muni_data)}")

sthlm = [d for d in muni_data if d.get('municipality') == '0180']
for s in sthlm:
    year = s.get('period')
    val = s.get('values', [{}])[0].get('value')
    if val:
        print(f"  Stockholm {year}: {val:.1f}%")
