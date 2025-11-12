import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from ai.loss_prevention_ai import LossPreventionAI
from ai.market_sentiment_analyzer import MarketSentimentAnalyzer
from ai.multi_model_predictor import MultiModelPredictor
from services.risk_manager import RiskManager
from utils.logger import setup_logger

logger = setup_logger(__name__)

class AutoTradingController:
    """Intelligent trading controller that prevents losses and maximizes profits"""
    
    def __init__(self):
        self.loss_prevention_ai = LossPreventionAI()
        self.sentiment_analyzer = MarketSentimentAnalyzer()
        self.multi_predictor = MultiModelPredictor()
        self.risk_manager = RiskManager()
        
        # Trading control parameters
        self.is_trading_enabled = True
        self.auto_pause_enabled = True
        self.profit_protection_enabled = True
        
        # Safety thresholds (more permissive for demo)
        self.min_safety_score = 40
        self.min_profit_probability = 0.55
        self.max_loss_probability = 0.45
        self.min_confidence = 0.6
        
        # Performance tracking
        self.session_stats = {
            'trades_executed': 0,
            'trades_prevented': 0,
            'wins': 0,
            'losses': 0,
            'total_profit': 0.0,
            'max_consecutive_losses': 0,
            'current_consecutive_losses': 0,
            'last_trade_time': None
        }
        
        # Load pre-trained models
        self._load_models()
    
    async def should_execute_trade(self, market_data: Dict, prediction: Dict, 
                                 trade_request: Dict) -> Dict:
        """Comprehensive analysis to determine if trade should be executed"""
        try:
            # Update AI models with current market data
            current_price = market_data.get('price', 0)
            volume = market_data.get('volume', 1.0)
            
            self.loss_prevention_ai.add_market_data(current_price, volume)
            
            # 1. Loss Prevention Analysis
            safety_analysis = self.loss_prevention_ai.analyze_market_safety(market_data)
            
            # 2. Market Sentiment Analysis
            sentiment_analysis = self.sentiment_analyzer.analyze_market_sentiment(current_price, volume)
            
            # 3. Multi-Model Prediction Analysis
            self.multi_predictor.add_price(current_price, volume)
            model_predictions = self.multi_predictor.predict_all_models()
            
            # 4. Risk Management Check
            stake = trade_request.get('amount', 1.0)
            risk_check = self.risk_manager.can_place_trade(stake, trade_request.get('contract_type', 'DIGITEVEN'))
            
            # 5. Comprehensive Decision Making
            decision = self._make_trading_decision(
                safety_analysis, sentiment_analysis, model_predictions, 
                prediction, risk_check, trade_request
            )
            
            # 6. Update session statistics
            self._update_session_stats(decision)
            
            return decision
            
        except Exception as e:
            logger.error(f"Trade decision analysis failed: {e}")
            return self._safe_rejection("Analysis failed - safety first")
    
    def _make_trading_decision(self, safety_analysis: Dict, sentiment_analysis: Dict,
                              model_predictions: Dict, prediction: Dict, 
                              risk_check: Dict, trade_request: Dict) -> Dict:
        """Make intelligent trading decision based on all analyses"""
        
        # Initialize decision structure
        decision = {
            'execute_trade': False,
            'reason': '',
            'confidence': 0.0,
            'recommended_stake': 0.0,
            'alternative_action': '',
            'safety_score': safety_analysis.get('safety_score', 0),
            'market_conditions': sentiment_analysis.get('market_direction', 'UNKNOWN'),
            'risk_level': safety_analysis.get('risk_level', 'HIGH')
        }
        
        # Check if trading is globally enabled
        if not self.is_trading_enabled:
            decision['reason'] = "Trading manually disabled"
            decision['alternative_action'] = "Enable trading to continue"
            return decision
        
        # 1. Risk Management Check (Highest Priority)
        if not risk_check.get('allowed', False):
            decision['reason'] = f"Risk management block: {risk_check.get('reason', 'Unknown')}"
            decision['alternative_action'] = "Wait for risk conditions to improve"
            return decision
        
        # 2. Loss Prevention Check (Critical Safety)
        if not safety_analysis.get('safe_to_trade', False):
            decision['reason'] = f"Loss prevention block: {safety_analysis.get('recommendation', 'Unsafe conditions')}"
            decision['alternative_action'] = "Wait for safer market conditions"
            self.session_stats['trades_prevented'] += 1
            return decision
        
        # 3. Safety Score Check
        safety_score = safety_analysis.get('safety_score', 0)
        if safety_score < self.min_safety_score:
            decision['reason'] = f"Safety score too low: {safety_score:.1f} < {self.min_safety_score}"
            decision['alternative_action'] = "Wait for safety score to improve"
            return decision
        
        # 4. Loss Probability Check
        loss_prob = safety_analysis.get('loss_probability', 1.0)
        if loss_prob > self.max_loss_probability:
            decision['reason'] = f"Loss probability too high: {loss_prob:.2f} > {self.max_loss_probability}"
            decision['alternative_action'] = "Wait for lower loss probability"
            return decision
        
        # 5. Profit Probability Check
        profit_prob = safety_analysis.get('profit_probability', 0.0)
        if profit_prob < self.min_profit_probability:
            decision['reason'] = f"Profit probability too low: {profit_prob:.2f} < {self.min_profit_probability}"
            decision['alternative_action'] = "Wait for higher profit probability"
            return decision
        
        # 6. Prediction Confidence Check
        pred_confidence = prediction.get('confidence', 0.0)
        if pred_confidence < self.min_confidence:
            decision['reason'] = f"Prediction confidence too low: {pred_confidence:.2f} < {self.min_confidence}"
            decision['alternative_action'] = "Wait for higher confidence prediction"
            return decision
        
        # 7. Market Sentiment Check
        market_direction = sentiment_analysis.get('market_direction', 'NEUTRAL')
        overall_sentiment = sentiment_analysis.get('overall_sentiment', 0.0)
        
        if market_direction == 'NEUTRAL' and abs(overall_sentiment) < 0.1:
            decision['reason'] = "Market sentiment too neutral for profitable trading"
            decision['alternative_action'] = "Wait for clearer market direction"
            return decision
        
        # 8. Consecutive Loss Protection
        if self.session_stats['current_consecutive_losses'] >= 3:
            decision['reason'] = f"Too many consecutive losses: {self.session_stats['current_consecutive_losses']}"
            decision['alternative_action'] = "Pause trading to prevent further losses"
            return decision
        
        # 9. Model Ensemble Agreement Check
        ensemble_prediction = model_predictions.get('ensemble', {})
        ensemble_confidence = ensemble_prediction.get('confidence', 0.0)
        
        if ensemble_confidence < 0.7:
            decision['reason'] = f"Model ensemble confidence too low: {ensemble_confidence:.2f}"
            decision['alternative_action'] = "Wait for stronger model agreement"
            return decision
        
        # 10. Optimal Trading Window Check
        trading_window = sentiment_analysis.get('optimal_trading_window', {})
        if trading_window.get('status') == 'suboptimal':
            decision['reason'] = "Not in optimal trading window"
            decision['alternative_action'] = "Wait for optimal trading window"
            return decision
        
        # ALL CHECKS PASSED - APPROVE TRADE
        decision['execute_trade'] = True
        decision['reason'] = "All safety and profitability checks passed"
        
        # Calculate optimal stake
        decision['recommended_stake'] = self._calculate_optimal_stake(
            safety_analysis, sentiment_analysis, prediction, trade_request
        )
        
        # Calculate combined confidence
        decision['confidence'] = self._calculate_combined_confidence(
            safety_analysis, sentiment_analysis, prediction, ensemble_confidence
        )
        
        # Suggest contract optimization
        decision['optimized_contract'] = self._optimize_contract_selection(
            model_predictions, sentiment_analysis, trade_request
        )
        
        decision['alternative_action'] = "Execute trade with recommended parameters"
        
        logger.info(f"Trade APPROVED: Safety={safety_score:.1f}, Profit Prob={profit_prob:.2f}, Confidence={decision['confidence']:.2f}")
        
        return decision
    
    def _calculate_optimal_stake(self, safety_analysis: Dict, sentiment_analysis: Dict,
                               prediction: Dict, trade_request: Dict) -> float:
        """Calculate optimal stake based on all factors"""
        base_stake = trade_request.get('amount', 1.0)
        
        # Safety multiplier (higher safety = higher stake)
        safety_score = safety_analysis.get('safety_score', 50) / 100
        safety_multiplier = 0.5 + (safety_score * 1.5)  # 0.5x to 2.0x
        
        # Confidence multiplier
        confidence = prediction.get('confidence', 0.5)
        confidence_multiplier = 0.5 + (confidence * 1.5)  # 0.5x to 2.0x
        
        # Sentiment multiplier
        sentiment_strength = abs(sentiment_analysis.get('overall_sentiment', 0))
        sentiment_multiplier = 0.8 + (sentiment_strength * 0.4)  # 0.8x to 1.2x
        
        # Profit probability multiplier
        profit_prob = safety_analysis.get('profit_probability', 0.5)
        profit_multiplier = 0.6 + (profit_prob * 0.8)  # 0.6x to 1.4x
        
        # Calculate optimal stake
        optimal_stake = base_stake * safety_multiplier * confidence_multiplier * sentiment_multiplier * profit_multiplier
        
        # Apply risk management limits
        max_stake = self.risk_manager.max_stake
        optimal_stake = min(optimal_stake, max_stake)
        optimal_stake = max(optimal_stake, 0.5)  # Minimum stake
        
        return round(optimal_stake, 2)
    
    def _calculate_combined_confidence(self, safety_analysis: Dict, sentiment_analysis: Dict,
                                     prediction: Dict, ensemble_confidence: float) -> float:
        """Calculate combined confidence score"""
        safety_confidence = safety_analysis.get('safety_score', 0) / 100
        sentiment_confidence = abs(sentiment_analysis.get('overall_sentiment', 0))
        prediction_confidence = prediction.get('confidence', 0)
        
        # Weighted average
        combined_confidence = (
            safety_confidence * 0.3 +
            sentiment_confidence * 0.2 +
            prediction_confidence * 0.3 +
            ensemble_confidence * 0.2
        )
        
        return min(1.0, combined_confidence)
    
    def _optimize_contract_selection(self, model_predictions: Dict, sentiment_analysis: Dict,
                                   trade_request: Dict) -> Dict:
        """Optimize contract type and parameters"""
        current_contract = trade_request.get('contract_type', 'DIGITEVEN')
        
        # Get ensemble recommendation
        ensemble = model_predictions.get('ensemble', {})
        recommended_contract = ensemble.get('contract_type', current_contract)
        
        # Get sentiment-based recommendation
        trading_signals = self.sentiment_analyzer.get_trading_signals()
        signal_contracts = trading_signals.get('contracts', [])
        
        # Choose best contract based on confidence
        best_contract = current_contract
        best_confidence = 0.5
        
        # Check ensemble recommendation
        if ensemble.get('confidence', 0) > best_confidence:
            best_contract = recommended_contract
            best_confidence = ensemble.get('confidence', 0)
        
        # Check signal-based contracts
        for signal in signal_contracts:
            if signal.get('strength', 0) > best_confidence:
                best_contract = signal.get('type', current_contract)
                best_confidence = signal.get('strength', 0)
        
        return {
            'contract_type': best_contract,
            'confidence': best_confidence,
            'duration': ensemble.get('duration', 5),
            'reasoning': f"Selected based on {best_confidence:.2f} confidence"
        }
    
    def _update_session_stats(self, decision: Dict):
        """Update session statistics"""
        if decision.get('execute_trade', False):
            self.session_stats['trades_executed'] += 1
            self.session_stats['last_trade_time'] = datetime.now()
        else:
            self.session_stats['trades_prevented'] += 1
    
    def record_trade_outcome(self, outcome: str, pnl: float):
        """Record trade outcome for learning"""
        if outcome == 'win':
            self.session_stats['wins'] += 1
            self.session_stats['current_consecutive_losses'] = 0
            self.session_stats['total_profit'] += pnl
        elif outcome == 'loss':
            self.session_stats['losses'] += 1
            self.session_stats['current_consecutive_losses'] += 1
            self.session_stats['max_consecutive_losses'] = max(
                self.session_stats['max_consecutive_losses'],
                self.session_stats['current_consecutive_losses']
            )
            self.session_stats['total_profit'] += pnl
        
        # Auto-pause after too many losses
        if self.auto_pause_enabled and self.session_stats['current_consecutive_losses'] >= 5:
            self.pause_trading("Auto-paused after 5 consecutive losses")
    
    def pause_trading(self, reason: str = "Manual pause"):
        """Pause trading"""
        self.is_trading_enabled = False
        logger.warning(f"Trading paused: {reason}")
    
    def resume_trading(self, reason: str = "Manual resume"):
        """Resume trading"""
        self.is_trading_enabled = True
        logger.info(f"Trading resumed: {reason}")
    
    def get_trading_status(self) -> Dict:
        """Get current trading status and statistics"""
        total_trades = self.session_stats['wins'] + self.session_stats['losses']
        win_rate = (self.session_stats['wins'] / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'trading_enabled': self.is_trading_enabled,
            'auto_pause_enabled': self.auto_pause_enabled,
            'profit_protection_enabled': self.profit_protection_enabled,
            'session_stats': {
                **self.session_stats,
                'win_rate': win_rate,
                'total_trades': total_trades
            },
            'safety_thresholds': {
                'min_safety_score': self.min_safety_score,
                'min_profit_probability': self.min_profit_probability,
                'max_loss_probability': self.max_loss_probability,
                'min_confidence': self.min_confidence
            },
            'models_loaded': {
                'loss_prevention': self.loss_prevention_ai.is_trained,
                'multi_predictor': any(self.multi_predictor.is_trained.values())
            }
        }
    
    def update_safety_thresholds(self, thresholds: Dict):
        """Update safety thresholds"""
        if 'min_safety_score' in thresholds:
            self.min_safety_score = max(0, min(100, thresholds['min_safety_score']))
        
        if 'min_profit_probability' in thresholds:
            self.min_profit_probability = max(0, min(1, thresholds['min_profit_probability']))
        
        if 'max_loss_probability' in thresholds:
            self.max_loss_probability = max(0, min(1, thresholds['max_loss_probability']))
        
        if 'min_confidence' in thresholds:
            self.min_confidence = max(0, min(1, thresholds['min_confidence']))
        
        logger.info(f"Safety thresholds updated: {thresholds}")
    
    def _load_models(self):
        """Load pre-trained AI models"""
        try:
            self.loss_prevention_ai.load_models()
            self.multi_predictor.load_models()
            logger.info("AI models loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load AI models: {e}")
    
    def _safe_rejection(self, reason: str) -> Dict:
        """Safe rejection with default values"""
        return {
            'execute_trade': False,
            'reason': reason,
            'confidence': 0.0,
            'recommended_stake': 0.0,
            'alternative_action': 'Wait for better conditions',
            'safety_score': 0,
            'market_conditions': 'UNKNOWN',
            'risk_level': 'CRITICAL'
        }
    
    async def train_models_with_data(self, historical_data: List[Dict]) -> bool:
        """Train AI models with historical data"""
        try:
            # Train loss prevention AI
            loss_prevention_trained = self.loss_prevention_ai.train_models(historical_data)
            
            # Train multi-model predictor
            multi_model_trained = self.multi_predictor.train_models(historical_data)
            
            success = loss_prevention_trained and multi_model_trained
            
            if success:
                logger.info("All AI models trained successfully")
            else:
                logger.warning("Some AI models failed to train")
            
            return success
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return False