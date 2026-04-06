import requests

url = 'https://api.scb.se/OV0104/v1/doris/sv/ssd/OE/OE0107/OE0107G/ResultKn'
r = requests.get(url)
d = r.json()

for var in d.get('variables', []):
    code = var.get('code')
    if code == 'Resultatraknposter':
        print("Income statement posts:")
        for v, t in zip(var.get('values', []), var.get('valueTexts', [])):
            if 'resultat' in t.lower():
                print(f"  {v}: {t}")

# Test query
print("\n--- Test query ---")
query = {
    "query": [
        {"code": "Region", "selection": {"filter": "item", "values": ["0180"]}},
        {"code": "Resultatraknposter", "selection": {"filter": "item", "values": ["120"]}},
        {"code": "ContentsCode", "selection": {"filter": "item", "values": ["OE0107E3"]}},
        {"code": "Tid", "selection": {"filter": "item", "values": ["2020"]}}
    ],
    "response": {"format": "json"}
}
resp = requests.post(url, json=query, timeout=30)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print(f"Data: {resp.json().get('data', [])}")
else:
    print(f"Error: {resp.text[:200]}")
