import asyncio
import os
from dotenv import load_dotenv
from backend.services.deriv_trader import DerivTrader

load_dotenv()

async def test_connection():
    api_token = os.getenv('DERIV_API_TOKEN')
    print(f"API Token: {api_token}")
    
    trader = DerivTrader()
    try:
        connected = await trader.connect(api_token, is_demo=True)
        print(f"Connected: {connected}")
        print(f"Authorized: {trader.authorized}")
        
        if connected and trader.authorized:
            balance = await trader.get_balance()
            print(f"Balance: {balance}")
        
        await trader.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())