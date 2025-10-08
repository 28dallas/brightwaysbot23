import asyncio
import json
import websockets
from typing import Optional, Dict, Any
from utils.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DerivTrader:
    def __init__(self):
        self.ws = None
        self.is_connected = False
        self.authorized = False
        self.reconnect_count = 0
        
    async def connect(self, api_token: Optional[str] = None, is_demo: bool = True):
        """Connect to Deriv with robust reconnection logic"""
        app_id = Config.DERIV_DEMO_APP_ID if is_demo else Config.DERIV_LIVE_APP_ID
        url = f"{Config.DERIV_WS_URL}?app_id={app_id}"
        
        for attempt in range(Config.WS_MAX_RETRIES):
            try:
                logger.info(f"Connecting to Deriv (attempt {attempt + 1})")
                self.ws = await websockets.connect(url, timeout=Config.WS_TIMEOUT)
                self.is_connected = True
                self.reconnect_count = 0
                
                if api_token:
                    auth_result = await self.authorize(api_token)
                    if not auth_result:
                        raise Exception("Authorization failed")
                
                logger.info("Successfully connected to Deriv")
                return True
                
            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < Config.WS_MAX_RETRIES - 1:
                    await asyncio.sleep(Config.WS_RECONNECT_DELAY * (2 ** attempt))
                
        return False
    
    async def authorize(self, api_token: str) -> Optional[Dict]:
        """Authorize with improved error handling"""
        try:
            auth_request = {"authorize": api_token}
            await self.ws.send(json.dumps(auth_request))
            
            response = await asyncio.wait_for(self.ws.recv(), timeout=10)
            data = json.loads(response)
            
            if "authorize" in data:
                self.authorized = True
                logger.info("Authorization successful")
                return data["authorize"]
            elif "error" in data:
                logger.error(f"Authorization error: {data['error']}")
                return None
                
        except Exception as e:
            logger.error(f"Authorization failed: {e}")
            return None
    
    async def buy_contract(self, contract_request: Dict) -> Dict:
        """Place trade with proper error handling"""
        if not self.is_connected:
            return {"error": "Not connected to Deriv"}
        
        try:
            buy_request = {
                "buy": 1,
                "price": contract_request["amount"],
                "parameters": {
                    "contract_type": contract_request["contract_type"],
                    "symbol": contract_request["symbol"],
                    "duration": contract_request["duration"],
                    "duration_unit": contract_request["duration_unit"]
                }
            }
            
            if contract_request.get("barrier"):
                buy_request["parameters"]["barrier"] = contract_request["barrier"]
            
            await self.ws.send(json.dumps(buy_request))
            response = await asyncio.wait_for(self.ws.recv(), timeout=15)
            result = json.loads(response)
            
            if "buy" in result:
                logger.info(f"Trade placed: {result['buy']['contract_id']}")
            elif "error" in result:
                logger.error(f"Trade error: {result['error']}")
                
            return result
            
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return {"error": str(e)}
    
    async def get_balance(self) -> Optional[float]:
        """Get balance with retry logic"""
        if not self.authorized:
            return None
        
        for attempt in range(3):
            try:
                balance_request = {"balance": 1}
                await self.ws.send(json.dumps(balance_request))
                
                response = await asyncio.wait_for(self.ws.recv(), timeout=10)
                data = json.loads(response)
                
                if "balance" in data:
                    balance = float(data["balance"]["balance"])
                    logger.info(f"Balance retrieved: {balance}")
                    return balance
                elif "error" in data:
                    logger.error(f"Balance error: {data['error']}")
                    
            except Exception as e:
                logger.error(f"Balance fetch attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(1)
                    
        return None
    
    async def close(self):
        """Clean connection closure"""
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            finally:
                self.is_connected = False
                self.authorized = False