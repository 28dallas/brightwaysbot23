import os
import sys
sys.path.append('backend')

from dotenv import load_dotenv, set_key

def get_trading_mode():
    """Get current trading mode with validation"""
    load_dotenv()  # Load environment variables from .env file
    mode = os.getenv('TRADING_MODE', 'demo')
    if mode not in ['demo', 'live']:
        print(f"Invalid trading mode '{mode}', defaulting to demo")
        return 'demo'
    return mode

def set_trading_mode(mode):
    """Set trading mode with validation and error handling"""
    if mode not in ['demo', 'live']:
        print(f"Invalid trading mode: {mode}")
        raise ValueError("Trading mode must be 'demo' or 'live'")

    try:
        env_path = '.env'
        if os.path.exists(env_path):
            set_key(env_path, 'TRADING_MODE', mode)
        os.environ['TRADING_MODE'] = mode
        print(f"Trading mode set to: {mode}")
        return True
    except Exception as e:
        print(f"Failed to set trading mode: {e}")
        return False

def test_trading_mode_persistence():
    """Test that trading mode persists correctly in .env file"""

    print("🔍 Testing Trading Mode Persistence")
    print("=" * 40)

    # Test initial state
    initial_mode = get_trading_mode()
    print(f"Initial trading mode: {initial_mode}")

    # Test setting to live
    print("\n📝 Setting mode to 'live'...")
    success = set_trading_mode('live')
    if success:
        print("✅ Successfully set to live")

        # Reload and check
        load_dotenv()
        new_mode = os.getenv('TRADING_MODE')
        print(f"Mode from .env file: {new_mode}")

        if new_mode == 'live':
            print("✅ .env file updated correctly")
        else:
            print("❌ .env file not updated")
    else:
        print("❌ Failed to set live mode")

    # Test setting back to demo
    print("\n📝 Setting mode back to 'demo'...")
    success = set_trading_mode('demo')
    if success:
        print("✅ Successfully set to demo")

        # Reload and check
        load_dotenv()
        final_mode = os.getenv('TRADING_MODE')
        print(f"Final mode from .env file: {final_mode}")

        if final_mode == 'demo':
            print("✅ .env file updated correctly")
        else:
            print("❌ .env file not updated")
    else:
        print("❌ Failed to set demo mode")

    print("\n🎯 Test completed!")

if __name__ == "__main__":
    test_trading_mode_persistence()
