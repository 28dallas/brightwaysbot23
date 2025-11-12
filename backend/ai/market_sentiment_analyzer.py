import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
from utils.logger import setup_logger

logger = setup_logger(__name__)

class MarketSentimentAnalyzer:
    """Advanced market sentiment analysis for optimal trading timing"""
    
    def __init__(self):
        self.price_data = []
        self.sentiment_history = []
        self.scaler = MinMaxScaler()
        self.lookback_period = 100
        
    def analyze_market_sentiment(self, current_price: float, volume: float = 1.0) -> Dict:
        """Comprehensive market sentiment analysis"""
        try:
            # Add current data
            self.price_data.append({
                'price': current_price,
                'volume': volume,
                'timestamp': datetime.now()
            })
            
            # Keep only recent data
            if len(self.price_data) > self.lookback_period:
                self.price_data = self.price_data[-self.lookback_period:]
            
            if len(self.price_data) < 20:
                return self._neutral_sentiment()
            
            # Calculate various sentiment indicators
            trend_sentiment = self._calculate_trend_sentiment()
            momentum_sentiment = self._calculate_momentum_sentiment()
            volatility_sentiment = self._calculate_volatility_sentiment()
            volume_sentiment = self._calculate_volume_sentiment()
            pattern_sentiment = self._calculate_pattern_sentiment()
            
            # Combine sentiments with weights
            overall_sentiment = (
                trend_sentiment * 0.25 +
                momentum_sentiment * 0.25 +
                volatility_sentiment * 0.20 +
                volume_sentiment * 0.15 +
                pattern_sentiment * 0.15
            )
            
            # Market regime detection
            market_regime = self._detect_market_regime()
            
            # Trading window analysis
            optimal_window = self._find_optimal_trading_window()
            
            sentiment_data = {
                'overall_sentiment': overall_sentiment,
                'trend_sentiment': trend_sentiment,
                'momentum_sentiment': momentum_sentiment,
                'volatility_sentiment': volatility_sentiment,
                'volume_sentiment': volume_sentiment,
                'pattern_sentiment': pattern_sentiment,
                'market_regime': market_regime,
                'optimal_trading_window': optimal_window,
                'sentiment_strength': abs(overall_sentiment),
                'market_direction': 'BULLISH' if overall_sentiment > 0.1 else 'BEARISH' if overall_sentiment < -0.1 else 'NEUTRAL',
                'confidence_level': self._calculate_confidence_level(overall_sentiment),
                'recommended_action': self._get_recommended_action(overall_sentiment, market_regime)
            }
            
            # Store sentiment history
            self.sentiment_history.append({
                'timestamp': datetime.now(),
                'sentiment': overall_sentiment,
                'regime': market_regime
            })
            
            if len(self.sentiment_history) > 200:
                self.sentiment_history = self.sentiment_history[-100:]
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"Market sentiment analysis failed: {e}")
            return self._neutral_sentiment()
    
    def _calculate_trend_sentiment(self) -> float:
        """Calculate trend-based sentiment (-1 to 1)"""
        prices = [d['price'] for d in self.price_data]
        
        if len(prices) < 10:
            return 0.0
        
        # Multiple timeframe trends
        short_trend = self._calculate_trend(prices[-5:])
        medium_trend = self._calculate_trend(prices[-15:])
        long_trend = self._calculate_trend(prices[-30:]) if len(prices) >= 30 else 0
        
        # Weighted trend sentiment
        trend_sentiment = (short_trend * 0.5 + medium_trend * 0.3 + long_trend * 0.2)
        
        # Normalize to -1 to 1
        return np.tanh(trend_sentiment * 100)
    
    def _calculate_momentum_sentiment(self) -> float:
        """Calculate momentum-based sentiment"""
        prices = [d['price'] for d in self.price_data]
        
        if len(prices) < 10:
            return 0.0
        
        # Rate of change indicators
        roc_3 = (prices[-1] - prices[-4]) / prices[-4] if len(prices) >= 4 else 0
        roc_5 = (prices[-1] - prices[-6]) / prices[-6] if len(prices) >= 6 else 0
        roc_10 = (prices[-1] - prices[-11]) / prices[-11] if len(prices) >= 11 else 0
        
        # RSI-like momentum
        gains = []
        losses = []
        for i in range(1, min(15, len(prices))):
            change = prices[-i] - prices[-i-1]
            if change > 0:
                gains.append(change)
            else:
                losses.append(abs(change))
        
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0
        
        if avg_loss == 0:
            rsi_momentum = 1.0
        else:
            rs = avg_gain / avg_loss
            rsi_momentum = (rs - 1) / (rs + 1)  # Normalize RSI to -1 to 1
        
        # Combine momentum indicators
        momentum_sentiment = (roc_3 * 0.4 + roc_5 * 0.3 + roc_10 * 0.2 + rsi_momentum * 0.1)
        
        return np.tanh(momentum_sentiment * 50)
    
    def _calculate_volatility_sentiment(self) -> float:
        """Calculate volatility-based sentiment (low volatility = positive for trading)"""
        prices = [d['price'] for d in self.price_data]
        
        if len(prices) < 10:
            return 0.0
        
        returns = np.diff(prices) / prices[:-1]
        
        # Current vs historical volatility
        current_vol = np.std(returns[-5:]) if len(returns) >= 5 else 0
        historical_vol = np.std(returns) if len(returns) > 0 else 0
        
        # Volatility ratio (lower is better for trading)
        vol_ratio = current_vol / (historical_vol + 1e-8)
        
        # Convert to sentiment (lower volatility = positive sentiment)
        volatility_sentiment = 1 - min(2, vol_ratio)  # Cap at -1
        
        return volatility_sentiment
    
    def _calculate_volume_sentiment(self) -> float:
        """Calculate volume-based sentiment"""
        volumes = [d['volume'] for d in self.price_data]
        
        if len(volumes) < 10:
            return 0.0
        
        # Volume trend
        recent_volume = np.mean(volumes[-5:])
        historical_volume = np.mean(volumes[:-5]) if len(volumes) > 5 else recent_volume
        
        volume_trend = (recent_volume - historical_volume) / (historical_volume + 1e-8)
        
        # Volume consistency
        volume_std = np.std(volumes[-10:]) if len(volumes) >= 10 else 0
        volume_mean = np.mean(volumes[-10:]) if len(volumes) >= 10 else 1
        volume_consistency = 1 - (volume_std / (volume_mean + 1e-8))
        
        # Combine volume indicators
        volume_sentiment = (volume_trend * 0.6 + volume_consistency * 0.4)
        
        return np.tanh(volume_sentiment)
    
    def _calculate_pattern_sentiment(self) -> float:
        """Calculate pattern-based sentiment for digit trading"""
        prices = [d['price'] for d in self.price_data]
        
        if len(prices) < 15:
            return 0.0
        
        # Extract last digits
        last_digits = []
        for price in prices[-15:]:
            try:
                digit = int(str(price).split('.')[-1][-1])
                last_digits.append(digit)
            except:
                continue
        
        if len(last_digits) < 10:
            return 0.0
        
        # Pattern analysis
        even_count = sum(1 for d in last_digits if d % 2 == 0)
        odd_count = len(last_digits) - even_count
        
        # Digit distribution entropy
        digit_counts = np.bincount(last_digits, minlength=10)
        digit_probs = digit_counts / len(last_digits)
        digit_probs = digit_probs[digit_probs > 0]
        entropy = -np.sum(digit_probs * np.log2(digit_probs))
        
        # Pattern predictability (lower entropy = more predictable)
        max_entropy = np.log2(10)  # Maximum possible entropy for 10 digits
        predictability = 1 - (entropy / max_entropy)
        
        # Even/odd bias
        even_odd_balance = 1 - abs(even_count - odd_count) / len(last_digits)
        
        # Combine pattern indicators
        pattern_sentiment = (predictability * 0.6 + even_odd_balance * 0.4)
        
        # Convert to -1 to 1 scale
        return (pattern_sentiment - 0.5) * 2
    
    def _detect_market_regime(self) -> str:
        """Detect current market regime"""
        prices = [d['price'] for d in self.price_data]
        
        if len(prices) < 20:
            return "UNKNOWN"
        
        returns = np.diff(prices) / prices[:-1]
        
        # Volatility analysis
        volatility = np.std(returns)
        
        # Trend analysis
        trend_slope = self._calculate_trend(prices)
        
        # Regime classification
        if volatility > 0.02:  # High volatility
            if abs(trend_slope) > 0.001:
                return "TRENDING_VOLATILE"
            else:
                return "RANGING_VOLATILE"
        else:  # Low volatility
            if abs(trend_slope) > 0.0005:
                return "TRENDING_STABLE"
            else:
                return "RANGING_STABLE"
    
    def _find_optimal_trading_window(self) -> Dict:
        """Find optimal trading time window"""
        if len(self.sentiment_history) < 10:
            return {"status": "insufficient_data", "window_start": None, "window_end": None}
        
        # Analyze sentiment patterns over time
        sentiments = [s['sentiment'] for s in self.sentiment_history[-50:]]
        
        # Find periods of consistent positive sentiment
        window_size = 5
        best_window_score = -1
        best_window_start = 0
        
        for i in range(len(sentiments) - window_size):
            window_sentiment = np.mean(sentiments[i:i+window_size])
            window_stability = 1 - np.std(sentiments[i:i+window_size])
            window_score = window_sentiment * 0.7 + window_stability * 0.3
            
            if window_score > best_window_score:
                best_window_score = window_score
                best_window_start = i
        
        # Current time analysis
        current_time = datetime.now()
        
        return {
            "status": "optimal" if best_window_score > 0.3 else "suboptimal",
            "window_score": best_window_score,
            "current_in_window": best_window_start <= len(sentiments) - window_size,
            "recommendation": "TRADE_NOW" if best_window_score > 0.5 else "WAIT_FOR_BETTER_WINDOW"
        }
    
    def _calculate_trend(self, prices: List[float]) -> float:
        """Calculate trend slope"""
        if len(prices) < 2:
            return 0.0
        
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]
        return slope / np.mean(prices)  # Normalize by price level
    
    def _calculate_confidence_level(self, sentiment: float) -> str:
        """Calculate confidence level based on sentiment strength"""
        strength = abs(sentiment)
        
        if strength > 0.7:
            return "VERY_HIGH"
        elif strength > 0.5:
            return "HIGH"
        elif strength > 0.3:
            return "MEDIUM"
        elif strength > 0.1:
            return "LOW"
        else:
            return "VERY_LOW"
    
    def _get_recommended_action(self, sentiment: float, regime: str) -> str:
        """Get recommended trading action"""
        if abs(sentiment) < 0.1:
            return "HOLD - Neutral market conditions"
        
        if regime in ["TRENDING_VOLATILE", "RANGING_VOLATILE"]:
            return "REDUCE_EXPOSURE - High volatility detected"
        
        if sentiment > 0.5:
            return "INCREASE_POSITION - Strong positive sentiment"
        elif sentiment > 0.2:
            return "NORMAL_TRADING - Positive sentiment"
        elif sentiment < -0.5:
            return "AVOID_TRADING - Strong negative sentiment"
        elif sentiment < -0.2:
            return "REDUCE_POSITION - Negative sentiment"
        else:
            return "CAUTIOUS_TRADING - Mixed signals"
    
    def _neutral_sentiment(self) -> Dict:
        """Return neutral sentiment when analysis fails"""
        return {
            'overall_sentiment': 0.0,
            'trend_sentiment': 0.0,
            'momentum_sentiment': 0.0,
            'volatility_sentiment': 0.0,
            'volume_sentiment': 0.0,
            'pattern_sentiment': 0.0,
            'market_regime': 'UNKNOWN',
            'optimal_trading_window': {"status": "unknown"},
            'sentiment_strength': 0.0,
            'market_direction': 'NEUTRAL',
            'confidence_level': 'VERY_LOW',
            'recommended_action': 'HOLD - Analysis unavailable'
        }
    
    def get_trading_signals(self) -> Dict:
        """Get specific trading signals based on current sentiment"""
        if not self.price_data:
            return {"signal": "NO_SIGNAL", "strength": 0, "contracts": []}
        
        latest_analysis = self.analyze_market_sentiment(self.price_data[-1]['price'])
        
        signals = []
        
        # Trend-based signals
        if latest_analysis['trend_sentiment'] > 0.3:
            signals.append({"type": "CALL", "strength": latest_analysis['trend_sentiment']})
        elif latest_analysis['trend_sentiment'] < -0.3:
            signals.append({"type": "PUT", "strength": abs(latest_analysis['trend_sentiment'])})
        
        # Pattern-based signals for digit trading
        if latest_analysis['pattern_sentiment'] > 0.2:
            signals.append({"type": "DIGITEVEN", "strength": latest_analysis['pattern_sentiment']})
        elif latest_analysis['pattern_sentiment'] < -0.2:
            signals.append({"type": "DIGITODD", "strength": abs(latest_analysis['pattern_sentiment'])})
        
        # Overall signal
        if latest_analysis['overall_sentiment'] > 0.4:
            main_signal = "STRONG_BUY"
        elif latest_analysis['overall_sentiment'] > 0.1:
            main_signal = "BUY"
        elif latest_analysis['overall_sentiment'] < -0.4:
            main_signal = "STRONG_SELL"
        elif latest_analysis['overall_sentiment'] < -0.1:
            main_signal = "SELL"
        else:
            main_signal = "HOLD"
        
        return {
            "signal": main_signal,
            "strength": abs(latest_analysis['overall_sentiment']),
            "contracts": signals,
            "market_regime": latest_analysis['market_regime'],
            "confidence": latest_analysis['confidence_level']
        }