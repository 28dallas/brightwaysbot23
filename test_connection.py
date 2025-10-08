import asyncio
import json
import websockets
from datetime import datetime

async def test_deriv_connection():
    """Test connection to Deriv and place a small test trade"""
    
    # Your API token from .env
    api_token = "hrvh9vPCEnv7XJV"
    app_id = "1089"
    
    url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
    
    try:
        print("Connecting to Deriv...")
        async with websockets.connect(url) as ws:
            
            # 1. Authorize
            print("Authorizing...")
            auth_request = {"authorize": api_token}
            await ws.send(json.dumps(auth_request))
            
            auth_response = await ws.recv()
            auth_data = json.loads(auth_response)
            
            if "authorize" in auth_data:
                print("Authorization successful!")
                print(f"Account ID: {auth_data['authorize']['loginid']}")
                print(f"Currency: {auth_data['authorize']['currency']}")
            else:
                print("Authorization failed:", auth_data.get('error', 'Unknown error'))
                return
            
            # 2. Get Balance
            print("\nGetting balance...")
            balance_request = {"balance": 1}
            await ws.send(json.dumps(balance_request))
            
            balance_response = await ws.recv()
            balance_data = json.loads(balance_response)
            
            if "balance" in balance_data:
                balance = balance_data["balance"]["balance"]
                print(f"Current Balance: ${balance} {balance_data['balance']['currency']}")
            else:
                print("Balance fetch failed:", balance_data.get('error', 'Unknown error'))
                return
            
            # 3. Subscribe to ticks for Volatility 100 (1s)
            print("\nSubscribing to ticks...")
            tick_request = {"ticks": "1HZ100V"}
            await ws.send(json.dumps(tick_request))
            
            # Wait for a few ticks
            tick_count = 0
            current_price = None
            
            while tick_count < 3:
                response = await ws.recv()
                data = json.loads(response)
                
                if "tick" in data:
                    tick_count += 1
                    current_price = data["tick"]["quote"]
                    last_digit = int(str(current_price).split('.')[-1][-1])
                    
                    print(f"Tick {tick_count}: Price = {current_price}, Last Digit = {last_digit}")
            
            # 4. Place a small test trade (Even/Odd)
            if current_price:
                print(f"\nPlacing test trade...")
                
                # Get contract price first
                proposal_request = {
                    "proposal": 1,
                    "contract_type": "DIGITEVEN",
                    "symbol": "1HZ100V",
                    "duration": 5,
                    "duration_unit": "t",
                    "currency": "USD",
                    "amount": 1,
                    "basis": "stake"
                }
                
                await ws.send(json.dumps(proposal_request))
                proposal_response = await ws.recv()
                proposal_data = json.loads(proposal_response)
                
                if "proposal" in proposal_data:
                    proposal_id = proposal_data["proposal"]["id"]
                    print(f"Got proposal ID: {proposal_id}")
                    
                    # Now buy the contract
                    trade_request = {
                        "buy": proposal_id,
                        "price": 1
                    }
                else:
                    print("Proposal failed:", proposal_data.get('error', 'Unknown error'))
                    return
                
                await ws.send(json.dumps(trade_request))
                trade_response = await ws.recv()
                trade_data = json.loads(trade_response)
                
                if "buy" in trade_data:
                    contract_id = trade_data["buy"]["contract_id"]
                    print(f"Trade placed successfully!")
                    print(f"Contract ID: {contract_id}")
                    print(f"Stake: $1")
                    print(f"Contract: Even Digits")
                    print(f"Duration: 5 ticks")
                    print(f"\nCheck your Deriv account for the trade!")
                else:
                    print("Trade failed:", trade_data.get('error', 'Unknown error'))
            
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_deriv_connection())