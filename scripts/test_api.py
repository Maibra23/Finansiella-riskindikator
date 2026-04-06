"""Test SCB API to check correct query format."""
import requests
import json
import sys
sys.path.insert(0, '.')

from src.config import YEARS_STR

base_url = 'https://api.scb.se/OV0104/v1/doris/sv/ssd/'

# Get details of each table we need
tables = {
    'balance_sheet': 'OE/OE0107/OE0107G/BalansKn',
    'tax_rate': 'OE/OE0101/Kommunalskatter2000',
    'tax_base': 'OE/OE0101/SkatteKraft',
    'population': 'BE/BE0101/BE0101A/BefolkningNy',
    'income_statement': 'OE/OE0107/OE0107G/ResultKn',
}

for name, path in tables.items():
    print(f"\n=== {name.upper()} ({path}) ===")
    url = base_url + path
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        for var in data.get('variables', []):
            code = var.get('code')
            text = var.get('text')
            vals = var.get('values', [])[:5]
            valetxts = var.get('valueTexts', [])[:5]
            print(f"  {code}: {text}")
            if vals:
                for v, t in zip(vals, valetxts):
                    print(f"    - {v}: {t}")
    else:
        print(f"  Error: {resp.status_code}")

# Test different query formats
print("\n\n=== TEST POST QUERIES ===")

# Find balance post codes that contain "skuld" (debt)
url = base_url + 'OE/OE0107/OE0107G/BalansKn'
resp = requests.get(url, timeout=10)
data = resp.json()
print("\nBalance posts containing 'skuld':")
for var in data.get('variables', []):
    if var.get('code') == 'Balansraknposter':
        for v, t in zip(var.get('values', []), var.get('valueTexts', [])):
            if 'skuld' in t.lower():
                print(f"  {v}: {t}")

# Check available years
url = base_url + 'OE/OE0107/OE0107G/BalansKn'
resp = requests.get(url, timeout=10)
data = resp.json()
for var in data.get('variables', []):
    if var.get('code') == 'Tid':
        years = var.get('values', [])
        print(f"Available years for balance sheet: {years[-10:]}")  # Last 10

# Use correct codes:
# 089 = LÅNGFRISTIGA SKULDER (Long-term debt)
# OE0107E5 = Tkr (thousands of SEK)

print("\n--- Test 1: Balance sheet query (Stockholm only, 2020) ---")
url = base_url + 'OE/OE0107/OE0107G/BalansKn'
query = {
    "query": [
        {"code": "Region", "selection": {"filter": "item", "values": ["0180"]}},
        {"code": "Balansraknposter", "selection": {"filter": "item", "values": ["089"]}},
        {"code": "ContentsCode", "selection": {"filter": "item", "values": ["OE0107E5"]}},
        {"code": "Tid", "selection": {"filter": "item", "values": ["2020"]}}
    ],
    "response": {"format": "json"}
}
resp = requests.post(url, json=query, timeout=30)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Data: {data.get('data', [])}")

print("\n--- Test 2: Balance sheet query (All municipalities via all filter) ---")
query2 = {
    "query": [
        {"code": "Region", "selection": {"filter": "all", "values": ["*"]}},
        {"code": "Balansraknposter", "selection": {"filter": "item", "values": ["089"]}},
        {"code": "ContentsCode", "selection": {"filter": "item", "values": ["OE0107E5"]}},
        {"code": "Tid", "selection": {"filter": "item", "values": ["2020"]}}
    ],
    "response": {"format": "json"}
}
resp = requests.post(url, json=query2, timeout=30)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    rows = data.get('data', [])
    print(f"Rows returned: {len(rows)}")
else:
    print(f"Error: {resp.text[:200]}")

# Get all region codes from metadata
print("\n--- Getting available region codes ---")
resp = requests.get(url, timeout=10)
regions = []
if resp.status_code == 200:
    for var in resp.json().get('variables', []):
        if var.get('code') == 'Region':
            regions = var.get('values', [])
            print(f"Total regions: {len(regions)}")
            # Filter for municipality codes (4-digit starting with 0-2)
            munis = [r for r in regions if len(r) == 4 and r[0] in '012']
            print(f"Municipality codes: {len(munis)}")
            print(f"First 5: {munis[:5]}")

print("\n--- Test 3: Balance sheet query (explicit municipality codes, 2020) ---")
# Try with explicit municipality codes
munis_to_fetch = munis[:10] if munis else ["0180", "0114", "0115"]
query3 = {
    "query": [
        {"code": "Region", "selection": {"filter": "item", "values": munis_to_fetch}},
        {"code": "Balansraknposter", "selection": {"filter": "item", "values": ["089"]}},
        {"code": "ContentsCode", "selection": {"filter": "item", "values": ["OE0107E5"]}},
        {"code": "Tid", "selection": {"filter": "item", "values": ["2020"]}}
    ],
    "response": {"format": "json"}
}
resp = requests.post(url, json=query3, timeout=30)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    rows = data.get('data', [])
    print(f"Rows returned: {len(rows)}")
    if rows:
        print(f"First 3: {rows[:3]}")
else:
    print(f"Error: {resp.text[:200]}")

# Try tax base query with 2022
print("\n--- Test 2: Tax base query (Stockholm, 2022) ---")
url = base_url + 'OE/OE0101/SkatteKraft'
query = {
    "query": [
        {"code": "Region", "selection": {"filter": "item", "values": ["0180"]}},
        {"code": "ContentsCode", "selection": {"filter": "item", "values": ["OE0101B0"]}},
        {"code": "Tid", "selection": {"filter": "item", "values": ["2022"]}}
    ],
    "response": {"format": "json"}
}
resp = requests.post(url, json=query, timeout=30)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Values: {data.get('value', [])}% of national average")
else:
    print(f"Error: {resp.text[:200]}")

# Try population query
print("\n--- Test 3: Population query (Stockholm, total, 2022) ---")
url = base_url + 'BE/BE0101/BE0101A/BefolkningNy'
query = {
    "query": [
        {"code": "Region", "selection": {"filter": "item", "values": ["0180"]}},
        {"code": "Civilstand", "selection": {"filter": "item", "values": ["OG", "G", "SK", "ÄNKL"]}},
        {"code": "Alder", "selection": {"filter": "item", "values": ["tot"]}},
        {"code": "Kon", "selection": {"filter": "item", "values": ["1", "2"]}},
        {"code": "ContentsCode", "selection": {"filter": "item", "values": ["BE0101N1"]}},
        {"code": "Tid", "selection": {"filter": "item", "values": ["2022"]}}
    ],
    "response": {"format": "json"}
}
resp = requests.post(url, json=query, timeout=30)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Values (first 5): {data.get('value', [])[:5]}")
else:
    print(f"Error: {resp.text[:200]}")
