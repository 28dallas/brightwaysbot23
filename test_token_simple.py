import asyncio
import json
import websockets

async def test_token():
    token = "bNaLRPnZ1ygA3S9"
    
    try:
        ws = await websockets.connect("wss://ws.binaryws.com/websockets/v3?app_id=1089")
        
        # Test authorization
        await ws.send(json.dumps({"authorize": token}))
        response = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(response)
        
        if "authorize" in data:
            print(f"✅ Token valid - Account: {data['authorize']['loginid']}")
            
            # Get balance
            await ws.send(json.dumps({"balance": 1}))
            balance_response = await asyncio.wait_for(ws.recv(), timeout=10)
            balance_data = json.loads(balance_response)
            
            if "balance" in balance_data:
                print(f"💰 Balance: {balance_data['balance']['balance']} {balance_data['balance']['currency']}")
            else:
                print("❌ Balance request failed")
                
        else:
            print(f"❌ Token invalid: {data.get('error', {}).get('message', 'Unknown error')}")
            
        await ws.close()
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")

asyncio.run(test_token())