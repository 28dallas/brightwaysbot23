import os
from dotenv import load_dotenv, set_key
from utils.logger import setup_logger

logger = setup_logger(__name__)

def get_trading_mode():
    """Get current trading mode with validation"""
    load_dotenv()  # Load environment variables from .env file
    mode = os.getenv('TRADING_MODE', 'demo')
    if mode not in ['demo', 'live']:
        logger.warning(f"Invalid trading mode '{mode}', defaulting to demo")
        return 'demo'
    return mode

def set_trading_mode(mode):
    """Set trading mode with validation and error handling"""
    if mode not in ['demo', 'live']:
        logger.error(f"Invalid trading mode: {mode}")
        raise ValueError("Trading mode must be 'demo' or 'live'")
    
    try:
        env_path = '.env'
        if os.path.exists(env_path):
            set_key(env_path, 'TRADING_MODE', mode)
        os.environ['TRADING_MODE'] = mode
        logger.info(f"Trading mode set to: {mode}")
        return True
    except Exception as e:
        logger.error(f"Failed to set trading mode: {e}")
        return False