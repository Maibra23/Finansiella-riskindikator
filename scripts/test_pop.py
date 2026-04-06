import requests

url = 'https://api.scb.se/OV0104/v1/doris/sv/ssd/BE/BE0101/BE0101A/BefolkningNy'

# Test query for all municipalities, total age, all years
print("--- Testing all-municipalities population query ---")
query = {
    "query": [
        {"code": "Region", "selection": {"filter": "all", "values": ["*"]}},
        {"code": "Civilstand", "selection": {"filter": "all", "values": ["*"]}},
        {"code": "Alder", "selection": {"filter": "item", "values": ["tot"]}},  # Total only
        {"code": "Kon", "selection": {"filter": "all", "values": ["*"]}},
        {"code": "ContentsCode", "selection": {"filter": "item", "values": ["BE0101N1"]}},
        {"code": "Tid", "selection": {"filter": "item", "values": ["2020"]}}
    ],
    "response": {"format": "json"}
}
resp = requests.post(url, json=query, timeout=30)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    result = resp.json()
    rows = result.get('data', [])
    print(f"Data rows: {len(rows)}")
    if rows:
        print(f"First 3 rows: {rows[:3]}")
else:
    print(f"Error: {resp.text[:200]}")

# Test with specific ages for dependency ratio
print("\n--- Testing age-specific query ---")
# Need ages 0-19 (young), 20-64 (working), 65+ (old)
# Fetch totals for each single age
query2 = {
    "query": [
        {"code": "Region", "selection": {"filter": "item", "values": ["0180"]}},
        {"code": "Civilstand", "selection": {"filter": "all", "values": ["*"]}},
        {"code": "Alder", "selection": {"filter": "item", "values": ["0", "1", "19", "20", "64", "65", "99", "100+", "tot"]}},
        {"code": "Kon", "selection": {"filter": "all", "values": ["*"]}},
        {"code": "ContentsCode", "selection": {"filter": "item", "values": ["BE0101N1"]}},
        {"code": "Tid", "selection": {"filter": "item", "values": ["2020"]}}
    ],
    "response": {"format": "json"}
}
resp = requests.post(url, json=query2, timeout=30)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    result = resp.json()
    rows = result.get('data', [])
    print(f"Data rows: {len(rows)}")
else:
    print(f"Error: {resp.text[:200]}")
