import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def test_deriv():
    token = os.getenv('DERIV_API_TOKEN')
    print(f"Token: {token}")
    
    if not token:
        print("No token found")
        return
    
    try:
        # Test live account
        print("Testing live account...")
        ws = await websockets.connect("wss://ws.binaryws.com/websockets/v3?app_id=1089")
        
        await ws.send(json.dumps({"authorize": token}))
        response = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(response)
        print(f"Live auth response: {data}")
        
        if "authorize" in data:
            print("✅ Live auth successful")
            await ws.send(json.dumps({"balance": 1}))
            balance_response = await asyncio.wait_for(ws.recv(), timeout=10)
            balance_data = json.loads(balance_response)
            print(f"Live balance response: {balance_data}")
            
            if "balance" in balance_data:
                balance = balance_data["balance"]["balance"]
                print(f"✅ Live balance: {balance}")
        
        await ws.close()
        
        # Test demo account
        print("\nTesting demo account...")
        ws = await websockets.connect("wss://ws.binaryws.com/websockets/v3?app_id=1089")
        
        await ws.send(json.dumps({"authorize": token}))
        response = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(response)
        print(f"Demo auth response: {data}")
        
        await ws.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_deriv())