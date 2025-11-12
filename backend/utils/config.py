import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the correct path
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / '.env'
load_dotenv(env_path)

# Also try loading from root directory as fallback
root_env_path = backend_dir.parent / '.env'
load_dotenv(root_env_path)

class Config:
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./trading.db')
    DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'sqlite')

    # Deriv API
    DERIV_API_TOKEN = os.getenv('DERIV_API_TOKEN', '')
    DERIV_APP_ID = os.getenv('DERIV_APP_ID', '1089')
    DERIV_WS_URL = os.getenv('DERIV_WS_URL', 'wss://ws.binaryws.com/websockets/v3')
    DERIV_DEMO_APP_ID = '1089'
    DERIV_LIVE_APP_ID = '1089'

    # Trading
    TRADING_MODE = os.getenv('TRADING_MODE', 'demo')
    DEFAULT_STAKE = float(os.getenv('DEFAULT_STAKE', '1.0'))
    MAX_STAKE = float(os.getenv('MAX_STAKE', '5.0'))
    MIN_TRADE_INTERVAL = int(os.getenv('MIN_TRADE_INTERVAL', '30'))
    MAX_CONCURRENT_TRADES = int(os.getenv('MAX_CONCURRENT_TRADES', '3'))

    # AI
    AI_MODEL_PATH = os.getenv('AI_MODEL_PATH', './backend/ai_models')
    AI_TRAINING_ENABLED = os.getenv('AI_TRAINING_ENABLED', 'true').lower() == 'true'
    AI_CONFIDENCE_THRESHOLD = float(os.getenv('AI_CONFIDENCE_THRESHOLD', '0.7'))

    # Security
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'brightbot_secret_key_2024')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '30'))

    # Server
    BACKEND_HOST = os.getenv('BACKEND_HOST', '127.0.0.1')
    BACKEND_PORT = int(os.getenv('BACKEND_PORT', '8001'))
    FRONTEND_HOST = os.getenv('FRONTEND_HOST', '127.0.0.1')
    FRONTEND_PORT = int(os.getenv('FRONTEND_PORT', '3000'))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', './logs/brightbot.log')

    # Risk Management
    MAX_DRAWDOWN_PERCENT = float(os.getenv('MAX_DRAWDOWN_PERCENT', '20'))
    STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '5'))
    TRAILING_STOP_LOSS_PERCENT = float(os.getenv('TRAILING_STOP_LOSS_PERCENT', '2'))
    TAKE_PROFIT_PERCENT = float(os.getenv('TAKE_PROFIT_PERCENT', '10'))

    # Notifications
    EMAIL_NOTIFICATIONS = os.getenv('EMAIL_NOTIFICATIONS', 'false').lower() == 'true'
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

    # Development
    DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
    RELOAD = os.getenv('RELOAD', 'true').lower() == 'true'

    # WebSocket Settings (legacy)
    WS_RECONNECT_DELAY = 5
    WS_MAX_RETRIES = 10
    WS_TIMEOUT = 30

    @classmethod
    def validate_config(cls):
        """Validate critical configuration values"""
        errors = []

        if not cls.JWT_SECRET_KEY:
            errors.append("JWT_SECRET_KEY is required")

        if cls.TRADING_MODE not in ['demo', 'live']:
            errors.append("TRADING_MODE must be 'demo' or 'live'")

        if cls.MAX_STAKE <= 0:
            errors.append("MAX_STAKE must be positive")

        if cls.AI_CONFIDENCE_THRESHOLD < 0 or cls.AI_CONFIDENCE_THRESHOLD > 1:
            errors.append("AI_CONFIDENCE_THRESHOLD must be between 0 and 1")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

        return True

# Legacy constants for compatibility
SECRET_KEY = Config.JWT_SECRET_KEY
ALGORITHM = Config.JWT_ALGORITHM
