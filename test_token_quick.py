import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def test_token():
    api_token = os.getenv('DERIV_API_TOKEN')
    print(f"Token: {api_token}")
    
    if not api_token:
        print("No token found")
        return
    
    url = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    
    try:
        ws = await websockets.connect(url)
        print("Connected")
        
        # Test auth
        await ws.send(json.dumps({"authorize": api_token}))
        response = await ws.recv()
        data = json.loads(response)
        print(f"Auth: {data}")
        
        if "authorize" in data:
            print("✅ Auth successful")
            # Test balance
            await ws.send(json.dumps({"balance": 1}))
            balance_response = await ws.recv()
            balance_data = json.loads(balance_response)
            print(f"Balance: {balance_data}")
        else:
            print("❌ Auth failed")
        
        await ws.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_token())