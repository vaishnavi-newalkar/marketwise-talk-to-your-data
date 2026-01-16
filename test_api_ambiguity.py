"""
Test the full API flow for ambiguity detection
"""
import requests
import json

API_URL = "http://127.0.0.1:8000"

# First, upload a test database (assume you have a sample DB)
# We'll skip upload and use a mock session_id for testing the ask endpoint

# Test the /ask endpoint with an ambiguous query
test_query = "Show me recent orders"
mock_session_id = "test-session-123"

# Note: This will fail without a real session, but you can check the logs
payload = {
    "session_id": mock_session_id,
    "question": test_query,
    "is_clarification": False
}

try:
    response = requests.post(f"{API_URL}/ask", json=payload, timeout=10)
    print(f"Status Code: {response.status_code}")
    print("\nResponse:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
