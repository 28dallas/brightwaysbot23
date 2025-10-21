import os
from dotenv import set_key, find_dotenv
from utils.logger import setup_logger

logger = setup_logger(__name__)

def update_env_file(updates: dict):
    """
    Safely update key-value pairs in the .env file.
    """
    try:
        env_path = find_dotenv()
        if not env_path:
            env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        for key, value in updates.items():
            set_key(env_path, key, value)
    except Exception as e:
        logger.error(f"Failed to update .env file: {e}")