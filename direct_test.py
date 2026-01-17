"""
Direct Test - Upload database without initial questions by patching
"""

import sqlite3
import requests
import json

API_URL = "http://localhost:8000"

print("Step 1: Check API Health")
response = requests.get(f"{API_URL}/health")
print(f"  Status: {response.status_code}")
if response.status_code != 200:
    print("  ERROR: API not healthy")
    exit(1)

print("\nStep 2: Upload Database (with increased timeout)")
with open('sample_ecommerce.db', 'rb') as f:
    files = {'file': ('test.db', f, 'application/x-sqlite3')}
    
    print("  Sending request... (this may take 30-60 seconds)")
    try:
        response = requests.post(
            f"{API_URL}/upload-db", 
            files=files, 
            timeout=90  # Increased timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            session_id = data.get('session_id')
            tables = data.get('tables', [])
            
            print(f"  SUCCESS!")
            print(f"  Session ID: {session_id}")
            print(f"  Tables: {tables}")
            print(f"  Initial questions: {len(data.get('initial_questions', []))}")
            
            # Save session_id for later use
            with open('session_id.txt', 'w') as sf:
                sf.write(session_id)
            
            print("\nStep 3: Test simple query")
            payload = {
                "session_id": session_id,
                "question": "List all products"
            }
            
            response = requests.post(f"{API_URL}/ask", json=payload, timeout=90)
            
            if response.status_code == 200:
                result = response.json()
                print(f"  SUCCESS!")
                print(f"  SQL generated: {len(result.get('sql', ''))} characters")
                print(f"  Results: {len(result.get('results', []))} rows")
                
                # Print first result
                results = result.get('results', [])
                if results:
                    print(f"\n  First result:")
                    print(f"    {results[0]}")
                
                print("\n✅ ALL TESTS PASSED!")
                print(f"\nSession ID saved to: session_id.txt")
                print(f"Use this to test more queries")
            else:
                print(f"  ERROR: {response.status_code}")
                print(f"  {response.text}")
        else:
            print(f"  ERROR: {response.status_code}") 
            print(f"  {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"  ERROR: Request timed out after 90 seconds")
        print(f"  This suggests the LLM call for initial questions is hanging")
        print(f"  Check your API keys and LLM client configuration")
    except Exception as e:
        print(f"  ERROR: {e}")
