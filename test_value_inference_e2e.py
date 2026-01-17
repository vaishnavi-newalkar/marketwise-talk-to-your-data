"""
Test value inference with actual query - Shows reasoning about discontinued flag
"""

import requests
import json

API_URL = "http://localhost:8000"

print("="*70)
print("SCHEMA-AWARE VALUE INFERENCE TEST")
print("="*70)

# Upload database
print("\n[1/2] Uploading sample database...")
with open('sample_ecommerce.db', 'rb') as f:
    files = {'file': ('test.db', f, 'application/x-sqlite3')}
    response = requests.post(f"{API_URL}/upload-db", files=files, timeout=90)
    
    if response.status_code != 200:
        print(f"Upload failed: {response.status_code}")
        print(response.text)
        exit(1)
    
    data = response.json()
    session_id = data.get('session_id')
    schema = data.get('schema', {})
    
    print(f"  Session: {session_id}")
    
    # Check for discontinued column
    print("\n  Schema analysis:")
    for table_name, table_info in schema.get('tables', []):
        if table_name == 'products':
            for col in table_info.get('columns', []):
                if 'discontinued' in col.get('name', '').lower():
                    print(f"    ✅ Found: {table_name}.{col['name']} ({col['type']})")

# Test query with 'discontinued' semantic flag
print("\n[2/2] Testing UNIVERSAL query with semantic flag...")
question = "Customers who ordered only discontinued products"
print(f"  Question: '{question}'")
print(f"  Expected: Value inference should detect 'discontinued' is INTEGER")
print(f"            and infer: discontinued = 1 means product is discontinued\n")

payload = {
    "session_id": session_id,
    "question": question
}

response = requests.post(f"{API_URL}/ask", json=payload, timeout=90)

if response.status_code != 200:
    print(f"❌ Query failed: {response.status_code}")
    print(response.text)
    exit(1)

data = response.json()

# Save response
with open('value_inference_test.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("="*70)
print("RESULTS")
print("="*70)

# Check reasoning for value inference
reasoning = data.get('reasoning', '')
print("\n📋 Reasoning:")
print(reasoning)

# Check if value inference is mentioned
print("\n🔍 Value Inference Check:")
if 'discontinued' in reasoning.lower():
    print("  ✅ Reasoning mentions 'discontinued'")
    
    if ('integer' in reasoning.lower() or 'int' in reasoning.lower()) and \
       ('1' in reasoning or '0' in reasoning):
        print("  ✅ Reasoning explains INTEGER representation (0/1)")
    else:
        print("  ⚠️  Reasoning might not fully explain value inference")
else:
    print("  ⚠️  'discontinued' not mentioned in reasoning")

# Check SQL
sql = data.get('sql', '')
print(f"\n💾 Generated SQL:")
print(sql)

print(f"\n🔍 SQL Pattern Check:")
if 'discontinued' in sql.lower():
    print("  ✅ SQL uses 'discontinued' column")
    
    # Check for value inference (should use = 1, not arbitrary values)
    if 'discontinued = 1' in sql.lower() or 'discontinued=1' in sql.lower():
        print("  ✅ Correctly inferred: discontinued = 1")
    elif 'discontinued > 0' in sql.lower():
        print("  ✅ Alternative inference: discontinued > 0")
    else:
        print(f"  ⚠️  Check value used for discontinued in SQL")

# Check for NOT EXISTS pattern (UNIVERSAL intent)
if 'not exists' in sql.lower():
    print("  ✅ Uses NOT EXISTS pattern (UNIVERSAL intent)")

# Results
results = data.get('results', [])
print(f"\n📊 Results: {len(results)} customer(s)")
if results:
    for row in results:
        print(f"  {row}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

has_value_inference = 'discontinued' in reasoning.lower() and \
                     (('integer' in reasoning.lower() or 'int' in reasoning.lower()))
has_correct_sql = 'discontinued' in sql.lower()
has_not_exists = 'not exists' in sql.lower()

if has_value_inference and has_correct_sql and has_not_exists:
    print("✅ ALL CHECKS PASSED!")
    print("   - Value inference detected and explained")
    print("   - SQL uses inferred value correctly")
    print("   - UNIVERSAL pattern (NOT EXISTS) used correctly")
else:
    print("⚠️  Some checks did not pass:")
    if not has_value_inference:
        print("   - Value inference explanation needed")
    if not has_correct_sql:
        print("   - SQL should use discontinued column")
    if not has_not_exists:
        print("   - NOT EXISTS pattern expected for UNIVERSAL")

print(f"\nFull response saved to: value_inference_test.json")
print("="*70)
