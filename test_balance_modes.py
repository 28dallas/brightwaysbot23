import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def test_balance_both_modes():
    """Test balance fetching in both demo and live modes"""
    api_token = os.getenv('DERIV_API_TOKEN')
    app_id = os.getenv('DERIV_APP_ID', '1089')
    
    print(f"API Token: {api_token}")
    print(f"App ID: {app_id}")
    print("=" * 50)
    
    # Test Demo Mode
    print("🔸 TESTING DEMO MODE")
    demo_balance = await test_mode(api_token, app_id, is_demo=True)
    
    print("\n" + "=" * 50)
    
    # Test Live Mode  
    print("🔸 TESTING LIVE MODE")
    live_balance = await test_mode(api_token, app_id, is_demo=False)
    
    print("\n" + "=" * 50)
    print("📊 RESULTS SUMMARY:")
    print(f"Demo Balance: {demo_balance}")
    print(f"Live Balance: {live_balance}")
    
    if demo_balance and live_balance:
        print("✅ Both modes working - showing real Deriv balances")
    elif demo_balance or live_balance:
        print("⚠️ Only one mode working")
    else:
        print("❌ Both modes failing - check API token")

async def test_mode(api_token, app_id, is_demo):
    mode_name = "DEMO" if is_demo else "LIVE"
    
    try:
        url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
        print(f"Connecting to {mode_name} mode...")
        
        ws = await websockets.connect(url, timeout=10)
        print(f"✅ {mode_name} WebSocket connected")
        
        # Authorize
        auth_request = {"authorize": api_token}
        await ws.send(json.dumps(auth_request))
        
        response = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(response)
        
        if "authorize" in data:
            print(f"✅ {mode_name} Authorization successful")
            
            # Get balance
            balance_request = {"balance": 1}
            await ws.send(json.dumps(balance_request))
            
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(response)
            
            if "balance" in data:
                balance = float(data["balance"]["balance"])
                currency = data["balance"]["currency"]
                account_type = data["balance"].get("account_type", "unknown")
                
                print(f"💰 {mode_name} Balance: {balance} {currency}")
                print(f"📋 {mode_name} Account Type: {account_type}")
                
                await ws.close()
                return balance
            else:
                print(f"❌ {mode_name} Balance fetch failed: {data}")
        else:
            print(f"❌ {mode_name} Authorization failed: {data}")
            
        await ws.close()
        
    except Exception as e:
        print(f"❌ {mode_name} Error: {e}")
    
    return None

if __name__ == "__main__":
    result = asyncio.run(test_balance_both_modes())