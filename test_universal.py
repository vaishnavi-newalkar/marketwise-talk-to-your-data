"""
Test the UNIVERSAL query optimization
"""

import requests
import json

API_URL = "http://localhost:8000"

# Read session_id
with open('session_id.txt', 'r') as f:
    session_id = f.read().strip()

print(f"Using session: {session_id}\n")

# Test UNIVERSAL query
question = "Customers who ordered only discontinued products"
print(f"Question: {question}")
print("Expected: UNIVERSAL intent with NOT EXISTS pattern\n")

payload = {
    "session_id": session_id,
    "question": question
}

response = requests.post(f"{API_URL}/ask", json=payload, timeout=90)

if response.status_code == 200:
    data = response.json()
    
    # Save full response
    with open('universal_test_response.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print("="*70)
    print("RESPONSE ANALYSIS")
    print("="*70)
    
    # Analyze reasoning steps
    steps = data.get('reasoning_steps', [])
    print(f"\n1. Reasoning Steps ({len(steps)} steps):")
    for step in steps[:10]:
        print(f"   - {step.get('text', '')} [{step.get('status', '')}]")
    
    # Analyze SQL
    sql = data.get('sql', '')
    print(f"\n2. Generated SQL ({len(sql)} chars):")
    if sql:
        print(sql)
        
        print(f"\n3. SQL Pattern Analysis:")
        print(f"   - Contains WITH (CTE): {('WITH' in sql.upper())}")
        print(f"   - Contains NOT EXISTS: {('NOT EXISTS' in sql.upper())}")
        print(f"   - Contains JOIN: {('JOIN' in sql.upper())}")
    else:
        print("   ❌ NO SQL GENERATED!")
    
    # Analyze results
    results = data.get('results', [])
    print(f"\n4. Query Results ({len(results)} rows):")
    if results:
        for row in results:
            print(f"   - {row}")
    else:
        print("   (No results  returned)")
    
    # Check for errors
    error = data.get('error')
    if error:
        print(f"\n❌ ERROR: {error}")
    
    # Natural language answer
    answer = data.get('answer', '')
    print(f"\n5. Natural Language Answer:")
    print(f"   {answer[:300]}")
    
    print("\n" + "="*70)
    print("Full response saved to: universal_test_response.json")
    print("="*70)
    
else:
    print(f"❌ Request failed: {response.status_code}")
    print(response.text)
