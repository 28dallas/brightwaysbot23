import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def test_api_token():
    api_token = os.getenv('DERIV_API_TOKEN')
    app_id = os.getenv('DERIV_APP_ID', '1089')
    
    print(f"Testing API Token: {api_token}")
    print(f"App ID: {app_id}")
    
    url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
    
    try:
        ws = await websockets.connect(url, timeout=10)
        print("✅ Connected to Deriv")
        
        # Test authorization
        auth_request = {"authorize": api_token}
        await ws.send(json.dumps(auth_request))
        
        response = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(response)
        
        if "authorize" in data:
            print("✅ API Token is VALID")
            print(f"Account info: {data['authorize']}")
            
            # Get balance
            balance_request = {"balance": 1}
            await ws.send(json.dumps(balance_request))
            
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(response)
            
            if "balance" in data:
                balance = data["balance"]["balance"]
                currency = data["balance"]["currency"]
                print(f"💰 Balance: {balance} {currency}")
                return float(balance)
            else:
                print(f"❌ Balance error: {data}")
        else:
            print("❌ API Token is INVALID")
            print(f"Error: {data}")
            
        await ws.close()
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
    
    return None

if __name__ == "__main__":
    result = asyncio.run(test_api_token())
    if result:
        print(f"\n🎉 Your real balance should be: {result}")
    else:
        print("\n❌ Failed to get real balance - check your API token")