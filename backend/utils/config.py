import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key')
    JWT_ALGORITHM = 'HS256'
    
    # Deriv API Configuration
    DERIV_API_TOKEN = os.getenv('DERIV_API_TOKEN')
    DERIV_DEMO_APP_ID = '1089'
    DERIV_LIVE_APP_ID = os.getenv('DERIV_APP_ID', '1089')
    DERIV_WS_URL = 'wss://ws.binaryws.com/websockets/v3'
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./trading.db')
    
    # WebSocket Settings
    WS_RECONNECT_DELAY = 5
    WS_MAX_RETRIES = 10
    WS_TIMEOUT = 30

# Legacy constants for compatibility
SECRET_KEY = Config.JWT_SECRET
ALGORITHM = Config.JWT_ALGORITHM