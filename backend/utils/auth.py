import jwt
import hashlib
import logging
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from utils.config import Config

logger = logging.getLogger(__name__)

security = HTTPBearer()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_jwt_token(user_id: int, email: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)

def verify_jwt_token(token: str) -> dict:
    if not token or not token.strip():
        raise HTTPException(status_code=401, detail="Token required")

    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])

        # Validate required fields
        if not payload.get('user_id') or not payload.get('email'):
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(status_code=401, detail="Token verification failed")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authorization header required")
        
    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
        
    payload = verify_jwt_token(token)
    return payload

def create_access_token(data: dict) -> str:
    """Create access token for compatibility"""
    return create_jwt_token(data['user_id'], data['email'])