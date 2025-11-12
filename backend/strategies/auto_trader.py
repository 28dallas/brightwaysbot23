import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from ai.predictor import EnhancedAIPredictor
from ai.auto_trading_controller import AutoTradingController
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
        self.trading_controller = AutoTradingController()
        self.strategies = {}
        
    async def start_auto_trading(self, user_id: int, strategy_config: Dict, api_token: Optional[str] = None):
        """Start automated trading for a user"""
        if self.is_running:
            logger.warning(f"Auto trading is already running for user {user_id}.")
            return

        self.is_running = True
        self._current_user_id = user_id
        logger.info(f"Starting auto trading for user {user_id}")
        
        # Determine if this is demo or live trading
        is_demo = api_token is None
        
        if not is_demo:
            # Connect to Deriv for live trading
            connected = await self.trader.connect(api_token=api_token, is_demo=False)
            if not connected or not self.trader.authorized:
                logger.error(f"Failed to connect to Deriv for user {user_id}. Stopping auto-trader.")
                self.is_running = False
                return
            
            logger.info(f"Connected to Deriv in live mode for auto trading")
        else:
            logger.info(f"Starting demo auto trading for user {user_id}")
            self._demo_balance = 10000.0

        try:
            trade_count = 0
            while self.is_running:
                logger.info(f"Auto trading loop iteration {trade_count + 1}")
                
                # Get AI prediction
                try:
                    prediction = self.predictor.predict_next_digit()
                    logger.info(f"AI prediction: {prediction}")
                except Exception as e:
                    logger.error(f"AI prediction failed: {e}")
                    prediction = {'prediction': 5, 'confidence': 0.5}  # Fallback
                
                # Get current market data for AI analysis
                try:
                    current_price = await self._get_current_market_price()
                    market_data = {
                        'price': current_price,
                        'volume': 1.0,
                        'timestamp': datetime.now()
                    }
                except Exception as e:
                    logger.error(f"Failed to get market data: {e}")
                    market_data = {'price': 100.0, 'volume': 1.0}  # Fallback
                
                # Prepare trade request
                balance = await self._get_user_balance(user_id)
                logger.info(f"Current balance: ${balance}")
                
                if strategy_config.get('type') == 'fixed_stake':
                    stake = strategy_config.get('fixed_stake_amount', 1.0)
                else:
                    stake = 1.0  # Fixed stake for now
                
                trade_request = {
                    "contract_type": strategy_config['contract_type'],
                    "symbol": strategy_config['symbol'],
                    "amount": stake,
                    "duration": strategy_config['duration'],
                    "duration_unit": strategy_config['duration_unit'],
                    "currency": "USD"
                }
                
                # AI-POWERED TRADING DECISION
                trading_decision = await self.trading_controller.should_execute_trade(
                    market_data, prediction, trade_request
                )
                
                logger.info(f"AI Trading Decision: {trading_decision}")
                
                # Check if AI approves the trade
                if not trading_decision.get('execute_trade', False):
                    logger.warning(f"Trade blocked by AI: {trading_decision.get('reason', 'Unknown')}")
                    logger.info(f"Alternative action: {trading_decision.get('alternative_action', 'Wait')}")
                    
                    # Wait longer if market conditions are bad
                    wait_time = strategy_config.get('check_interval', 30)
                    if trading_decision.get('risk_level') == 'CRITICAL':
                        wait_time *= 3  # Wait 3x longer for critical conditions
                    elif trading_decision.get('risk_level') == 'HIGH':
                        wait_time *= 2  # Wait 2x longer for high risk
                    
                    await asyncio.sleep(wait_time)
                    continue
                
                # Use AI-recommended stake if available
                recommended_stake = trading_decision.get('recommended_stake', stake)
                if recommended_stake != stake:
                    logger.info(f"AI recommends stake adjustment: ${stake} -> ${recommended_stake}")
                    trade_request['amount'] = recommended_stake
                    stake = recommended_stake
                
                # Use AI-optimized contract if available
                optimized_contract = trading_decision.get('optimized_contract', {})
                if optimized_contract.get('contract_type') != trade_request['contract_type']:
                    logger.info(f"AI recommends contract change: {trade_request['contract_type']} -> {optimized_contract.get('contract_type')}")
                    trade_request['contract_type'] = optimized_contract.get('contract_type')
                    trade_request['duration'] = optimized_contract.get('duration', trade_request['duration'])
                
                logger.info(f"AI-approved trade with confidence: {trading_decision.get('confidence', 0):.2f}")

                # Final risk management check
                final_risk_check = self.risk_manager.can_place_trade(stake, trade_request['contract_type'])
                if not final_risk_check['allowed']:
                    logger.warning(f"Final risk check failed: {final_risk_check['reason']}")
                    await asyncio.sleep(strategy_config.get('check_interval', 30))
                    continue
                
                # Add prediction-based parameters only when needed
                if strategy_config['contract_type'] == 'DIGITMATCH':
                    trade_request['barrier'] = str(prediction['prediction'])
                # DIGITEVEN/DIGITODD don't need barrier or prediction parameters
                
                logger.info(f"Placing trade: {trade_request}")
                
                # Execute trade (real or demo)
                if is_demo:
                    result = await self._simulate_trade(trade_request)
                else:
                    result = await self._execute_trade(user_id, trade_request)
                
                logger.info(f"Trade execution result: {result}")
                
                if result.get('success') or 'buy' in result:
                    contract_id = result.get('contract_id') or result.get('buy', {}).get('contract_id')
                    logger.info(f"Auto trade executed successfully: {contract_id}")
                    trade_count += 1
                    
                    # Record successful trade execution
                    self.trading_controller.record_trade_outcome('pending', 0.0)
                else:
                    logger.error(f"Auto trade failed: {result.get('error')}")
                    logger.error(f"Full result: {result}")
                    
                    # Record failed trade attempt
                    self.trading_controller.record_trade_outcome('failed', 0.0)
                
                # Sync balance after each trade
                try:
                    if not is_demo and self.trader.authorized:
                        current_balance = await self.trader.get_balance()
                        if current_balance is not None:
                            from models.database import SessionLocal, User
                            db = SessionLocal()
                            try:
                                user = db.query(User).filter(User.id == user_id).first()
                                if user and abs(user.balance - current_balance) > 0.01:
                                    user.balance = current_balance
                                    db.commit()
                                    logger.info(f"Balance re-synced: ${current_balance:.2f}")
                            finally:
                                db.close()
                except Exception as e:
                    logger.error(f"Balance re-sync failed: {e}")
                
                # Dynamic wait time based on AI analysis
                base_interval = strategy_config.get('trade_interval', 60)
                
                # Adjust interval based on market conditions
                if trading_decision.get('risk_level') == 'LOW':
                    trade_interval = base_interval * 0.8  # Trade more frequently in safe conditions
                elif trading_decision.get('risk_level') == 'HIGH':
                    trade_interval = base_interval * 1.5  # Trade less frequently in risky conditions
                else:
                    trade_interval = base_interval
                
                logger.info(f"Waiting {trade_interval:.0f} seconds before next trade (Risk: {trading_decision.get('risk_level', 'UNKNOWN')})")
                await asyncio.sleep(trade_interval)
                
        except Exception as e:
            logger.error(f"Auto trading error: {e}")
            import traceback
            logger.error(f"Auto trading traceback: {traceback.format_exc()}")
            
            # Pause trading on critical errors
            self.trading_controller.pause_trading(f"Critical error: {str(e)[:100]}")
        finally:
            # Close connection when trading stops
            if not is_demo:
                try:
                    await self.trader.close()
                except Exception as e:
                    logger.error(f"Error closing trader: {e}")
            self.is_running = False
            
            # Log final session statistics
            final_stats = self.trading_controller.get_trading_status()
            logger.info(f"Auto trading session ended for user {user_id}")
            logger.info(f"Session stats: {final_stats['session_stats']}")
    
    def stop_auto_trading(self):
        """Stop automated trading"""
        logger.info("Stop auto trading requested")
        self.is_running = False
        self.trading_controller.pause_trading("Manual stop requested")
    
    async def _get_current_market_price(self) -> float:
        """Get current market price from Deriv or use fallback"""
        try:
            if self.trader and self.trader.is_connected:
                # Try to get current tick price
                tick_data = await self.trader.get_tick_data()
                if tick_data and 'tick' in tick_data:
                    return float(tick_data['tick']['quote'])
        except Exception as e:
            logger.error(f"Failed to get current market price: {e}")
        
        # Fallback: generate realistic price
        import random
        base_price = 100.0
        return base_price + random.uniform(-5, 5)
    
    async def _get_user_balance(self, user_id: int) -> float:
        """Get user balance from database or trader"""
        # For demo mode, return the demo balance
        if hasattr(self, '_demo_balance'):
            return self._demo_balance
        
        # For live mode, get balance from trader
        if self.trader and self.trader.is_connected and self.trader.authorized:
            balance = await self.trader.get_balance()
            return balance if balance is not None else 1000.0
        
        # Fallback: get from database
        try:
            from models.database import SessionLocal, User
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                return user.balance if user else 1000.0
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error getting user balance: {e}")
            return 1000.0

    async def _execute_trade(self, user_id: int, trade_request: Dict) -> Dict:
        """Execute a real trade for the user"""
        try:
            logger.info(f"Executing REAL trade for user {user_id}: {trade_request}")
            
            # Place real trade on Deriv
            result = await self.trader.buy_contract(trade_request)
            logger.info(f"Real trade result: {result}")
            
            if "buy" in result:
                # Update user balance from Deriv immediately
                try:
                    await asyncio.sleep(1)  # Wait for trade to process
                    new_balance = await self.trader.get_balance()
                    if new_balance is not None:
                        from models.database import SessionLocal, User
                        db = SessionLocal()
                        try:
                            user = db.query(User).filter(User.id == user_id).first()
                            if user:
                                old_balance = user.balance
                                user.balance = new_balance
                                db.commit()
                                logger.info(f"Balance synced: ${old_balance:.2f} -> ${new_balance:.2f}")
                        finally:
                            db.close()
                except Exception as e:
                    logger.error(f"Balance sync failed: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Trade execution exception: {e}")
            return {"error": str(e)}
    
    async def _simulate_trade(self, trade_request: Dict) -> Dict:
        """Simulate a trade for demo mode"""
        import random
        from models.database import SessionLocal, User, Trade
        
        # Simulate trade result
        win = random.random() > 0.5
        stake = trade_request['amount']
        
        if win:
            payout = stake * 1.8  # 80% profit
            self._demo_balance += (payout - stake)
            pnl = payout - stake
        else:
            self._demo_balance -= stake
            payout = 0
            pnl = -stake
        
        logger.info(f"Demo trade: {'WIN' if win else 'LOSS'}, Balance: ${self._demo_balance:.2f}")
        
        contract_id = f"demo_{random.randint(1000, 9999)}"
        
        # Update database in a separate task to avoid blocking
        try:
            from models.database import SessionLocal, User, Trade
            db = SessionLocal()
            try:
                user_id = getattr(self, '_current_user_id', 1)
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.balance = self._demo_balance
                    
                    trade = Trade(
                        user_id=user_id,
                        stake=stake,
                        prediction=trade_request.get('prediction', 0),
                        result='win' if win else 'lose',
                        pnl=pnl,
                        contract_id=contract_id,
                        contract_type=trade_request['contract_type'],
                        is_demo=True,
                        confidence=0.5
                    )
                    db.add(trade)
                    db.commit()
                    logger.info(f"Trade recorded: {contract_id}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Database update failed: {e}")
        
        # Record trade outcome for AI learning
        outcome = "win" if win else "loss"
        try:
            self.trading_controller.record_trade_outcome(outcome, pnl)
        except:
            pass  # Don't let AI errors break demo trading
        
        return {
            "success": True,
            "contract_id": contract_id,
            "result": outcome,
            "payout": payout,
            "stake": stake
        }

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

    @staticmethod
    def create_fixed_stake_strategy(fixed_stake_amount: float = 1.0, min_confidence: float = 0.6):
        """Fixed stake strategy using a constant stake amount"""
        return {
            "name": "Fixed Stake",
            "type": "fixed_stake",
            "fixed_stake_amount": fixed_stake_amount,
            "min_confidence": min_confidence,
            "contract_type": "DIGITEVEN",
            "symbol": "R_100",
            "duration": 5,
            "duration_unit": "t",
            "check_interval": 30,
            "trade_interval": 60
        }
