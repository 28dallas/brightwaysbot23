import asyncio
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from utils.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)

class RiskManager:
    def __init__(self):
        self.active_positions = {}
        self.daily_stats = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'highest_balance': 10000.0,
            'daily_start_balance': 10000.0
        }
        self.session_start_balance = 10000.0
        self.max_concurrent_trades = Config.MAX_CONCURRENT_TRADES
        self.max_stake = Config.MAX_STAKE
        self.stop_loss_percent = Config.STOP_LOSS_PERCENT
        self.trailing_stop_loss_percent = Config.TRAILING_STOP_LOSS_PERCENT
        self.take_profit_percent = Config.TAKE_PROFIT_PERCENT
        self.max_drawdown_percent = Config.MAX_DRAWDOWN_PERCENT

    def can_place_trade(self, stake: float, contract_type: str) -> Dict[str, any]:
        """Check if a trade can be placed based on risk management rules"""

        current_balance = self.daily_stats['daily_start_balance'] + self.daily_stats['total_pnl']
        if current_balance <= 0:
            return {
                'allowed': False,
                'reason': 'Account balance is zero or negative. Trading stopped.'
            }
        # Check concurrent trades limit
        if len(self.active_positions) >= self.max_concurrent_trades:
            return {
                'allowed': False,
                'reason': f'Maximum concurrent trades ({self.max_concurrent_trades}) reached'
            }

        # Check stake limits
        if stake > self.max_stake:
            return {
                'allowed': False,
                'reason': f'Stake (${stake}) exceeds maximum allowed (${self.max_stake})'
            }

        # Check drawdown limits
        current_drawdown = self._calculate_drawdown()
        if current_drawdown >= self.max_drawdown_percent:
            return {
                'allowed': False,
                'reason': f'Maximum drawdown ({self.max_drawdown_percent}%) reached'
            }

       # Check if trailing stop loss percent is configured correctly
        if self.trailing_stop_loss_percent <= 0:
            return{
                'allowed': False,
                'reason': f'Trailing Stop Loss Percent must be greater than 0'
            }
        # Check minimum trade interval (30 seconds between trades)
        last_trade_time = self._get_last_trade_time()
        if last_trade_time and (time.time() - last_trade_time) < Config.MIN_TRADE_INTERVAL:
            return {
                'allowed': False,
                'reason': f'Minimum trade interval ({Config.MIN_TRADE_INTERVAL}s) not met'
            }

        return {'allowed': True}

    def calculate_optimal_stake(self, confidence: float, volatility: float = 1.0) -> float:
        """Calculate optimal stake based on confidence and volatility"""
        base_stake = Config.DEFAULT_STAKE

        # Adjust for confidence (higher confidence = higher stake)
        confidence_multiplier = min(confidence * 2, 3.0)  # Max 3x multiplier
        confidence_multiplier = confidence_multiplier * (1 + (self.daily_stats['win_rate'] / 100))

        # Adjust for volatility (higher volatility = lower stake)
        volatility_multiplier = max(0.5, 1.0 / volatility)
        #Risk Aversion based on drawdown
        risk_aversion = 1 - (self._calculate_drawdown() / self.max_drawdown_percent)
        optimal_stake = base_stake * confidence_multiplier * volatility_multiplier
        return min(optimal_stake, self.max_stake)

    def add_position(self, contract_id: str, stake: float, entry_price: float,
                    contract_type: str, prediction: str):
        """Add a new position to risk management"""
        self.active_positions[contract_id] = {
            'contract_id': contract_id,
            'initial_stake': stake,
            'current_stake': stake,
            'entry_price': entry_price,
            'contract_type': contract_type,
            'initial_pnl': self.daily_stats['total_pnl'],
            'prediction': prediction,
            'entry_time': time.time(),
            'stop_loss': self._calculate_stop_loss(entry_price, stake),
            'take_profit': self._calculate_take_profit(entry_price, stake)
        }

        logger.info(f"Added position {contract_id}: stake=${stake}, entry={entry_price}")

    def update_position(self, contract_id: str, current_price: float,
                       pnl: float, status: str):
        """Update position with current market data"""
        if contract_id not in self.active_positions:
            return

        position = self.active_positions[contract_id]
        position['current_price'] = current_price
        position['pnl'] = pnl
        position['status'] = status

        # Check stop loss
        if self._should_stop_loss(position):
            logger.warning(f"Stop loss triggered for {contract_id}")
            return 'stop_loss'

        # Check trailing stop loss
        if self._should_trailing_stop_loss(position):
            logger.info(f"Trailing stop loss triggered for {contract_id}")
            return 'trailing_stop_loss'
        # Check take profit
        if self._should_take_profit(position):
            logger.info(f"Take profit triggered for {contract_id}")
            return 'take_profit'

        return None

    def close_position(self, contract_id: str, pnl: float, status: str):
        """Close a position and update statistics"""
        if contract_id in self.active_positions:
            position = self.active_positions[contract_id]

            # Update daily statistics
            self.daily_stats['trades'] += 1
            self.daily_stats['total_pnl'] += pnl

            if pnl > 0:
                self.daily_stats['wins'] += 1
            else:
                self.daily_stats['losses'] += 1

            # Update max drawdown
            current_balance = self.daily_stats['daily_start_balance'] + self.daily_stats['total_pnl']
            self.daily_stats['highest_balance'] = max(self.daily_stats['highest_balance'], current_balance)
            current_drawdown = self._calculate_drawdown()
            self.daily_stats['max_drawdown'] = max(self.daily_stats['max_drawdown'], current_drawdown)

            logger.info(f"Closed position {contract_id}: PnL=${pnl:.2f}, Status={status}")

            del self.active_positions[contract_id]

    def get_risk_metrics(self) -> Dict[str, any]:
        """Get current risk management metrics"""
        return {
            'active_positions': len(self.active_positions),
            'max_concurrent': self.max_concurrent_trades,
            'current_drawdown': self._calculate_drawdown(),
            'max_drawdown_limit': self.max_drawdown_percent,
            'daily_trades': self.daily_stats['trades'],
            'daily_win_rate': self._calculate_win_rate(),
            'daily_pnl': self.daily_stats['total_pnl'],
            'session_pnl': self.session_start_balance - 10000.0 + self.daily_stats['total_pnl']
        }

    def reset_daily_stats(self):
        """Reset daily statistics (call at start of new trading day)"""
        self.daily_stats = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'daily_start_balance': 10000.0
        }
        logger.info("Daily statistics reset")

    def _calculate_drawdown(self) -> float:
        """Calculate current drawdown percentage"""
        if not self.daily_stats['trades']:
            return 0.0

        peak_balance = self.daily_stats['daily_start_balance']
        current_balance = self.daily_stats['daily_start_balance'] + self.daily_stats['total_pnl']

        if current_balance > peak_balance:
            peak_balance = current_balance

        if peak_balance == 0:
            return 0.0

        drawdown = ((peak_balance - current_balance) / peak_balance) * 100
        return max(0, drawdown)

    def _calculate_win_rate(self) -> float:    
        """Calculate current win rate"""
        total_trades = self.daily_stats['trades']
        if total_trades == 0:
            return 0.0
        return (self.daily_stats['wins'] / total_trades) * 100

    def _calculate_stop_loss(self, entry_price: float, stake: float) -> float:
        """Calculate stop loss price"""
        stop_loss_amount = stake * (self.stop_loss_percent / 100)
        return entry_price - stop_loss_amount


    def _calculate_take_profit(self, entry_price: float, stake: float) -> float:
        """Calculate take profit price"""
        take_profit_amount = stake * (self.take_profit_percent / 100)
        return entry_price + take_profit_amount

    def _should_stop_loss(self, position: Dict) -> bool:

        """Check if position should be stopped due to loss"""
        if 'current_price' not in position:
            return False
        return position['current_price'] <= position['stop_loss']

    def _should_take_profit(self, position: Dict) -> bool:
        """Check if position should be closed for profit"""
        if 'current_price' not in position:
            return False
        return position['current_price'] >= position['take_profit']

    def _should_trailing_stop_loss(self, position: Dict) -> bool:

        """Check if trailing stop loss should be triggered"""
        if 'current_price' not in position:
            return False

        # Calculate the trailing stop loss level
        #trailing_stop_loss_level = position['entry_price'] + (position['entry_price'] * (self.trailing_stop_loss_percent / 100))

        trailing_stop_loss_level = position['entry_price'] * (1 + (self.trailing_stop_loss_percent / 100))
        return position['current_price'] <= trailing_stop_loss_level

    def _get_last_trade_time(self) -> Optional[float]:
        """Get timestamp of last trade"""
        if not self.active_positions:
            return None

        last_times = [pos['entry_time'] for pos in self.active_positions.values()]
        return max(last_times) if last_times else None
