import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class SignalProcessor:
    def __init__(self):
        self.active_signals = {}
        self.risk_manager = None
        
    async def process_signal(self, signal: Dict[str, Any], source: str) -> Dict:
        """Process signals from TradingView or MT5"""
        try:
            # Validate signal
            if not self._validate_signal(signal):
                return {"status": "error", "message": "Invalid signal"}
            
            # Apply risk management
            if not await self._check_risk_limits(signal):
                return {"status": "rejected", "message": "Risk limits exceeded"}
            
            # Convert to Deriv trade parameters
            trade_params = await self._convert_to_deriv_params(signal, source)
            
            # Execute trade
            from ..trading.engine import execute_trade
            result = await execute_trade(trade_params)
            
            # Log signal execution
            self._log_signal_execution(signal, source, result)
            
            return {"status": "executed", "trade_id": result.get("contract_id")}
            
        except Exception as e:
            logger.error(f"Signal processing error: {e}")
            return {"status": "error", "message": str(e)}
    
    def _validate_signal(self, signal: Dict) -> bool:
        """Validate signal format and data"""
        required_fields = ["symbol", "action", "price"]
        return all(field in signal for field in required_fields)
    
    async def _check_risk_limits(self, signal: Dict) -> bool:
        """Check if signal passes risk management rules"""
        # Check daily trade limit
        today_trades = len([s for s in self.active_signals.values() 
                           if s.get("date") == datetime.now().date()])
        
        if today_trades >= 50:  # Max 50 trades per day
            return False
            
        # Check symbol exposure
        symbol_exposure = len([s for s in self.active_signals.values() 
                              if s.get("symbol") == signal["symbol"]])
        
        if symbol_exposure >= 3:  # Max 3 trades per symbol
            return False
            
        return True
    
    async def _convert_to_deriv_params(self, signal: Dict, source: str) -> Dict:
        """Convert external signal to Deriv trade parameters"""
        
        # Base parameters
        params = {
            "symbol": signal["symbol"],
            "contract_type": self._get_contract_type(signal),
            "duration": signal.get("duration", 5),
            "duration_unit": "t",  # ticks
            "basis": "stake",
            "amount": await self._calculate_stake(signal),
            "barrier": signal.get("price")
        }
        
        # Source-specific adjustments
        if source == "TradingView":
            params["contract_type"] = signal.get("contract_type", "CALL")
        elif source == "MT5":
            params["contract_type"] = "CALL" if signal["action"] == "buy" else "PUT"
            
        return params
    
    def _get_contract_type(self, signal: Dict) -> str:
        """Determine Deriv contract type from signal"""
        action = signal.get("action", "").lower()
        
        if action in ["buy", "call", "up"]:
            return "CALL"
        elif action in ["sell", "put", "down"]:
            return "PUT"
        else:
            return "CALL"  # Default
    
    async def _calculate_stake(self, signal: Dict) -> float:
        """Calculate optimal stake using risk management"""
        base_stake = 1.0
        
        # Apply Kelly Criterion if available
        confidence = signal.get("confidence", 0.6)
        win_rate = signal.get("win_rate", 0.55)
        
        if confidence > 0.7 and win_rate > 0.6:
            base_stake *= 1.5  # Increase stake for high confidence
        elif confidence < 0.5:
            base_stake *= 0.5  # Reduce stake for low confidence
            
        return min(base_stake, 10.0)  # Max stake limit
    
    def _log_signal_execution(self, signal: Dict, source: str, result: Dict):
        """Log signal execution for analysis"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "signal": signal,
            "result": result,
            "status": result.get("status")
        }
        
        logger.info(f"Signal executed: {log_entry}")
        
        # Store for tracking
        if result.get("contract_id"):
            self.active_signals[result["contract_id"]] = {
                "source": source,
                "signal": signal,
                "date": datetime.now().date(),
                "symbol": signal["symbol"]
            }

# Global signal processor
signal_processor = SignalProcessor()