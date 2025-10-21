import asyncio
import json
import websockets
from dotenv import load_dotenv
import os

load_dotenv()

async def test_token():
    api_token = os.getenv('DERIV_API_TOKEN')
    if not api_token:
        print("❌ No API token found in environment")
        return
    app_id = "1089"
    url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
    
    print(f"Testing token: {'*' * len(api_token)}")
    print(f"URL: {url}")
    
    ws = None
    try:
        ws = await asyncio.wait_for(
            websockets.connect(url, ping_interval=30, ping_timeout=10),
            timeout=10
        )
        print("✅ Connected to Deriv")
        
        # Test authorization
        auth_request = {"authorize": api_token}
        await ws.send(json.dumps(auth_request))
        print("📤 Sent auth request")
        
        response = await asyncio.wait_for(ws.recv(), timeout=15)
        data = json.loads(response)
        print(f"📥 Auth response: {data}")
        
        if "authorize" in data:
            print("✅ Authorization successful!")
            account_info = data["authorize"]
            print(f"Account ID: {account_info.get('loginid')}")
            print(f"Currency: {account_info.get('currency')}")
            print(f"Account Type: {account_info.get('account_type')}")
            
            # Get balance
            balance_request = {"balance": 1}
            await ws.send(json.dumps(balance_request))
            print("📤 Sent balance request")
            
            balance_response = await asyncio.wait_for(ws.recv(), timeout=15)
            balance_data = json.loads(balance_response)
            print(f"📥 Balance response: {balance_data}")
            
            if "balance" in balance_data:
                balance = balance_data["balance"]["balance"]
                currency = balance_data["balance"]["currency"]
                print(f"💰 Balance: {balance} {currency}")
            else:
                print("❌ Balance request failed")
                
        elif "error" in data:
            print(f"❌ Authorization failed: {data['error']['message']}")
            print(f"Error code: {data['error']['code']}")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        if ws and (not hasattr(ws, 'state') or ws.state == websockets.protocol.State.OPEN):
            await ws.close()

if __name__ == "__main__":
    asyncio.run(test_token())