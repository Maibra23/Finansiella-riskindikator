"""Check Kolada KPIs for dependency ratio and unemployment."""
import requests

base_url = 'https://api.kolada.se/v2/'

# Search for various terms
searches = ['demografi', 'alder', 'befolkning', 'kvot']
for term in searches:
    resp = requests.get(f'{base_url}kpi?title={term}', timeout=30)
    kpis = resp.json().get('values', [])
    muni_kpis = [k for k in kpis if k.get('municipality_type') == 'K'][:3]
    if muni_kpis:
        print(f"\n=== Search: {term} ===")
        for kpi in muni_kpis:
            print(f"  {kpi['id']}: {kpi['title'][:80]}")

# Check specific KPIs that might be dependency ratio
test_kpis = ['N01963', 'N01964', 'N01961', 'N01962']  # Common demographic KPIs
print("\n=== Testing demographic KPIs ===")
for kpi_id in test_kpis:
    resp = requests.get(f'{base_url}kpi/{kpi_id}', timeout=30)
    if resp.status_code == 200:
        kpi_info = resp.json().get('values', [])
        if kpi_info:
            title = kpi_info[0].get('title', '')
            print(f"{kpi_id}: {title}")
            # Get Stockholm data
            resp2 = requests.get(f'{base_url}data/kpi/{kpi_id}/year/2020', timeout=30)
            data = resp2.json()
            values = data.get('values', [])
            sthlm = [v for v in values if v.get('municipality') == '0180']
            if sthlm:
                val = sthlm[0].get('values', [{}])[0].get('value')
                print(f"  Stockholm 2020: {val}")
