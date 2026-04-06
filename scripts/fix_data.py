"""Script to investigate and fix data issues."""
import requests
import json
import sys
sys.path.insert(0, '.')

# 1. Check Kolada unemployment data
print("=== INVESTIGATING UNEMPLOYMENT DATA ===")
base_url = 'https://api.kolada.se/v2/'

# Search for unemployment KPIs
resp = requests.get(f"{base_url}kpi?title=arbetslöshet", timeout=30)
kpis = resp.json().get('values', [])
print(f"Found {len(kpis)} KPIs for 'arbetslöshet'")

# Filter for municipality KPIs
muni_kpis = [k for k in kpis if k.get('municipality_type') == 'K']
print(f"Municipality-level KPIs: {len(muni_kpis)}")

for kpi in muni_kpis[:5]:
    print(f"  {kpi['id']}: {kpi['title']}")

# Test N00945
print("\nTesting KPI N00945 (Total unemployment):")
resp = requests.get(f"{base_url}data/kpi/N00945/year/2020", timeout=30)
data = resp.json()
values = data.get('values', [])
print(f"  Records: {len(values)}")
if values:
    # Check sample
    sample = values[0]
    print(f"  Sample: {sample}")
    # Check for Stockholm
    sthlm = [v for v in values if v.get('municipality') == '0180']
    if sthlm:
        print(f"  Stockholm: {sthlm[0]}")

# 2. Check dependency ratio KPI in Kolada
print("\n=== CHECKING DEPENDENCY RATIO IN KOLADA ===")
resp = requests.get(f"{base_url}kpi?title=försörjningskvot", timeout=30)
kpis = resp.json().get('values', [])
print(f"Found {len(kpis)} KPIs for 'försörjningskvot'")

muni_kpis = [k for k in kpis if k.get('municipality_type') == 'K']
for kpi in muni_kpis[:5]:
    print(f"  {kpi['id']}: {kpi['title']}")

# Test dependency ratio KPIs
for kpi in muni_kpis[:3]:
    test_kpi = kpi['id']
    print(f"\nTesting KPI {test_kpi}: {kpi['title']}")
    resp = requests.get(f"{base_url}data/kpi/{test_kpi}/year/2020", timeout=30)
    data = resp.json()
    values = data.get('values', [])
    print(f"  Records: {len(values)}")
    if values:
        sthlm = [v for v in values if v.get('municipality') == '0180']
        if sthlm:
            val = sthlm[0].get('values', [{}])[0].get('value')
            print(f"  Stockholm value: {val}")

# 3. Search for open unemployment KPIs
print("\n=== SEARCHING FOR OPEN UNEMPLOYMENT KPIs ===")
# Search with "öppet"
resp = requests.get(f"{base_url}kpi?title=öppet", timeout=30)
kpis = resp.json().get('values', [])
muni_kpis = [k for k in kpis if k.get('municipality_type') == 'K']
print(f"Found {len(muni_kpis)} municipality KPIs with 'öppet'")
for kpi in muni_kpis[:5]:
    print(f"  {kpi['id']}: {kpi['title']}")

# Test N00941 - Öppet arbetslösa
test_kpis = ['N00941', 'N00708', 'N03926']
for kpi_id in test_kpis:
    resp = requests.get(f"{base_url}kpi/{kpi_id}", timeout=30)
    if resp.status_code == 200:
        kpi_info = resp.json().get('values', [])
        if kpi_info:
            print(f"\n{kpi_id}: {kpi_info[0].get('title')}")
            resp = requests.get(f"{base_url}data/kpi/{kpi_id}/year/2020", timeout=30)
            data = resp.json()
            values = data.get('values', [])
            print(f"  Records: {len(values)}")
            if values:
                sthlm = [v for v in values if v.get('municipality') == '0180']
                if sthlm:
                    val = sthlm[0].get('values', [{}])[0].get('value')
                    print(f"  Stockholm 2020: {val}")
