import numpy as np
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import joblib
import os
from datetime import datetime, timedelta
from utils.logger import setup_logger

logger = setup_logger(__name__)

class LossPreventionAI:
    """AI model specifically designed to prevent losses by predicting dangerous market conditions"""
    
    def __init__(self):
        self.loss_predictor = IsolationForest(contamination=0.1, random_state=42)
        self.profit_classifier = RandomForestClassifier(n_estimators=200, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.market_history = []
        self.loss_threshold = 0.3  # Stop trading if loss probability > 30%
        self.profit_threshold = 0.7  # Only trade if profit probability > 70%
        
    def analyze_market_safety(self, market_data: Dict) -> Dict:
        """Analyze if current market conditions are safe for trading"""
        try:
            features = self._extract_safety_features(market_data)
            if features is None:
                return self._safe_fallback()
            
            # Predict loss probability
            loss_prob = self._predict_loss_probability(features)
            profit_prob = self._predict_profit_probability(features)
            
            # Market volatility analysis
            volatility_score = self._calculate_volatility_score(market_data)
            
            # Trend stability analysis
            trend_stability = self._analyze_trend_stability(market_data)
            
            # Overall safety score (0-100, higher is safer)
            safety_score = self._calculate_safety_score(loss_prob, profit_prob, volatility_score, trend_stability)
            
            # Trading recommendation
            should_trade = self._should_allow_trading(safety_score, loss_prob, profit_prob)
            
            return {
                'safe_to_trade': should_trade,
                'safety_score': safety_score,
                'loss_probability': loss_prob,
                'profit_probability': profit_prob,
                'volatility_score': volatility_score,
                'trend_stability': trend_stability,
                'recommendation': self._get_recommendation(safety_score, should_trade),
                'risk_level': self._get_risk_level(safety_score)
            }
            
        except Exception as e:
            logger.error(f"Market safety analysis failed: {e}")
            return self._safe_fallback()
    
    def _extract_safety_features(self, market_data: Dict) -> Optional[np.ndarray]:
        """Extract features specifically for loss prevention"""
        if len(self.market_history) < 20:
            return None
        
        prices = [d['price'] for d in self.market_history[-50:]]
        volumes = [d.get('volume', 1.0) for d in self.market_history[-50:]]
        
        # Price movement features
        returns = np.diff(prices) / prices[:-1]
        log_returns = np.diff(np.log(prices))
        
        # Volatility clustering detection
        volatility_5 = np.std(returns[-5:]) if len(returns) >= 5 else 0
        volatility_10 = np.std(returns[-10:]) if len(returns) >= 10 else 0
        volatility_20 = np.std(returns[-20:]) if len(returns) >= 20 else 0
        volatility_ratio = volatility_5 / volatility_10 if volatility_10 > 0 else 1
        
        # Trend consistency
        trend_5 = np.polyfit(range(5), prices[-5:], 1)[0] if len(prices) >= 5 else 0
        trend_10 = np.polyfit(range(10), prices[-10:], 1)[0] if len(prices) >= 10 else 0
        trend_consistency = abs(trend_5 - trend_10) / (abs(trend_10) + 1e-8)
        
        # Price gaps and jumps
        price_gaps = np.abs(np.diff(prices))
        max_gap = np.max(price_gaps[-10:]) if len(price_gaps) >= 10 else 0
        avg_gap = np.mean(price_gaps[-10:]) if len(price_gaps) >= 10 else 0
        gap_ratio = max_gap / (avg_gap + 1e-8)
        
        # Market momentum indicators
        momentum_3 = (prices[-1] - prices[-4]) / prices[-4] if len(prices) >= 4 else 0
        momentum_5 = (prices[-1] - prices[-6]) / prices[-6] if len(prices) >= 6 else 0
        momentum_divergence = abs(momentum_3 - momentum_5)
        
        # Volume analysis
        volume_trend = np.polyfit(range(len(volumes[-10:])), volumes[-10:], 1)[0] if len(volumes) >= 10 else 0
        volume_volatility = np.std(volumes[-10:]) if len(volumes) >= 10 else 0
        
        # Last digit pattern analysis (for digit trading)
        last_digits = [int(str(p).split('.')[-1][-1]) for p in prices[-15:] if '.' in str(p)]
        digit_entropy = self._calculate_entropy(last_digits) if last_digits else 0
        digit_bias = abs(np.mean(last_digits) - 4.5) if last_digits else 0
        
        # Market regime detection features
        price_range = (np.max(prices[-20:]) - np.min(prices[-20:])) / np.mean(prices[-20:]) if len(prices) >= 20 else 0
        price_acceleration = np.mean(np.diff(returns[-5:])) if len(returns) >= 6 else 0
        
        features = np.array([
            volatility_ratio, trend_consistency, gap_ratio,
            momentum_divergence, volume_trend, volume_volatility,
            digit_entropy, digit_bias, price_range, price_acceleration,
            volatility_5, volatility_10, volatility_20,
            momentum_3, momentum_5, max_gap, avg_gap
        ])
        
        return np.nan_to_num(features, nan=0.0).reshape(1, -1)
    
    def _predict_loss_probability(self, features: np.ndarray) -> float:
        """Predict probability of loss in current market conditions"""
        if not self.is_trained:
            return 0.5  # Neutral when not trained
        
        try:
            # Anomaly detection for dangerous conditions
            anomaly_score = self.loss_predictor.decision_function(features)[0]
            # Convert to probability (0-1, higher means more likely to lose)
            loss_prob = max(0, min(1, (1 - anomaly_score) / 2))
            return loss_prob
        except:
            return 0.5
    
    def _predict_profit_probability(self, features: np.ndarray) -> float:
        """Predict probability of profit in current market conditions"""
        if not self.is_trained:
            return 0.5
        
        try:
            profit_proba = self.profit_classifier.predict_proba(features)[0]
            return profit_proba[1] if len(profit_proba) > 1 else 0.5
        except:
            return 0.5
    
    def _calculate_volatility_score(self, market_data: Dict) -> float:
        """Calculate volatility score (0-100, lower is better for trading)"""
        if len(self.market_history) < 10:
            return 50
        
        prices = [d['price'] for d in self.market_history[-20:]]
        returns = np.diff(prices) / prices[:-1]
        
        current_vol = np.std(returns[-5:]) if len(returns) >= 5 else 0
        avg_vol = np.std(returns) if len(returns) > 0 else 0
        
        # Normalize volatility score (0-100)
        vol_ratio = current_vol / (avg_vol + 1e-8)
        volatility_score = min(100, vol_ratio * 50)
        
        return volatility_score
    
    def _analyze_trend_stability(self, market_data: Dict) -> float:
        """Analyze trend stability (0-100, higher is more stable)"""
        if len(self.market_history) < 15:
            return 50
        
        prices = [d['price'] for d in self.market_history[-15:]]
        
        # Calculate multiple trend lines
        short_trend = np.polyfit(range(5), prices[-5:], 1)[0]
        medium_trend = np.polyfit(range(10), prices[-10:], 1)[0]
        long_trend = np.polyfit(range(15), prices[-15:], 1)[0]
        
        # Measure trend consistency
        trend_consistency = 1 - (abs(short_trend - medium_trend) + abs(medium_trend - long_trend)) / 2
        stability_score = max(0, min(100, trend_consistency * 100))
        
        return stability_score
    
    def _calculate_safety_score(self, loss_prob: float, profit_prob: float, 
                               volatility_score: float, trend_stability: float) -> float:
        """Calculate overall safety score (0-100)"""
        # Weighted combination of factors
        safety_score = (
            (1 - loss_prob) * 30 +  # 30% weight on loss prevention
            profit_prob * 25 +       # 25% weight on profit probability
            (100 - volatility_score) * 25 +  # 25% weight on low volatility
            trend_stability * 20     # 20% weight on trend stability
        )
        
        return max(0, min(100, safety_score))
    
    def _should_allow_trading(self, safety_score: float, loss_prob: float, profit_prob: float) -> bool:
        """Determine if trading should be allowed"""
        # Multiple safety checks
        if loss_prob > self.loss_threshold:
            return False
        
        if profit_prob < self.profit_threshold:
            return False
        
        if safety_score < 60:  # Minimum safety threshold
            return False
        
        return True
    
    def _get_recommendation(self, safety_score: float, should_trade: bool) -> str:
        """Get trading recommendation"""
        if not should_trade:
            if safety_score < 30:
                return "STOP_TRADING_IMMEDIATELY - High risk detected"
            elif safety_score < 50:
                return "PAUSE_TRADING - Unfavorable conditions"
            else:
                return "WAIT - Market conditions not optimal"
        else:
            if safety_score > 80:
                return "TRADE_AGGRESSIVELY - Excellent conditions"
            elif safety_score > 70:
                return "TRADE_NORMALLY - Good conditions"
            else:
                return "TRADE_CAUTIOUSLY - Acceptable conditions"
    
    def _get_risk_level(self, safety_score: float) -> str:
        """Get risk level description"""
        if safety_score >= 80:
            return "LOW"
        elif safety_score >= 60:
            return "MEDIUM"
        elif safety_score >= 40:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def _calculate_entropy(self, data: List[int]) -> float:
        """Calculate entropy of digit sequence"""
        if not data:
            return 0
        
        counts = np.bincount(data, minlength=10)
        probs = counts / len(data)
        probs = probs[probs > 0]  # Remove zeros
        
        return -np.sum(probs * np.log2(probs))
    
    def add_market_data(self, price: float, volume: float = 1.0, outcome: Optional[str] = None):
        """Add market data point for analysis"""
        data_point = {
            'price': price,
            'volume': volume,
            'timestamp': datetime.now(),
            'outcome': outcome  # 'win', 'loss', or None
        }
        
        self.market_history.append(data_point)
        
        # Keep only recent data
        if len(self.market_history) > 1000:
            self.market_history = self.market_history[-500:]
    
    def train_models(self, historical_data: List[Dict]) -> bool:
        """Train loss prevention models"""
        if len(historical_data) < 100:
            logger.warning("Insufficient data for loss prevention training")
            return False
        
        try:
            # Prepare training data
            X, y_loss, y_profit = [], [], []
            
            for i in range(50, len(historical_data)):
                # Set market history for feature extraction
                self.market_history = historical_data[i-50:i]
                features = self._extract_safety_features({})
                
                if features is not None:
                    X.append(features[0])
                    
                    # Label for loss prediction (1 if next trade was a loss)
                    next_outcome = historical_data[i].get('outcome', 'unknown')
                    y_loss.append(1 if next_outcome == 'loss' else 0)
                    y_profit.append(1 if next_outcome == 'win' else 0)
            
            if len(X) < 50:
                logger.warning("Insufficient feature data for training")
                return False
            
            X = np.array(X)
            y_loss = np.array(y_loss)
            y_profit = np.array(y_profit)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train loss predictor (anomaly detection)
            normal_data = X_scaled[y_loss == 0]  # Only winning conditions
            if len(normal_data) > 10:
                self.loss_predictor.fit(normal_data)
            
            # Train profit classifier
            if len(set(y_profit)) > 1:  # Need both classes
                self.profit_classifier.fit(X_scaled, y_profit)
            
            self.is_trained = True
            logger.info("Loss prevention models trained successfully")
            
            # Save models
            self._save_models()
            
            return True
            
        except Exception as e:
            logger.error(f"Loss prevention training failed: {e}")
            return False
    
    def _save_models(self):
        """Save trained models"""
        try:
            model_dir = "ai_models"
            if not os.path.exists(model_dir):
                os.makedirs(model_dir)
            
            joblib.dump({
                'loss_predictor': self.loss_predictor,
                'profit_classifier': self.profit_classifier,
                'scaler': self.scaler,
                'is_trained': self.is_trained
            }, os.path.join(model_dir, "loss_prevention_models.pkl"))
            
            logger.info("Loss prevention models saved")
        except Exception as e:
            logger.error(f"Failed to save models: {e}")
    
    def load_models(self):
        """Load pre-trained models"""
        try:
            model_path = os.path.join("ai_models", "loss_prevention_models.pkl")
            if os.path.exists(model_path):
                data = joblib.load(model_path)
                self.loss_predictor = data['loss_predictor']
                self.profit_classifier = data['profit_classifier']
                self.scaler = data['scaler']
                self.is_trained = data['is_trained']
                logger.info("Loss prevention models loaded successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
        return False
    
    def _safe_fallback(self) -> Dict:
        """Safe fallback when analysis fails"""
        return {
            'safe_to_trade': True,
            'safety_score': 60,
            'loss_probability': 0.4,
            'profit_probability': 0.6,
            'volatility_score': 50,
            'trend_stability': 60,
            'recommendation': "TRADE_CAUTIOUSLY - Limited data available",
            'risk_level': "MEDIUM"
        }