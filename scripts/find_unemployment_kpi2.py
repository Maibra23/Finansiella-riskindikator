"""Find unemployment KPIs with good coverage."""
import requests
import urllib.parse

base_url = 'https://api.kolada.se/v2/'

# Try different search terms
search_terms = ['N00', 'N03', 'N009']  # Common unemployment KPI prefixes

all_kpis = []

# Get KPIs by prefix
for prefix in ['N009', 'N007', 'N039']:
    for i in range(10, 100):
        kpi_id = f'{prefix}{i}'
        try:
            resp = requests.get(f'{base_url}kpi/{kpi_id}', timeout=10)
            if resp.status_code == 200:
                kpi_info = resp.json().get('values', [])
                if kpi_info and kpi_info[0].get('municipality_type') == 'K':
                    title = kpi_info[0].get('title', '')
                    if any(word in title.lower() for word in ['arbets', 'syssels', 'employ', 'jobba']):
                        all_kpis.append({'id': kpi_id, 'title': title})
        except:
            pass

print(f"Found {len(all_kpis)} potential unemployment KPIs")

# Test specific known KPIs
test_kpis = [
    'N00914',  # Openly unemployed
    'N00915',  # Openly unemployed women
    'N00916',  # Openly unemployed men
    'N00920',  # Youth unemployment
    'N00941',
    'N03035',
    'N03935',
    'N03936',  # Youth unemployment
]

print("\nTesting specific KPIs:")
for kpi_id in test_kpis:
    try:
        resp = requests.get(f'{base_url}kpi/{kpi_id}', timeout=10)
        if resp.status_code != 200:
            continue
        kpi_info = resp.json().get('values', [])
        if not kpi_info:
            continue

        title = kpi_info[0].get('title', '')[:70]
        muni_type = kpi_info[0].get('municipality_type', '')

        # Get data
        resp = requests.get(f'{base_url}data/kpi/{kpi_id}/year/2010,2015,2020,2023', timeout=30)
        data = resp.json().get('values', [])
        muni_data = [d for d in data if len(d.get('municipality', '')) == 4]
        years = sorted(set(d.get('period') for d in muni_data if d.get('period')))

        sthlm = [d for d in muni_data if d.get('municipality') == '0180']
        sthlm_vals = {}
        for s in sthlm:
            year = s.get('period')
            val = s.get('values', [{}])[0].get('value')
            if val is not None:
                sthlm_vals[year] = round(val, 1)

        print(f"\n{kpi_id} ({muni_type}): {title}")
        print(f"  Years: {years}")
        print(f"  Stockholm: {sthlm_vals}")
    except Exception as e:
        print(f"{kpi_id}: Error - {e}")

# Also check N01961 for dependency ratio
print("\n\nWorking-age KPI (N01961):")
resp = requests.get(f'{base_url}data/kpi/N01961/year/2010,2015,2020,2023', timeout=30)
data = resp.json().get('values', [])
muni_data = [d for d in data if len(d.get('municipality', '')) == 4]
years = sorted(set(d.get('period') for d in muni_data if d.get('period')))
sthlm = [d for d in muni_data if d.get('municipality') == '0180']
print(f"Years: {years}")
for s in sthlm:
    year = s.get('period')
    val = s.get('values', [{}])[0].get('value')
    if val:
        print(f"Stockholm {year}: {val:.1f}%")
