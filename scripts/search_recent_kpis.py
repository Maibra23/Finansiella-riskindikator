"""Search for recent unemployment KPIs."""
import requests

base_url = 'https://api.kolada.se/v2/'

# Search all KPIs and find those with recent data
resp = requests.get(f'{base_url}kpi', timeout=60)
all_kpis = resp.json().get('values', [])

print(f"Total KPIs: {len(all_kpis)}")

# Filter for municipality-level KPIs with employment/unemployment keywords
unemployment_kpis = []
for kpi in all_kpis:
    if kpi.get('municipality_type') != 'K':
        continue
    title = kpi.get('title', '').lower()
    if any(word in title for word in ['arbets', 'syssels', 'arbetsl']):
        # Check publication period
        publ = kpi.get('publ_period', '')
        unemployment_kpis.append({
            'id': kpi['id'],
            'title': kpi['title'],
            'publ_period': publ,
            'area': kpi.get('operating_area', '')
        })

print(f"\nFound {len(unemployment_kpis)} employment/unemployment KPIs")
print("\nKPIs sorted by publication period:")

# Sort by publication period (most recent first)
unemployment_kpis.sort(key=lambda x: x.get('publ_period') or '', reverse=True)

for kpi in unemployment_kpis[:20]:
    print(f"  {kpi['id']}: {kpi['title'][:60]} (publ: {kpi['publ_period']})")

# Test the most promising ones
print("\n\nTesting recent KPIs for data availability:")
years = ','.join(str(y) for y in range(2018, 2025))

for kpi in unemployment_kpis[:10]:
    kpi_id = kpi['id']
    resp = requests.get(f'{base_url}data/kpi/{kpi_id}/year/{years}', timeout=30)
    data = resp.json().get('values', [])
    muni_data = [d for d in data if len(d.get('municipality', '')) == 4]
    data_years = sorted(set(d.get('period') for d in muni_data if d.get('period')))

    if data_years:
        sthlm = [d for d in muni_data if d.get('municipality') == '0180']
        sthlm_val = None
        for s in sthlm:
            val = s.get('values', [{}])[0].get('value')
            if val:
                sthlm_val = val
                break
        print(f"\n{kpi_id}: {kpi['title'][:50]}")
        print(f"  Recent years: {data_years}")
        print(f"  Stockholm sample: {sthlm_val}")
