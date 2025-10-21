import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def test_deriv_connection():
    api_token = os.getenv('DERIV_API_TOKEN')
    app_id = os.getenv('DERIV_APP_ID', '1089')
    
    print(f"API Token: {api_token}")
    print(f"App ID: {app_id}")
    
    url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
    print(f"Connecting to: {url}")
    
    try:
        ws = await websockets.connect(url, timeout=30)
        print("✅ WebSocket connected")
        
        # Authorize
        auth_request = {"authorize": api_token}
        await ws.send(json.dumps(auth_request))
        print("📤 Authorization request sent")
        
        response = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(response)
        print(f"📥 Auth response: {data}")
        
        if "authorize" in data:
            print("✅ Authorization successful")
            
            # Get balance
            balance_request = {"balance": 1}
            await ws.send(json.dumps(balance_request))
            print("📤 Balance request sent")
            
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(response)
            print(f"📥 Balance response: {data}")
            
            if "balance" in data:
                balance = float(data["balance"]["balance"])
                print(f"💰 Balance: {balance}")
                return balance
        else:
            print("❌ Authorization failed")
            
        await ws.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    result = asyncio.run(test_deriv_connection())
    print(f"Final result: {result}")