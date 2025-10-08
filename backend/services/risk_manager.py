import numpy as np
from typing import Dict, List, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

class RiskManager:
    def __init__(self, max_risk_per_trade: float = 0.02, max_daily_loss: float = 0.1):
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_loss = max_daily_loss
        
    def calculate_position_size(self, balance: float, confidence: float, volatility: float = 0.1) -> float:
        """Calculate optimal position size using Kelly Criterion"""
        try:
            # Kelly Criterion: f = (bp - q) / b
            # where b = odds, p = win probability, q = loss probability
            win_prob = min(0.9, max(0.1, confidence))
            loss_prob = 1 - win_prob
            odds = 0.8  # Deriv payout ratio
            
            kelly_fraction = (odds * win_prob - loss_prob) / odds
            kelly_fraction = max(0, min(kelly_fraction, self.max_risk_per_trade))
            
            # Adjust for volatility
            volatility_adjustment = 1 - min(0.5, volatility)
            adjusted_fraction = kelly_fraction * volatility_adjustment
            
            position_size = balance * adjusted_fraction
            logger.info(f"Position size calculated: {position_size} (Kelly: {kelly_fraction:.3f})")
            
            return max(1.0, min(position_size, balance * self.max_risk_per_trade))
            
        except Exception as e:
            logger.error(f"Position size calculation error: {e}")
            return balance * 0.01  # Fallback to 1%
    
    def check_daily_risk_limit(self, daily_pnl: float, balance: float) -> bool:
        """Check if daily loss limit is exceeded"""
        daily_loss_pct = abs(daily_pnl) / balance if balance > 0 else 0
        return daily_loss_pct < self.max_daily_loss
    
    def should_stop_trading(self, recent_trades: List[Dict]) -> bool:
        """Determine if trading should be stopped based on recent performance"""
        if len(recent_trades) < 5:
            return False
            
        # Check for consecutive losses
        consecutive_losses = 0
        for trade in recent_trades[:10]:  # Last 10 trades
            if trade.get('pnl', 0) < 0:
                consecutive_losses += 1
            else:
                break
                
        if consecutive_losses >= 5:
            logger.warning("5 consecutive losses detected - recommending stop")
            return True
            
        # Check drawdown
        pnls = [t.get('pnl', 0) for t in recent_trades[:20]]
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        if max_drawdown > 1000:  # $1000 drawdown limit
            logger.warning(f"Max drawdown exceeded: ${max_drawdown}")
            return True
            
        return False