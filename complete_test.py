"""
Complete Test - Upload + UNIVERSAL Query Test
"""

import requests
import json
import time

API_URL = "http://localhost:8000"

print("="*70)
print("COMPLETE SYSTEM TEST")
print("="*70)

# Step 1: Upload
print("\n[1/2] Uploading database...")
with open('sample_ecommerce.db', 'rb') as f:
    files = {'file': ('test.db', f, 'application/x-sqlite3')}
    response = requests.post(f"{API_URL}/upload-db", files=files, timeout=90)
    
    if response.status_code != 200:
        print(f"Upload failed: {response.status_code}")
        print(response.text)
        exit(1)
    
    data = response.json()
    session_id = data.get('session_id')
    tables = data.get('tables', [])
    
    print(f"  ✓ Session: {session_id}")
    print(f"  ✓ Tables: {', '.join(tables)}")

# Step 2: Test UNIVERSAL query
print("\n[2/2] Testing UNIVERSAL query...")
question = "Customers who ordered only discontinued products"
print(f"  Question: '{question}'")

payload = {
    "session_id": session_id,
    "question": question
}

start = time.time()
response = requests.post(f"{API_URL}/ask", json=payload, timeout=90)
elapsed = time.time() - start

if response.status_code != 200:
    print(f"\n❌ Query failed: {response.status_code}")
    print(response.text)
    exit(1)

data = response.json()

# Save response
with open('test_response.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\n  ✓ Response received in {elapsed:.1f}s")

# Analyze
print("\n" + "="*70)
print("RESULTS")
print("="*70)

# Reasoning
steps = data.get('reasoning_steps', [])
print(f"\nReasoning ({len(steps)} steps):")
for i, step in enumerate(steps[:8], 1):
    text = step.get('text', '')
    status = step.get('status', '')
    print(f"  {i}. {text} [{status}]")
if len(steps) > 8:
    print(f"  ... {len(steps)-8} more steps")

# SQL
sql = data.get('sql', '')
print(f"\nSQL ({len(sql)} chars):")
if sql:
    # Print formatted
    lines = sql.strip().split('\n')
    for line in lines[:20]:
        print(f"  {line}")
    if len(lines) > 20:
        print(f"  ... {len(lines)-20} more lines")
    
    # Check patterns
    print(f"\nPatterns:")
    print(f"  WITH clause: {('WITH' in sql.upper())}")
    print(f"  NOT EXISTS: {('NOT EXISTS' in sql.upper())}")
else:
    print("  ❌ NO SQL GENERATED")

# Results
results = data.get('results', [])
print(f"\nResults ({len(results)} rows):")
if results:
    for row in results[:5]:
        print(f"  {row}")
    if len(results) > 5:
        print (f"  ... {len(results)-5} more rows")

# Answer
answer = data.get('answer', '')
if answer:
    print(f"\nAnswer:")
    print(f"  {answer[:200]}")
    if len(answer) > 200:
        print(f"  ... (truncated)")

# Summary
print("\n" + "="*70)
has_sql = len(sql) > 0
has_not_exists = 'NOT EXISTS' in sql.upper() if sql else False
has_results = len(results) >= 0  # Could be 0 if no customers match

if has_sql and has_not_exists:
    print("✅ TEST PASSED - UNIVERSAL pattern correctly implemented!")
elif has_sql:
    print("⚠️  SQL generated but missing NOT EXISTS pattern")
else:
    print("❌ TEST FAILED - No SQL generated")

print(f"\nFull response saved to: test_response.json")
print("="*70)
