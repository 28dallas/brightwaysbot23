import asyncio
import json
import websockets
import os
from dotenv import load_dotenv

load_dotenv()

async def test_digitmatch_trade():
    api_token = os.getenv('DERIV_API_TOKEN')
    app_id = os.getenv('DERIV_APP_ID', '1089')

    print("Testing DIGITMATCH trade placement...")
    print(f"API Token: {api_token}")
    print(f"App ID: {app_id}")

    url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"

    try:
        ws = await websockets.connect(url, ping_interval=30, ping_timeout=10)
        print("✅ Connected to Deriv")

        # Test authorization
        auth_request = {"authorize": api_token}
        await ws.send(json.dumps(auth_request))

        response = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(response)

        if "authorize" in data:
            print("✅ API Token is VALID")

            # Test DIGITMATCH trade placement
            buy_request = {
                "buy": 1,
                "stake": 1.0,  # Using stake instead of price for DIGITMATCH
                "parameters": {
                    "contract_type": "DIGITMATCH",
                    "symbol": "R_100",
                    "duration": 1,
                    "duration_unit": "t",
                    "currency": "USD",
                    "barrier": "0"
                }
            }

            print(f"Sending DIGITMATCH trade request: {json.dumps(buy_request, indent=2)}")
            await ws.send(json.dumps(buy_request))

            response = await asyncio.wait_for(ws.recv(), timeout=15)
            data = json.loads(response)

            print(f"Trade response: {json.dumps(data, indent=2)}")

            if "buy" in data:
                contract_id = data['buy']['contract_id']
                print(f"✅ Trade successful - Contract ID: {contract_id}")
                return True
            elif "error" in data:
                print(f"❌ Trade error: {data['error']['message']}")
                return False
            else:
                print(f"❌ Unexpected response: {data}")
                return False

        else:
            print("❌ API Token is INVALID")
            print(f"Error: {data}")
            return False

        await ws.close()

    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_digitmatch_trade())
    if result:
        print("\n🎉 DIGITMATCH trade placement works!")
    else:
        print("\n❌ DIGITMATCH trade placement failed")
