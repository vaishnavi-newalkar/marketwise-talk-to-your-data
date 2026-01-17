"""
End-to-End System Test
Tests the complete flow: Upload DB -> Ask Questions -> Get Results
"""

import requests
import json
import time
import os
import sys
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

API_URL = "http://localhost:8000"

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_section(title):
    """Print a section header"""
    print(f"\n{'─' * 80}")
    print(f"  {title}")
    print(f"{'─' * 80}")

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
        print("❌ API is not reachable at http://localhost:8000")
        print("   Make sure to run: uvicorn api:app --reload --port 8000")
        return False

def upload_database(db_path):
    """Upload a database and return session_id"""
    print_section("📤 STEP 1: Upload Database")
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return None
    
    print(f"📁 Uploading: {db_path}")
    
    with open(db_path, 'rb') as f:
        files = {'file': (os.path.basename(db_path), f, 'application/x-sqlite3')}
        
        try:
            response = requests.post(f"{API_URL}/upload-db", files=files, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                session_id = data.get('session_id')
                schema = data.get('schema', {})
                
                print(f"✅ Upload successful!")
                print(f"🆔 Session ID: {session_id}")
                print(f"\n📊 Database Schema:")
                
                tables = schema.get('tables', [])
                for table in tables:
                    print(f"\n   📋 Table: {table['name']} ({table['row_count']} rows)")
                    for col in table['columns'][:5]:  # Show first 5 columns
                        print(f"      • {col['name']} ({col['type']})")
                    if len(table['columns']) > 5:
                        print(f"      ... and {len(table['columns']) - 5} more columns")
                
                return session_id
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"❌ Error uploading: {e}")
            return None

def ask_question(session_id, question, test_name=""):
    """Ask a question and display results"""
    print_section(f"💬 {test_name}")
    
    print(f"❓ Question: {question}")
    
    payload = {
        "session_id": session_id,
        "question": question
    }
    
    try:
        print("⏳ Processing...")
        start_time = time.time()
        
        response = requests.post(f"{API_URL}/ask", json=payload, timeout=60)
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Response received in {elapsed:.2f}s\n")
            
            # Display reasoning steps
            reasoning_steps = data.get("reasoning_steps", [])
            if reasoning_steps:
                print("🧠 Reasoning Steps:")
                for i, step in enumerate(reasoning_steps[:8], 1):  # Show first 8
                    icon = step.get("icon", "")
                    text = step.get("text", "")
                    status = step.get("status", "")
                    print(f"   {i}. {icon} {text} [{status}]")
                if len(reasoning_steps) > 8:
                    print(f"   ... and {len(reasoning_steps) - 8} more steps")
            
            # Display SQL
            sql = data.get("sql", "")
            if sql:
                print(f"\n💾 Generated SQL ({len(sql)} chars):")
                # Pretty print SQL
                sql_lines = sql.strip().split('\n')
                for line in sql_lines[:15]:  # Show first 15 lines
                    print(f"   {line}")
                if len(sql_lines) > 15:
                    print(f"   ... ({len(sql_lines) - 15} more lines)")
                
                # Check for key patterns
                sql_upper = sql.upper()
                print(f"\n🔍 SQL Analysis:")
                print(f"   • Uses CTE (WITH): {'WITH' in sql_upper}")
                print(f"   • Uses NOT EXISTS: {'NOT EXISTS' in sql_upper}")
                print(f"   • Uses JOIN: {'JOIN' in sql_upper}")
                print(f"   • Uses GROUP BY: {'GROUP BY' in sql_upper}")
            
            # Display results
            results = data.get("results", [])
            if results:
                print(f"\n📊 Query Results ({len(results)} rows):")
                if len(results) > 0:
                    # Show column headers
                    headers = list(results[0].keys())
                    print(f"\n   {' | '.join(headers)}")
                    print(f"   {'-' * (len(' | '.join(headers)))} ")
                    
                    # Show first 5 rows
                    for row in results[:5]:
                        values = [str(v) for v in row.values()]
                        print(f"   {' | '.join(values)}")
                    
                    if len(results) > 5:
                        print(f"   ... and {len(results) - 5} more rows")
            else:
                print(f"\n📊 Query Results: No rows returned")
            
            # Display natural language answer
            answer = data.get("answer", "")
            if answer:
                print(f"\n💬 Natural Language Answer:")
                print(f"   {answer[:300]}...")
            
            print(f"\n{'─' * 80}")
            return True
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (>60s)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_test_suite(session_id):
    """Run a suite of test queries"""
    print_header("🧪 STEP 2: Run Test Queries")
    
    tests = [
        {
            "name": "TEST 1: UNIVERSAL Query (only discontinued products)",
            "question": "Customers who ordered only discontinued products"
        },
        {
            "name": "TEST 2: AGGREGATION Query (revenue by customer)",
            "question": "Show total revenue for each customer"
        },
        {
            "name": "TEST 3: BASIC Query (all products)",
            "question": "List all products with their prices"
        },
        {
            "name": "TEST 4: EXISTENTIAL Query (customers with orders)",
            "question": "Customers who have placed at least one order"
        },
        {
            "name": "TEST 5: ABSENCE Query (products never ordered)",
            "question": "Products that have never been ordered"
        },
    ]
    
    results = []
    for test in tests:
        success = ask_question(session_id, test["question"], test["name"])
        results.append({
            "test": test["name"],
            "success": success
        })
        time.sleep(1)  # Small delay between tests
    
    # Summary
    print_header("📊 TEST SUMMARY")
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    
    print(f"\n✅ Passed: {passed}/{total}")
    print(f"\n📋 Details:")
    for r in results:
        status = "✅" if r["success"] else "❌"
        print(f"   {status} {r['test']}")
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

def main():
    """Main test flow"""
    print_header("🚀 END-TO-END SYSTEM TEST")
    
    # Check API
    print_section("🔍 Checking API Status")
    if not check_api_health():
        print("\n❌ Cannot proceed - API is not running")
        return
    
    # Database path
    db_path = "sample_ecommerce.db"
    
    if not os.path.exists(db_path):
        print(f"\n⚠️  Sample database not found: {db_path}")
        print("   Creating it now...")
        os.system("python create_sample_db.py")
        print()
    
    # Upload database
    session_id = upload_database(db_path)
    
    if not session_id:
        print("\n❌ Cannot proceed - database upload failed")
        return
    
    # Run tests
    run_test_suite(session_id)
    
    print_header("✅ TEST COMPLETE")
    print("\n💡 You can now use this session_id in the Streamlit UI or test_query.py")
    print(f"   Session ID: {session_id}\n")

if __name__ == "__main__":
    main()
