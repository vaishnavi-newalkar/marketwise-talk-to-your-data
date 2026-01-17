"""
Simple one-query test to verify system is working
"""

import requests
import json

API_URL = "http://localhost:8000"

print("Testing API Health...")
try:
    response = requests.get(f"{API_URL}/health", timeout=5)
    print(f"API Health: {response.status_code}")
except Exception as e:
    print(f"API Error: {e}")
    exit(1)

print("\nUploading database...")
with open('sample_ecommerce.db', 'rb') as f:
    files = {'file': ('sample_ecommerce.db', f, 'application/x-sqlite3')}
    response = requests.post(f"{API_URL}/upload-db", files=files, timeout=30)
    
    if response.status_code != 200:
        print(f"Upload failed: {response.status_code}")
        print(response.text)
        exit(1)
    
    data = response.json()
    session_id = data.get('session_id')
    schema = data.get('schema', {})
    tables = schema.get('tables', [])
    
    print(f"Success! Session: {session_id}")
    print(f"Tables found: {len(tables)}")
    for table in tables:
        print(f"  - {table['name']}: {table['row_count']} rows, {len(table['columns'])} columns")

print("\nAsking question...")
question = "Customers who ordered only discontinued products"
print(f"Q: {question}")

payload = {
    "session_id": session_id,
    "question": question
}

response = requests.post(f"{API_URL}/ask", json=payload, timeout=60)

if response.status_code != 200:
    print(f"Query failed: {response.status_code}")
    print(response.text)
    exit(1)

data = response.json()

# Save full response to file
with open('last_test_response.json', 'w') as f:
    json.dump(data, f, indent=2)
    print("\nFull response saved to: last_test_response.json")

# Display summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)

sql = data.get("sql", "")
print(f"\nSQL ({len(sql)} chars):")
print(sql)

results = data.get("results", [])
print(f"\nResults ({len(results)} rows):")
for row in results:
    print(f"  {row}")

answer = data.get("answer", "")
print(f"\nAnswer:")
print(f"  {answer}")

print("\n" + "="*70)
print("TEST COMPLETE!")
print(f"Session ID: {session_id}")
print("="*70)
