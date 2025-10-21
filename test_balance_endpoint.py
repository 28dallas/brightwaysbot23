#!/usr/bin/env python3

import asyncio
import os
from dotenv import load_dotenv
from backend.services.deriv_trader import DerivTrader

load_dotenv()

async def test_balance():
    """Test balance fetching without authentication"""
    api_token = os.getenv('DERIV_API_TOKEN')
    print(f"Testing with API token: {api_token[:10]}..." if api_token else "No API token found")
    
    trader = DerivTrader()
    
    try:
        # Test connection
        connected = await trader.connect(api_token, is_demo=False)
        print(f"Connection successful: {connected}")
        
        if connected:
            # Test balance fetch
            balance = await trader.get_balance()
            print(f"Balance: {balance}")
            
            if balance is not None:
                print("✅ Balance endpoint should work!")
                return {"balance": balance, "account_type": "live"}
            else:
                print("❌ Balance fetch failed")
        else:
            print("❌ Connection failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await trader.close()
    
    print("Falling back to demo balance")
    return {"balance": 10000.0, "account_type": "demo"}

if __name__ == "__main__":
    result = asyncio.run(test_balance())
    print(f"Final result: {result}")