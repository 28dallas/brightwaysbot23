import asyncio
import sys
import os
sys.path.append('backend')

from services.deriv_trader import DerivTrader
from dotenv import load_dotenv

load_dotenv()

async def test_real_deriv():
    api_token = os.getenv('DERIV_API_TOKEN')
    print(f"Testing with token: ***{api_token[-4:] if api_token else 'None'}")
    
    trader = DerivTrader()
    try:
        # Test demo connection
        print("Connecting to demo...")
        connected = await trader.connect(api_token, is_demo=True)
        print(f"Demo connected: {connected}, Authorized: {trader.authorized}")
        
        if connected and trader.authorized:
            balance = await trader.get_balance()
            print(f"Demo balance: {balance}")
            
            # Test a small trade
            trade_result = await trader.buy_contract({
                "contract_type": "DIGITEVEN",
                "symbol": "R_100", 
                "amount": 1.0,
                "duration": 5,
                "duration_unit": "t",
                "currency": "USD"
            })
            print(f"Trade result: {trade_result}")
        
        await trader.close()
        
    except Exception as e:
        print(f"Error: {e}")
        await trader.close()

if __name__ == "__main__":
    asyncio.run(test_real_deriv())