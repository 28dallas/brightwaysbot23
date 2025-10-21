import numpy as np
from typing import Dict, List, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os
from utils.logger import setup_logger

logger = setup_logger(__name__)

class EnhancedAIPredictor:
    def __init__(self):
        self.price_history = []
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_path = "ai_model.pkl"
        
    def add_price(self, price: float, volume: float = 1.0):
        """Add price data with volume"""
        self.price_history.append({'price': price, 'volume': volume, 'timestamp': len(self.price_history)})
        if len(self.price_history) > 1000:
            self.price_history.pop(0)
    
    def extract_features(self, lookback: int = 20) -> Optional[np.ndarray]:
        """Extract technical features from price history"""
        if len(self.price_history) < lookback:
            return None
            
        prices = np.array([p['price'] for p in self.price_history[-lookback:]])
        
        # Technical indicators
        returns = np.diff(prices) / prices[:-1]
        sma_5 = np.mean(prices[-5:])
        sma_10 = np.mean(prices[-10:])
        volatility = np.std(returns[-10:]) if len(returns) >= 10 else 0
        
        # Price position relative to moving averages
        current_price = prices[-1]
        price_vs_sma5 = (current_price - sma_5) / sma_5
        price_vs_sma10 = (current_price - sma_10) / sma_10
        
        # Momentum indicators
        momentum_5 = (prices[-1] - prices[-6]) / prices[-6] if len(prices) >= 6 else 0
        momentum_10 = (prices[-1] - prices[-11]) / prices[-11] if len(prices) >= 11 else 0
        
        # Last digit patterns
        last_digits = [int(str(p).split('.')[-1][-1]) for p in prices[-10:] if '.' in str(p)]
        digit_mean = np.mean(last_digits) if last_digits else 5
        digit_std = np.std(last_digits) if len(last_digits) > 1 else 0
        
        features = np.array([
            price_vs_sma5, price_vs_sma10, volatility, momentum_5, momentum_10,
            digit_mean, digit_std, len(returns)
        ])
        
        return features.reshape(1, -1)
    
    def predict_next_digit(self) -> Dict:
        """Enhanced prediction with ML model"""
        if len(self.price_history) < 20:
            return {'prediction': 5, 'confidence': 0.5, 'signal': 'neutral'}
        
        try:
            features = self.extract_features()
            if features is None:
                return self._fallback_prediction()
            
            if self.is_trained:
                # Use trained model
                features_scaled = self.scaler.transform(features)
                prediction_proba = self.model.predict_proba(features_scaled)[0]
                prediction = np.argmax(prediction_proba)
                confidence = np.max(prediction_proba)
            else:
                # Fallback to pattern-based prediction
                return self._fallback_prediction()
            
            # Determine signal
            recent_prices = [p['price'] for p in self.price_history[-5:]]
            trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            signal = 'buy' if trend > 0.001 else 'sell' if trend < -0.001 else 'neutral'
            
            return {
                'prediction': int(prediction),
                'confidence': float(confidence),
                'signal': signal,
                'trend': float(trend),
                'model_used': 'ml' if self.is_trained else 'pattern'
            }
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return self._fallback_prediction()
    
    def _fallback_prediction(self) -> Dict:
        """Fallback pattern-based prediction"""
        recent_prices = np.array([p['price'] for p in self.price_history[-20:]])
        price_changes = np.diff(recent_prices)
        
        trend = float(np.mean(price_changes))
        volatility = np.std(price_changes)
        
        # Last digit analysis
        last_digits = [int(str(p).split('.')[-1][-1]) for p in recent_prices if '.' in str(p)]
        if last_digits:
            digit_freq = np.bincount(last_digits, minlength=10)
            least_common = np.argmin(digit_freq)
            confidence = min(0.8, 0.5 + abs(trend) * 100 + volatility * 10)
            
            signal = 'buy' if trend > 0 else 'sell' if trend < 0 else 'neutral'
            
            return {
                'prediction': least_common,
                'confidence': confidence,
                'signal': signal,
                'trend': trend,
                'model_used': 'pattern'
            }
        
        return {'prediction': 5, 'confidence': 0.5, 'signal': 'neutral', 'model_used': 'random'}
    
    def train_model(self, historical_data: List[Dict]):
        """Train the ML model with historical data"""
        try:
            if len(historical_data) < 100:
                logger.warning("Insufficient data for training")
                return False
            
            X, y = [], []
            for i in range(20, len(historical_data)):
                # Use historical prices to create features
                prices = [d['price'] for d in historical_data[i-20:i]]
                features = self._extract_features_from_prices(prices)
                if features is not None:
                    X.append(features)
                    # Target: next digit
                    next_price = historical_data[i]['price']
                    next_digit = int(str(next_price).split('.')[-1][-1]) if '.' in str(next_price) else 5
                    y.append(next_digit)
            
            if len(X) < 50:
                return False
                
            X = np.array(X)
            y = np.array(y)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train model
            self.model.fit(X_scaled, y)
            self.is_trained = True
            
            # Save model
            joblib.dump({'model': self.model, 'scaler': self.scaler}, self.model_path)
            logger.info(f"Model trained with {len(X)} samples")
            
            return True
            
        except Exception as e:
            logger.error(f"Model training error: {e}")
            return False
    
    def _extract_features_from_prices(self, prices: List[float]) -> Optional[np.ndarray]:
        """Extract features from a list of prices"""
        if len(prices) < 20:
            return None
            
        prices = np.array(prices)
        returns = np.diff(prices) / prices[:-1]
        
        sma_5 = np.mean(prices[-5:])
        sma_10 = np.mean(prices[-10:])
        volatility = np.std(returns[-10:])
        
        current_price = prices[-1]
        price_vs_sma5 = (current_price - sma_5) / sma_5
        price_vs_sma10 = (current_price - sma_10) / sma_10
        
        momentum_5 = (prices[-1] - prices[-6]) / prices[-6] if len(prices) >= 6 else 0
        momentum_10 = (prices[-1] - prices[-11]) / prices[-11] if len(prices) >= 11 else 0
        
        last_digits = [int(str(p).split('.')[-1][-1]) for p in prices[-10:] if '.' in str(p)]
        digit_mean = np.mean(last_digits) if last_digits else 5
        digit_std = np.std(last_digits) if len(last_digits) > 1 else 0
        
        return np.array([price_vs_sma5, price_vs_sma10, volatility, momentum_5, momentum_10, digit_mean, digit_std, len(returns)])
    
    def load_model(self):
        """Load pre-trained model"""
        try:
            if os.path.exists(self.model_path):
                data = joblib.load(self.model_path)
                self.model = data['model']
                self.scaler = data['scaler']
                self.is_trained = True
                logger.info("Model loaded successfully")
                return True
        except Exception as e:
            logger.error(f"Model loading error: {e}")
        return False