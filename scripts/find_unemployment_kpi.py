"""Find unemployment KPIs with good coverage."""
import requests

base_url = 'https://api.kolada.se/v2/'

# Search for unemployment KPIs
resp = requests.get(f'{base_url}kpi?title=arbetslos', timeout=30)
kpis = resp.json().get('values', [])

# Filter for municipality-level KPIs
muni_kpis = [k for k in kpis if k.get('municipality_type') == 'K']

print(f"Found {len(muni_kpis)} municipality-level unemployment KPIs")
print("\nChecking data availability for each KPI...\n")

# Test each KPI
best_kpis = []
for kpi in muni_kpis[:15]:
    kpi_id = kpi['id']
    title = kpi['title'][:70]

    # Get data for test years
    try:
        resp = requests.get(f'{base_url}data/kpi/{kpi_id}/year/2010,2015,2020,2023', timeout=30)
        data = resp.json().get('values', [])

        # Filter for 4-digit municipality codes
        muni_data = [d for d in data if len(d.get('municipality', '')) == 4]

        # Get years with data
        years = sorted(set(d.get('period') for d in muni_data if d.get('period')))

        # Get Stockholm values
        sthlm = [d for d in muni_data if d.get('municipality') == '0180']
        sthlm_vals = {}
        for s in sthlm:
            year = s.get('period')
            val = s.get('values', [{}])[0].get('value')
            if val is not None:
                sthlm_vals[year] = val

        # Calculate coverage score
        coverage = len(years)
        muni_count = len(set(d['municipality'] for d in muni_data))

        # Check if values are realistic (1-20%)
        realistic = all(0.5 < v < 25 for v in sthlm_vals.values()) if sthlm_vals else False

        print(f"{kpi_id}: {title}")
        print(f"  Years: {years}, Munis: {muni_count}")
        print(f"  Stockholm: {sthlm_vals}")
        print(f"  Realistic: {realistic}")
        print()

        if coverage >= 2 and realistic:
            best_kpis.append({
                'id': kpi_id,
                'title': title,
                'years': years,
                'coverage': coverage,
                'sthlm': sthlm_vals
            })

    except Exception as e:
        print(f"{kpi_id}: Error - {e}")

print("\n" + "="*60)
print("BEST UNEMPLOYMENT KPIs:")
print("="*60)
for kpi in sorted(best_kpis, key=lambda x: x['coverage'], reverse=True)[:5]:
    print(f"\n{kpi['id']}: {kpi['title']}")
    print(f"  Years: {kpi['years']}")
    print(f"  Stockholm: {kpi['sthlm']}")
