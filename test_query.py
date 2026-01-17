"""
Quick API Test - Tests the /ask endpoint with a UNIVERSAL query
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_universal_query():
    """Test a UNIVERSAL intent query (with 'only')"""
    
    print("=" * 70)
    print("TESTING UNIVERSAL QUERY: 'Customers who ordered only Rock music'")
    print("=" * 70)
    
    # This assumes you have a session_id from uploading a database
    # Replace with your actual session_id
    
    payload = {
        "session_id": "YOUR_SESSION_ID_HERE",  # Update this!
        "question": "Customers who ordered only discontinued products"
    }
    
    try:
        print("\n📤 Sending request to /ask endpoint...")
        response = requests.post(f"{API_URL}/ask", json=payload, timeout=30)
        
        print(f"📥 Response Status: {response.status_code}\n")
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ SUCCESS!")
            print("\n" + "=" * 70)
            print("RESPONSE BREAKDOWN")
            print("=" * 70)
            
            # Check for intent type in reasoning steps
            reasoning_steps = data.get("reasoning_steps", [])
            print(f"\n📋 Reasoning Steps ({len(reasoning_steps)} steps):")
            for step in reasoning_steps[:10]:  # Show first 10
                icon = step.get("icon", "")
                text = step.get("text", "")
                status = step.get("status", "")
                print(f"  {icon} {text} [{status}]")
            
            # Check for SQL
            sql = data.get("sql", "")
            print(f"\n💾 Generated SQL:")
            print(f"  Length: {len(sql)} characters")
            print(f"  Contains NOT EXISTS: {'NOT EXISTS' in sql.upper()}")
            print(f"  First 200 chars: {sql[:200]}...")
            
            # Check for reasoning
            reasoning = data.get("reasoning", "")
            print(f"\n🧠 Reasoning:")
            print(f"  Length: {len(reasoning)} characters")
            print(f"  First 200 chars: {reasoning[:200]}...")
            
            # Check for answer
            answer = data.get("answer", "")
            print(f"\n💬 Answer:")
            print(f"  {answer[:300]}...")
            
            # Verify UNIVERSAL pattern
            print(f"\n🔍 UNIVERSAL Intent Verification:")
            has_not_exists = "NOT EXISTS" in sql.upper()
            has_join_or_where = ("JOIN" in sql.upper() or "WHERE" in sql.upper())
            
            print(f"  ✅ Has NOT EXISTS clause: {has_not_exists}")
            print(f"  ✅ Has JOIN or WHERE: {has_join_or_where}")
            
            if has_not_exists and has_join_or_where:
                print(f"\n✅ UNIVERSAL pattern correctly implemented!")
            else:
                print(f"\n⚠️  Warning: UNIVERSAL pattern may be incomplete")
            
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to API")
        print("Make sure uvicorn is running: uvicorn api:app --reload --port 8000")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


def check_api_health():
    """Check if API is running"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is running and healthy")
            return True
        else:
            print(f"⚠️  API returned status {response.status_code}")
            return False
    except:
        print("❌ API is not reachable")
        return False


if __name__ == "__main__":
    print("\n🔍 Checking API status...")
    if check_api_health():
        print("\n" + "=" * 70)
        print("NOTE: Update the session_id in the script before testing!")
        print("To get a session_id:")
        print("  1. Upload a database via UI or POST /upload-db")
        print("  2. Copy the session_id from the response")
        print("  3. Replace 'YOUR_SESSION_ID_HERE' in test_query.py")
        print("=" * 70)
        
        # Uncomment when you have a session_id:
        # test_universal_query()
    else:
        print("\n❌ Cannot test - API is not running")
        print("Start it with: uvicorn api:app --reload --port 8000")
