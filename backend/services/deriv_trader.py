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
        
    async def connect(self, api_token: Optional[str] = None, app_id: Optional[str] = None, is_demo: bool = True):
        """Connect to Deriv with robust reconnection logic"""
        config_app_id = Config.DERIV_DEMO_APP_ID if is_demo else Config.DERIV_LIVE_APP_ID
        effective_app_id = app_id or config_app_id or "1089"  # Default fallback
        url = f"{Config.DERIV_WS_URL}?app_id={effective_app_id}"

        for attempt in range(3):
            try:
                logger.info(f"Connecting to Deriv - URL: {url}, Demo: {is_demo}, API Token: {bool(api_token)}")
                self.ws = await websockets.connect(
                    url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5
                )
                self.is_connected = True
                self.reconnect_count = 0

                # For demo mode, we don't need authorization
                if api_token and not is_demo:
                    auth_result = await self.authorize(api_token)
                    if not auth_result:
                        logger.error("Authorization failed")
                        await self.close()
                        return False
                elif is_demo:
                    self.authorized = True  # Demo mode doesn't require auth

                logger.info(f"Successfully connected to Deriv - Demo: {is_demo}, Authorized: {self.authorized}")
                return True

            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                await self.close()
                if attempt < 2:
                    await asyncio.sleep(2)

        return False
    
    async def authorize(self, api_token: str) -> Optional[Dict]:
        """Authorize with improved error handling"""
        if not self.ws or (hasattr(self.ws, 'state') and self.ws.state != websockets.protocol.State.OPEN):
            logger.error("WebSocket not connected")
            return None
            
        try:
            auth_request = {"authorize": api_token}
            logger.info(f"Sending authorization request")
            await self.ws.send(json.dumps(auth_request))
            
            response = await asyncio.wait_for(self.ws.recv(), timeout=15)
            data = json.loads(response)
            logger.info(f"Auth response received")
            
            if "authorize" in data:
                self.authorized = True
                logger.info(f"Authorization successful - Account: {data['authorize'].get('loginid', 'Unknown')}")
                return data["authorize"]
            elif "error" in data:
                logger.error(f"Authorization error: {data['error']['message']}")
                return None
                
        except asyncio.TimeoutError:
            logger.error("Authorization timeout")
            return None
        except Exception as e:
            logger.error(f"Authorization failed: {e}")
            return None
    
    async def buy_contract(self, contract_request: Dict) -> Dict:
        """Place trade with proper error handling"""
        if not self.is_connected:
            return {"error": {"message": "Not connected"}}

        try:
            # Build parameters based on contract type
            parameters = {
                "contract_type": contract_request["contract_type"],
                "symbol": contract_request["symbol"],
                "duration": int(contract_request["duration"]),
                "duration_unit": contract_request["duration_unit"],
                "currency": contract_request.get("currency", "USD")
            }

            # Add contract-specific parameters
            if contract_request["contract_type"] == "DIGITMATCH":
                # For digit matching, barrier specifies the digit to match
                parameters["barrier"] = contract_request["barrier"]
            elif contract_request.get("barrier"):
                parameters["barrier"] = contract_request["barrier"]

            buy_request = {
                "buy": contract_request.get("contract_id", 1),
                "price": float(contract_request["amount"]),
                "parameters": parameters
            }

            logger.info(f"Placing trade: {buy_request}")
            await self.ws.send(json.dumps(buy_request))
            response = await asyncio.wait_for(self.ws.recv(), timeout=20)
            result = json.loads(response)
            logger.info(f"Trade response: {result}")

            if "buy" in result:
                contract_id = result['buy']['contract_id']
                logger.info(f"Trade successful - Contract ID: {contract_id}")
            elif "error" in result:
                logger.error(f"Trade error: {result['error']['message']}")

            return result

        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return {"error": {"message": str(e)}}
    
    async def get_balance(self) -> Optional[float]:
        """Get balance with retry logic"""
        if not self.authorized or not self.ws or (hasattr(self.ws, 'state') and self.ws.state != websockets.protocol.State.OPEN):
            logger.error("Not authorized or WebSocket closed")
            return None
        
        for attempt in range(3):
            try:
                balance_request = {"balance": 1}
                logger.info(f"Requesting balance (attempt {attempt + 1})")
                await self.ws.send(json.dumps(balance_request))
                
                response = await asyncio.wait_for(self.ws.recv(), timeout=15)
                data = json.loads(response)
                logger.info(f"Balance response received")
                
                if "balance" in data:
                    balance_value = data["balance"]["balance"]
                    if isinstance(balance_value, (int, float, str)):
                        balance = float(balance_value)
                        currency = data["balance"].get("currency", "USD")
                        logger.info(f"Balance retrieved: {balance} {currency}")
                        return balance
                    else:
                        logger.error(f"Invalid balance format: {balance_value}")
                elif "error" in data:
                    logger.error(f"Balance error: {data['error']['message']}")
                    return None
                    
            except (asyncio.TimeoutError, ValueError) as e:
                logger.error(f"Balance fetch attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Unexpected error in balance fetch: {e}")
                return None
                    
        return None
    
    async def get_contract_info(self, contract_id: str) -> Optional[Dict]:
        """Get contract information by contract ID"""
        if not self.authorized or not self.ws or (hasattr(self.ws, 'state') and self.ws.state != websockets.protocol.State.OPEN):
            logger.error("Not authorized or WebSocket closed")
            return None

        try:
            contract_request = {
                "proposal_open_contract": 1,
                "contract_id": int(contract_id)
            }

            logger.info(f"Requesting contract info for {contract_id}")
            await self.ws.send(json.dumps(contract_request))

            response = await asyncio.wait_for(self.ws.recv(), timeout=15)
            data = json.loads(response)
            logger.info(f"Contract info response received")

            if "proposal_open_contract" in data:
                return data["proposal_open_contract"]
            elif "error" in data:
                logger.error(f"Contract info error: {data['error']['message']}")
                return None

        except asyncio.TimeoutError:
            logger.error("Contract info request timeout")
            return None
        except Exception as e:
            logger.error(f"Contract info request failed: {e}")
            return None

    async def close(self):
        """Clean connection closure"""
        if self.ws:
            try:
                # Check if connection is open using websockets state attribute
                if hasattr(self.ws, 'state') and self.ws.state == websockets.protocol.State.OPEN:
                    await asyncio.wait_for(self.ws.close(), timeout=5)
            except asyncio.TimeoutError:
                logger.warning("WebSocket close timeout")
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")

        self.ws = None
        self.is_connected = False
        self.authorized = False
