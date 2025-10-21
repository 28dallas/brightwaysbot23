import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    token = os.getenv('DERIV_API_TOKEN')
    if not token:
        print("❌ No token in .env")
        return False
    
    print(f"✅ Token found: {token[:5]}...")
    
    try:
        ws = await websockets.connect("wss://ws.binaryws.com/websockets/v3?app_id=1089")
        
        # Auth
        await ws.send(json.dumps({"authorize": token}))
        auth_resp = await asyncio.wait_for(ws.recv(), timeout=10)
        auth_data = json.loads(auth_resp)
        
        if "authorize" in auth_data:
            print("✅ Auth successful")
            
            # Balance
            await ws.send(json.dumps({"balance": 1}))
            bal_resp = await asyncio.wait_for(ws.recv(), timeout=10)
            bal_data = json.loads(bal_resp)
            
            if "balance" in bal_data:
                balance = bal_data["balance"]["balance"]
                currency = bal_data["balance"]["currency"]
                print(f"✅ Balance: {balance} {currency}")
                await ws.close()
                return True
            else:
                print(f"❌ Balance error: {bal_data}")
        else:
            print(f"❌ Auth error: {auth_data}")
        
        await ws.close()
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test())
    print(f"\n{'✅ Token works!' if success else '❌ Token failed!'}")