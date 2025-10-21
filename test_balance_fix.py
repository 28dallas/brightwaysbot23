import requests
import json

# Test the balance endpoint
try:
    response = requests.get('http://localhost:8001/api/balance')
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")