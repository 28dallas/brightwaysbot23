#!/usr/bin/env python3
"""
Test script to verify balance endpoint functionality
"""

import requests
import json

def test_balance_endpoint():
    base_url = "http://localhost:8000"
    
    # Test data
    test_user = {
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User"
    }
    
    try:
        # 1. Register a test user
        print("1. Registering test user...")
        register_response = requests.post(f"{base_url}/api/register", json=test_user)
        
        if register_response.status_code == 200:
            register_data = register_response.json()
            token = register_data.get("token")
            print(f"✓ Registration successful. Token: {token[:20]}...")
        else:
            # Try to login instead (user might already exist)
            print("Registration failed, trying login...")
            login_response = requests.post(f"{base_url}/api/login", json={
                "email": test_user["email"],
                "password": test_user["password"]
            })
            
            if login_response.status_code == 200:
                login_data = login_response.json()
                token = login_data.get("token")
                print(f"✓ Login successful. Token: {token[:20]}...")
            else:
                print(f"✗ Login failed: {login_response.text}")
                return
        
        # 2. Test balance endpoint
        print("\n2. Testing balance endpoint...")
        headers = {"Authorization": f"Bearer {token}"}
        balance_response = requests.get(f"{base_url}/api/balance", headers=headers)
        
        if balance_response.status_code == 200:
            balance_data = balance_response.json()
            print(f"✓ Balance endpoint working!")
            print(f"  Balance: ${balance_data.get('balance', 0)}")
            print(f"  Account Type: {balance_data.get('account_type', 'unknown')}")
        else:
            print(f"✗ Balance endpoint failed: {balance_response.text}")
        
        # 3. Test history endpoint
        print("\n3. Testing history endpoint...")
        history_response = requests.get(f"{base_url}/api/history", headers=headers)
        
        if history_response.status_code == 200:
            history_data = history_response.json()
            print(f"✓ History endpoint working!")
            print(f"  Ticks: {len(history_data.get('ticks', []))}")
            print(f"  Trades: {len(history_data.get('trades', []))}")
        else:
            print(f"✗ History endpoint failed: {history_response.text}")
            
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to backend server. Make sure it's running on port 8000")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_balance_endpoint()