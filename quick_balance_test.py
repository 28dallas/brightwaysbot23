import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def test_deriv_direct():
    api_token = "bNaLRPnZ1ygA3S9"
    print(f"Testing token: {api_token}")
    
    try:
        # Connect directly to Deriv
        ws = await websockets.connect('wss://ws.binaryws.com/websockets/v3?app_id=1089', ping_interval=30)
        
        # Authorize
        auth_msg = {"authorize": api_token}
        await ws.send(json.dumps(auth_msg))
        response = await ws.recv()
        auth_data = json.loads(response)
        print(f"Auth response: {auth_data}")
        
        if "authorize" in auth_data:
            # Get balance
            balance_msg = {"balance": 1}
            await ws.send(json.dumps(balance_msg))
            balance_response = await ws.recv()
            balance_data = json.loads(balance_response)
            print(f"Balance response: {balance_data}")
        
        await ws.close()
        
    except Exception as e:
        print(f"Direct test error: {e}")

if __name__ == "__main__":
    asyncio.run(test_deriv_direct())