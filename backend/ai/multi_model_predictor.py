import numpy as np
from typing import Dict, List, Optional
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import joblib
import os
from utils.logger import setup_logger

logger = setup_logger(__name__)

class MultiModelPredictor:
    def __init__(self):
        self.models = {
            'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'gradient_boost': GradientBoostingClassifier(n_estimators=100, random_state=42),
            'svm': SVC(probability=True, random_state=42),
            'neural_network': MLPClassifier(hidden_layer_sizes=(100, 50), random_state=42, max_iter=500)
        }
        
        self.scalers = {model: StandardScaler() for model in self.models.keys()}
        self.is_trained = {model: False for model in self.models.keys()}
        self.price_history = []
        self.model_dir = "ai_models"
        
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
    
    def add_price(self, price: float, volume: float = 1.0):
        """Add price data to history"""
        self.price_history.append({
            'price': price, 
            'volume': volume, 
            'timestamp': len(self.price_history)
        })
        if len(self.price_history) > 1000:
            self.price_history.pop(0)
    
    def extract_features(self, lookback: int = 30) -> Optional[np.ndarray]:
        """Extract comprehensive features for ML models"""
        if len(self.price_history) < lookback:
            return None
            
        prices = np.array([p['price'] for p in self.price_history[-lookback:]])
        
        # Price-based features
        returns = np.diff(prices) / prices[:-1]
        log_returns = np.diff(np.log(prices))
        
        # Moving averages
        sma_5 = np.mean(prices[-5:])
        sma_10 = np.mean(prices[-10:])
        sma_20 = np.mean(prices[-20:])
        ema_5 = self.calculate_ema(prices, 5)
        ema_10 = self.calculate_ema(prices, 10)
        
        # Volatility measures
        volatility_5 = np.std(returns[-5:]) if len(returns) >= 5 else 0
        volatility_10 = np.std(returns[-10:]) if len(returns) >= 10 else 0
        volatility_20 = np.std(returns[-20:]) if len(returns) >= 20 else 0
        
        # Price position indicators
        current_price = prices[-1]
        price_vs_sma5 = (current_price - sma_5) / sma_5
        price_vs_sma10 = (current_price - sma_10) / sma_10
        price_vs_sma20 = (current_price - sma_20) / sma_20
        
        # Momentum indicators
        momentum_3 = (prices[-1] - prices[-4]) / prices[-4] if len(prices) >= 4 else 0
        momentum_5 = (prices[-1] - prices[-6]) / prices[-6] if len(prices) >= 6 else 0
        momentum_10 = (prices[-1] - prices[-11]) / prices[-11] if len(prices) >= 11 else 0
        
        # RSI
        rsi = self.calculate_rsi(prices)
        
        # Bollinger Bands
        bb_upper, bb_lower, bb_middle = self.calculate_bollinger_bands(prices)
        bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
        
        # MACD
        macd, macd_signal = self.calculate_macd(prices)
        
        # Last digit patterns
        last_digits = [int(str(p).split('.')[-1][-1]) for p in prices[-15:] if '.' in str(p)]
        digit_mean = np.mean(last_digits) if last_digits else 5
        digit_std = np.std(last_digits) if len(last_digits) > 1 else 0
        digit_trend = np.polyfit(range(len(last_digits)), last_digits, 1)[0] if len(last_digits) > 1 else 0
        
        # Pattern recognition features
        even_count = sum(1 for d in last_digits if d % 2 == 0)
        odd_count = len(last_digits) - even_count
        even_odd_ratio = even_count / odd_count if odd_count > 0 else 1
        
        # Autocorrelation
        autocorr_1 = np.corrcoef(returns[:-1], returns[1:])[0, 1] if len(returns) > 1 else 0
        autocorr_5 = np.corrcoef(returns[:-5], returns[5:])[0, 1] if len(returns) > 5 else 0
        
        features = np.array([
            price_vs_sma5, price_vs_sma10, price_vs_sma20,
            volatility_5, volatility_10, volatility_20,
            momentum_3, momentum_5, momentum_10,
            rsi, bb_position, macd, macd_signal,
            digit_mean, digit_std, digit_trend,
            even_odd_ratio, autocorr_1, autocorr_5,
            ema_5, ema_10, len(returns)
        ])
        
        # Handle NaN values
        features = np.nan_to_num(features, nan=0.0, posinf=1.0, neginf=-1.0)
        
        return features.reshape(1, -1)
    
    def calculate_ema(self, prices, period):
        """Calculate Exponential Moving Average"""
        alpha = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema
    
    def calculate_rsi(self, prices, period=14):
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50
            
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return prices[-1], prices[-1], prices[-1]
            
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        return upper, lower, sma
    
    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """Calculate MACD"""
        if len(prices) < slow:
            return 0, 0
            
        ema_fast = self.calculate_ema(prices, fast)
        ema_slow = self.calculate_ema(prices, slow)
        
        macd_line = ema_fast - ema_slow
        
        # Simplified signal line calculation
        signal_line = macd_line * 0.9  # Approximation
        
        return macd_line, signal_line
    
    def predict_all_models(self) -> Dict:
        """Get predictions from all models"""
        features = self.extract_features()
        if features is None:
            return self._fallback_predictions()
        
        predictions = {}
        
        for model_name, model in self.models.items():
            try:
                if self.is_trained[model_name]:
                    # Scale features
                    features_scaled = self.scalers[model_name].transform(features)
                    
                    # Get prediction
                    if hasattr(model, 'predict_proba'):
                        proba = model.predict_proba(features_scaled)[0]
                        prediction = np.argmax(proba)
                        confidence = np.max(proba)
                    else:
                        prediction = model.predict(features_scaled)[0]
                        confidence = 0.7
                    
                    predictions[model_name] = {
                        'next_digit': int(prediction),
                        'confidence': float(confidence),
                        'signal': self._generate_signal(features_scaled[0], model_name),
                        'contract_type': self._suggest_contract_type(features_scaled[0], model_name),
                        'stake': self._calculate_optimal_stake(features_scaled[0]),
                        'duration': self._suggest_duration(model_name)
                    }
                else:
                    # Use fallback for untrained models
                    predictions[model_name] = self._model_fallback(model_name)
                    
            except Exception as e:
                logger.error(f"Error in {model_name} prediction: {e}")
                predictions[model_name] = self._model_fallback(model_name)
        
        # Add ensemble prediction
        predictions['ensemble'] = self._create_ensemble_prediction(predictions)
        
        return predictions
    
    def _generate_signal(self, features, model_name):
        """Generate trading signal based on features"""
        # Use different feature indices for different signals
        if model_name == 'random_forest':
            return 'BUY' if features[6] > 0 else 'SELL'  # momentum_3
        elif model_name == 'neural_network':
            return 'STRONG_BUY' if features[3] > 0.02 else 'BUY' if features[3] > 0 else 'SELL'
        elif model_name == 'svm':
            return 'BUY' if features[9] < 30 else 'SELL' if features[9] > 70 else 'HOLD'  # RSI
        elif model_name == 'gradient_boost':
            return 'BUY' if features[11] > features[12] else 'SELL'  # MACD
        else:
            return 'HOLD'
    
    def _suggest_contract_type(self, features, model_name):
        """Suggest contract type based on model and features"""
        contracts = ['DIGITEVEN', 'DIGITODD', 'CALL', 'PUT', 'DIGITDIFF', 'RANGE']
        
        if model_name == 'random_forest':
            return 'DIGITEVEN' if features[16] > 1 else 'DIGITODD'  # even_odd_ratio
        elif model_name == 'neural_network':
            return 'CALL' if features[0] > 0 else 'PUT'  # price_vs_sma5
        elif model_name == 'svm':
            return 'RANGE' if abs(features[10]) < 0.3 else 'CALL'  # bb_position
        else:
            return contracts[hash(model_name) % len(contracts)]
    
    def _calculate_optimal_stake(self, features):
        """Calculate optimal stake based on volatility and confidence"""
        volatility = abs(features[4])  # volatility_10
        base_stake = 5.0
        
        if volatility > 0.05:
            return base_stake * 0.5  # Reduce stake in high volatility
        elif volatility < 0.01:
            return base_stake * 1.5  # Increase stake in low volatility
        else:
            return base_stake
    
    def _suggest_duration(self, model_name):
        """Suggest trade duration based on model type"""
        durations = {
            'random_forest': 5,
            'neural_network': 3,
            'svm': 10,
            'gradient_boost': 7
        }
        return durations.get(model_name, 5)
    
    def _model_fallback(self, model_name):
        """Fallback prediction for untrained models"""
        return {
            'next_digit': np.random.randint(0, 10),
            'confidence': 0.5 + np.random.random() * 0.3,
            'signal': np.random.choice(['BUY', 'SELL', 'HOLD']),
            'contract_type': np.random.choice(['DIGITEVEN', 'DIGITODD', 'CALL', 'PUT']),
            'stake': 2.0 + np.random.random() * 3.0,
            'duration': np.random.choice([3, 5, 7, 10])
        }
    
    def _create_ensemble_prediction(self, predictions):
        """Create ensemble prediction from all models"""
        if not predictions:
            return self._model_fallback('ensemble')
        
        # Average predictions
        digits = [p['next_digit'] for p in predictions.values()]
        confidences = [p['confidence'] for p in predictions.values()]
        stakes = [p['stake'] for p in predictions.values()]
        
        # Most common signal
        signals = [p['signal'] for p in predictions.values()]
        signal_counts = {s: signals.count(s) for s in set(signals)}
        most_common_signal = max(signal_counts, key=signal_counts.get)
        
        return {
            'next_digit': int(np.round(np.mean(digits))),
            'confidence': np.mean(confidences),
            'signal': most_common_signal,
            'contract_type': 'DIGITEVEN',
            'stake': np.mean(stakes),
            'duration': 5
        }
    
    def _fallback_predictions(self):
        """Fallback when no features available"""
        return {model: self._model_fallback(model) for model in self.models.keys()}
    
    def train_models(self, historical_data: List[Dict]):
        """Train all models with historical data"""
        if len(historical_data) < 100:
            logger.warning("Insufficient data for training")
            return False
        
        # Prepare training data
        X, y = [], []
        for i in range(30, len(historical_data)):
            # Set price history for feature extraction
            self.price_history = historical_data[i-30:i]
            features = self.extract_features(30)
            
            if features is not None:
                X.append(features[0])
                # Target: next digit
                next_price = historical_data[i]['price']
                next_digit = int(str(next_price).split('.')[-1][-1]) if '.' in str(next_price) else 5
                y.append(next_digit)
        
        if len(X) < 50:
            logger.warning("Insufficient feature data for training")
            return False
        
        X = np.array(X)
        y = np.array(y)
        
        # Train each model
        for model_name, model in self.models.items():
            try:
                logger.info(f"Training {model_name}...")
                
                # Scale features
                X_scaled = self.scalers[model_name].fit_transform(X)
                
                # Train model
                model.fit(X_scaled, y)
                self.is_trained[model_name] = True
                
                # Save model
                model_path = os.path.join(self.model_dir, f"{model_name}.pkl")
                joblib.dump({
                    'model': model,
                    'scaler': self.scalers[model_name]
                }, model_path)
                
                logger.info(f"{model_name} trained successfully")
                
            except Exception as e:
                logger.error(f"Error training {model_name}: {e}")
        
        return True
    
    def load_models(self):
        """Load pre-trained models"""
        for model_name in self.models.keys():
            try:
                model_path = os.path.join(self.model_dir, f"{model_name}.pkl")
                if os.path.exists(model_path):
                    data = joblib.load(model_path)
                    self.models[model_name] = data['model']
                    self.scalers[model_name] = data['scaler']
                    self.is_trained[model_name] = True
                    logger.info(f"{model_name} loaded successfully")
            except Exception as e:
                logger.error(f"Error loading {model_name}: {e}")