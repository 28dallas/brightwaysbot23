import asyncio
import json
from typing import Dict, List, Optional
from utils.logger import setup_logger
from services.deriv_trader import DerivTrader

logger = setup_logger(__name__)

class ContractMonitor:
    def __init__(self):
        self.active_contracts = {}
        self.trader = DerivTrader()
        
    async def monitor_contract(self, contract_id: str, user_id: int, callback=None):
        """Monitor a contract until completion"""
        try:
            # Subscribe to contract updates
            proposal_request = {
                "proposal_open_contract": 1,
                "contract_id": contract_id
            }
            
            await self.trader.ws.send(json.dumps(proposal_request))
            
            while True:
                response = await self.trader.ws.recv()
                data = json.loads(response)
                
                if "proposal_open_contract" in data:
                    contract = data["proposal_open_contract"]
                    
                    # Check if contract is finished
                    if contract.get("is_sold") or contract.get("status") == "sold":
                        result = {
                            "contract_id": contract_id,
                            "pnl": float(contract.get("profit", 0)),
                            "result": "win" if float(contract.get("profit", 0)) > 0 else "lose",
                            "exit_tick": contract.get("exit_tick"),
                            "sell_price": contract.get("sell_price")
                        }
                        
                        if callback:
                            await callback(result)
                        
                        logger.info(f"Contract {contract_id} completed: {result}")
                        break
                        
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Contract monitoring error: {e}")
    
    async def sell_contract(self, contract_id: str, price: Optional[float] = None):
        """Sell an active contract"""
        try:
            sell_request = {"sell": contract_id}
            if price:
                sell_request["price"] = price
                
            await self.trader.ws.send(json.dumps(sell_request))
            response = await self.trader.ws.recv()
            
            return json.loads(response)
            
        except Exception as e:
            logger.error(f"Contract sell error: {e}")
            return {"error": str(e)}
    
    async def get_contract_status(self, contract_id: str):
        """Get current status of a contract"""
        try:
            status_request = {
                "proposal_open_contract": 1,
                "contract_id": contract_id
            }
            
            await self.trader.ws.send(json.dumps(status_request))
            response = await self.trader.ws.recv()
            data = json.loads(response)
            
            if "proposal_open_contract" in data:
                return data["proposal_open_contract"]
                
        except Exception as e:
            logger.error(f"Contract status error: {e}")
            
        return None