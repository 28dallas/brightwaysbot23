import asyncio
import os
from dotenv import load_dotenv
from backend.services.deriv_trader import DerivTrader

load_dotenv()

async def test_api():
    api_token = os.getenv('DERIV_API_TOKEN')
    if not api_token:
        print("❌ No DERIV_API_TOKEN found in .env file")
        return False
    
    print(f"✅ API Token found: {'*' * len(api_token)}")
    
    trader = DerivTrader()
    try:
        print("🔄 Testing live connection...")
        connected = await asyncio.wait_for(
            trader.connect(api_token=api_token, is_demo=False), 
            timeout=15
        )
        
        if connected and trader.authorized:
            print("✅ Live connection successful")
            balance = await asyncio.wait_for(trader.get_balance(), timeout=10)
            if balance is not None:
                print(f"💰 Live balance: {balance}")
                await trader.close()
                return True
            else:
                print("❌ Failed to get balance")
        else:
            print("❌ Live connection failed")
            
        await trader.close()
        
        print("🔄 Testing demo connection...")
        connected = await asyncio.wait_for(
            trader.connect(api_token=api_token, is_demo=True), 
            timeout=15
        )
        
        if connected and trader.authorized:
            print("✅ Demo connection successful")
            balance = await asyncio.wait_for(trader.get_balance(), timeout=10)
            if balance is not None:
                print(f"💰 Demo balance: {balance}")
                await trader.close()
                return True
            else:
                print("❌ Failed to get demo balance")
        else:
            print("❌ Demo connection failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await trader.close()
    
    return False

if __name__ == "__main__":
    success = asyncio.run(test_api())
    if success:
        print("\n✅ API token is working correctly")
    else:
        print("\n❌ API token test failed")
        print("\nTo fix:")
        print("1. Get API token from https://app.deriv.com")
        print("2. Add to .env file: DERIV_API_TOKEN=your_token_here")