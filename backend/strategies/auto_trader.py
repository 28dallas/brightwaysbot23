import asyncio
from typing import Dict, List
from datetime import datetime, timedelta
from ai.predictor import EnhancedAIPredictor
from services.risk_manager import RiskManager
from services.deriv_trader import DerivTrader
from utils.logger import setup_logger

logger = setup_logger(__name__)

class AutoTrader:
    def __init__(self):
        self.is_running = False
        self.predictor = EnhancedAIPredictor()
        self.risk_manager = RiskManager()
        self.trader = DerivTrader()
        self.strategies = {}
        
    async def start_auto_trading(self, user_id: int, strategy_config: Dict):
        """Start automated trading for a user"""
        self.is_running = True
        logger.info(f"Starting auto trading for user {user_id}")
        
        try:
            while self.is_running:
                # Get AI prediction
                prediction = self.predictor.predict_next_digit()
                
                # Check if confidence meets threshold
                if prediction['confidence'] < strategy_config.get('min_confidence', 0.6):
                    await asyncio.sleep(strategy_config.get('check_interval', 30))
                    continue
                
                # Calculate position size
                balance = await self._get_user_balance(user_id)
                stake = self.risk_manager.calculate_position_size(
                    balance, prediction['confidence']
                )
                
                # Place trade based on strategy
                trade_request = {
                    "contract_type": strategy_config['contract_type'],
                    "symbol": strategy_config['symbol'],
                    "amount": stake,
                    "duration": strategy_config['duration'],
                    "duration_unit": strategy_config['duration_unit']
                }
                
                # Add prediction-based parameters
                if strategy_config['contract_type'] in ['DIGITEVEN', 'DIGITODD']:
                    trade_request['prediction'] = 1 if prediction['prediction'] % 2 else 0
                elif strategy_config['contract_type'] == 'DIGITMATCH':
                    trade_request['barrier'] = str(prediction['prediction'])
                elif strategy_config['contract_type'] in ['CALL', 'PUT']:
                    trade_request['prediction'] = 1 if prediction['signal'] == 'buy' else 0
                
                # Execute trade
                result = await self._execute_trade(user_id, trade_request)
                
                if result.get('success'):
                    logger.info(f"Auto trade executed: {result['contract_id']}")
                else:
                    logger.error(f"Auto trade failed: {result.get('error')}")
                
                # Wait before next trade
                await asyncio.sleep(strategy_config.get('trade_interval', 60))
                
        except Exception as e:
            logger.error(f"Auto trading error: {e}")
        finally:
            self.is_running = False
    
    def stop_auto_trading(self):
        """Stop automated trading"""
        self.is_running = False
        logger.info("Auto trading stopped")
    
    async def _get_user_balance(self, user_id: int) -> float:
        """Get user balance from database"""
        # This would query the database for user balance
        return 1000.0  # Placeholder
    
    async def _execute_trade(self, user_id: int, trade_request: Dict) -> Dict:
        """Execute a trade for the user"""
        try:
            # Connect to Deriv
            connected = await self.trader.connect()
            if not connected:
                return {"error": "Failed to connect to Deriv"}
            
            # Place trade
            result = await self.trader.buy_contract(trade_request)
            
            # Close connection
            await self.trader.close()
            
            return result
            
        except Exception as e:
            return {"error": str(e)}

class StrategyBuilder:
    """Build and manage trading strategies"""
    
    @staticmethod
    def create_martingale_strategy(base_stake: float = 1.0, multiplier: float = 2.0):
        """Martingale strategy - double stake after loss"""
        return {
            "name": "Martingale",
            "type": "progressive",
            "base_stake": base_stake,
            "multiplier": multiplier,
            "max_steps": 5,
            "reset_on_win": True
        }
    
    @staticmethod
    def create_anti_martingale_strategy(base_stake: float = 1.0, multiplier: float = 1.5):
        """Anti-Martingale - increase stake after win"""
        return {
            "name": "Anti-Martingale",
            "type": "progressive",
            "base_stake": base_stake,
            "multiplier": multiplier,
            "max_steps": 3,
            "reset_on_loss": True
        }
    
    @staticmethod
    def create_fibonacci_strategy(base_stake: float = 1.0):
        """Fibonacci progression strategy"""
        return {
            "name": "Fibonacci",
            "type": "progressive",
            "base_stake": base_stake,
            "sequence": [1, 1, 2, 3, 5, 8, 13, 21],
            "reset_on_win": True
        }
    
    @staticmethod
    def create_ai_confidence_strategy(min_confidence: float = 0.7):
        """AI-based strategy using confidence levels"""
        return {
            "name": "AI Confidence",
            "type": "ai_based",
            "min_confidence": min_confidence,
            "contract_type": "DIGITEVEN",
            "symbol": "R_100",
            "duration": 5,
            "duration_unit": "t",
            "check_interval": 30,
            "trade_interval": 60
        }