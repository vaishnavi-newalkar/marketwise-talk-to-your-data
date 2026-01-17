"""
Quick Test Summary - Shows just the final results
"""

import requests
import json

API_URL = "http://localhost:8000"

def quick_test():
    """Run a quick test and show results"""
    
    # Upload database
    print("=" * 70)
    print(" QUICK SYSTEM TEST")
    print("=" * 70)
    
    print("\n[1/3] Uploading database...")
    with open('sample_ecommerce.db', 'rb') as f:
        files = {'file': ('sample_ecommerce.db', f, 'application/x-sqlite3')}
        response = requests.post(f"{API_URL}/upload-db", files=files, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            session_id = data.get('session_id')
            print(f"SUCCESS! Session ID: {session_id}")
            
            schema = data.get('schema', {})
            tables = schema.get('tables', [])
            print(f"Found {len(tables)} tables: {', '.join([t['name'] for t in tables])}")
        else:
            print(f"FAILED: {response.status_code}")
            return
    
    # Test a UNIVERSAL query
    print("\n[2/3] Testing UNIVERSAL query...")
    print("Question: 'Customers who ordered only discontinued products'")
    
    payload = {
        "session_id": session_id,
        "question": "Customers who ordered only discontinued products"
    }
    
    response = requests.post(f"{API_URL}/ask", json=payload, timeout=60)
    
    if response.status_code == 200:
        data = response.json()
        sql = data.get("sql", "")
        results = data.get("results", [])
        
        print("SUCCESS!")
        print(f"\nSQL Generated ({len(sql)} chars):")
        print("  - Contains 'NOT EXISTS': " + str("NOT EXISTS" in sql.upper()))
        print("  - Contains 'WITH': " + str("WITH" in sql.upper()))
        
        print(f"\nResults: {len(results)} customer(s)")
        if results:
            for row in results:
                print(f"  - {row}")
        
        answer = data.get("answer", "")
        print(f"\nAnswer: {answer[:200]}...")
    else:
        print(f"FAILED: {response.status_code}")
    
    # Test aggregation
    print("\n[3/3] Testing AGGREGATION query...")
    print("Question: 'Show total revenue for each customer'")
    
    payload["question"] = "Show total revenue for each customer"
    response = requests.post(f"{API_URL}/ask", json=payload, timeout=60)
    
    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])
        
        print("SUCCESS!")
        print(f"\nResults: {len(results)} customer(s)")
        if results:
            for row in results[:3]:
                print(f"  - {row}")
            if len(results) > 3:
                print(f"  ... and {len(results) - 3} more")
    else:
        print(f"FAILED: {response.status_code}")
    
    print("\n" + "=" * 70)
    print(" ALL TESTS COMPLETED!")
    print("=" * 70)
    print(f"\nSession ID: {session_id}")
    print("You can use this in the Streamlit UI at http://localhost:8501")

if __name__ == "__main__":
    try:
        quick_test()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
