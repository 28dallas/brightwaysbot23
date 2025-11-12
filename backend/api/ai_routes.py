from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio

from models.database import get_db, User, Trade
from ai.auto_trading_controller import AutoTradingController
from ai.loss_prevention_ai import LossPreventionAI
from ai.market_sentiment_analyzer import MarketSentimentAnalyzer
from strategies.auto_trader import AutoTrader
from utils.auth import get_current_user
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

# Initialize AI services
trading_controller = AutoTradingController()
loss_prevention_ai = LossPreventionAI()
market_analyzer = MarketSentimentAnalyzer()
auto_trader = AutoTrader()

@router.get("/market-safety")
async def get_market_safety_analysis(current_user: dict = Depends(get_current_user)):
    """Get current market safety analysis"""
    try:
        # Get current market data (simplified)
        market_data = {
            'price': 100.0,  # Would get from real market data
            'volume': 1.0,
            'timestamp': datetime.now()
        }
        
        safety_analysis = loss_prevention_ai.analyze_market_safety(market_data)
        return {
            "success": True,
            "analysis": safety_analysis
        }
    except Exception as e:
        logger.error(f"Market safety analysis failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "analysis": loss_prevention_ai._safe_fallback()
        }

@router.get("/market-sentiment")
async def get_market_sentiment(current_user: dict = Depends(get_current_user)):
    """Get current market sentiment analysis"""
    try:
        # Get current price (simplified)
        current_price = 100.0  # Would get from real market data
        
        sentiment_analysis = market_analyzer.analyze_market_sentiment(current_price)
        trading_signals = market_analyzer.get_trading_signals()
        
        return {
            "success": True,
            "sentiment": sentiment_analysis,
            "signals": trading_signals
        }
    except Exception as e:
        logger.error(f"Market sentiment analysis failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "sentiment": market_analyzer._neutral_sentiment(),
            "signals": {"signal": "NO_SIGNAL", "strength": 0, "contracts": []}
        }

@router.get("/trading-status")
async def get_ai_trading_status(current_user: dict = Depends(get_current_user)):
    """Get AI trading controller status"""
    try:
        status = trading_controller.get_trading_status()
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        logger.error(f"Failed to get trading status: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/trading-control")
async def control_ai_trading(control_data: dict, current_user: dict = Depends(get_current_user)):
    """Control AI trading (pause/resume/update settings)"""
    try:
        action = control_data.get('action')
        
        if action == 'pause':
            reason = control_data.get('reason', 'Manual pause')
            trading_controller.pause_trading(reason)
            return {"success": True, "message": f"Trading paused: {reason}"}
        
        elif action == 'resume':
            reason = control_data.get('reason', 'Manual resume')
            trading_controller.resume_trading(reason)
            return {"success": True, "message": f"Trading resumed: {reason}"}
        
        elif action == 'update_thresholds':
            thresholds = control_data.get('thresholds', {})
            trading_controller.update_safety_thresholds(thresholds)
            return {"success": True, "message": "Safety thresholds updated"}
        
        else:
            return {"success": False, "error": "Invalid action. Use 'pause', 'resume', or 'update_thresholds'"}
    
    except Exception as e:
        logger.error(f"AI trading control failed: {e}")
        return {"success": False, "error": str(e)}

@router.post("/should-trade")
async def check_should_trade(trade_data: dict, current_user: dict = Depends(get_current_user)):
    """Check if AI approves a specific trade"""
    try:
        market_data = trade_data.get('market_data', {'price': 100.0, 'volume': 1.0})
        prediction = trade_data.get('prediction', {'prediction': 5, 'confidence': 0.5})
        trade_request = trade_data.get('trade_request', {
            'contract_type': 'DIGITEVEN',
            'amount': 1.0,
            'symbol': 'R_100',
            'duration': 5,
            'duration_unit': 't'
        })
        
        decision = await trading_controller.should_execute_trade(
            market_data, prediction, trade_request
        )
        
        return {
            "success": True,
            "decision": decision
        }
    
    except Exception as e:
        logger.error(f"Trade decision analysis failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "decision": trading_controller._safe_rejection("Analysis failed")
        }

@router.post("/train-models")
async def train_ai_models(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Train AI models with historical data"""
    try:
        # Get historical trade data
        trades = db.query(Trade).filter(
            Trade.user_id == current_user['user_id']
        ).order_by(Trade.timestamp.asc()).all()
        
        if len(trades) < 50:
            return {
                "success": False,
                "error": "Insufficient historical data. Need at least 50 trades to train models.",
                "trades_available": len(trades)
            }
        
        # Convert trades to training data format
        historical_data = []
        for trade in trades:
            historical_data.append({
                'price': float(trade.stake),  # Using stake as price proxy
                'volume': 1.0,
                'timestamp': trade.timestamp,
                'outcome': 'win' if trade.result == 'win' else 'loss' if trade.result == 'lose' else 'unknown'
            })
        
        # Train models
        success = await trading_controller.train_models_with_data(historical_data)
        
        if success:
            return {
                "success": True,
                "message": "AI models trained successfully",
                "training_data_points": len(historical_data)
            }
        else:
            return {
                "success": False,
                "error": "Model training failed",
                "training_data_points": len(historical_data)
            }
    
    except Exception as e:
        logger.error(f"Model training failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/auto-trading/start")
async def start_auto_trading_with_ai(config: dict, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Start AI-powered auto trading"""
    try:
        user = db.query(User).filter(User.id == current_user['user_id']).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Enhanced strategy config with AI safety features
        strategy_config = {
            'type': config.get('type', 'ai_enhanced'),
            'contract_type': config.get('contract_type', 'DIGITEVEN'),
            'symbol': config.get('symbol', 'R_100'),
            'duration': config.get('duration', 5),
            'duration_unit': config.get('duration_unit', 't'),
            'min_confidence': config.get('min_confidence', 0.8),  # Higher default
            'check_interval': config.get('check_interval', 30),
            'trade_interval': config.get('trade_interval', 60),
            'fixed_stake_amount': config.get('stake', 1.0)
        }
        
        # Use API token for live trading
        api_token = user.api_token if user.account_type == 'live' else None
        
        # Start auto trading in background
        asyncio.create_task(
            auto_trader.start_auto_trading(
                user_id=user.id,
                strategy_config=strategy_config,
                api_token=api_token
            )
        )
        
        return {
            "success": True,
            "message": "AI-powered auto trading started",
            "config": strategy_config,
            "account_type": user.account_type
        }
    
    except Exception as e:
        logger.error(f"Failed to start auto trading: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/auto-trading/stop")
async def stop_auto_trading_ai(current_user: dict = Depends(get_current_user)):
    """Stop AI-powered auto trading"""
    try:
        auto_trader.stop_auto_trading()
        return {
            "success": True,
            "message": "Auto trading stopped"
        }
    except Exception as e:
        logger.error(f"Failed to stop auto trading: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/auto-trading/status")
async def get_auto_trading_status(current_user: dict = Depends(get_current_user)):
    """Get auto trading status"""
    try:
        ai_status = trading_controller.get_trading_status()
        
        return {
            "success": True,
            "is_running": auto_trader.is_running,
            "ai_status": ai_status
        }
    except Exception as e:
        logger.error(f"Failed to get auto trading status: {e}")
        return {
            "success": False,
            "error": str(e),
            "is_running": False
        }

@router.get("/enhanced-prediction")
async def get_enhanced_ai_prediction(current_user: dict = Depends(get_current_user)):
    """Get AI prediction with enhanced analysis"""
    try:
        from ai.predictor import EnhancedAIPredictor
        ai_predictor = EnhancedAIPredictor()
        
        # Get basic prediction
        prediction = ai_predictor.predict_next_digit()
        
        # Get market safety analysis
        market_data = {'price': 100.0, 'volume': 1.0}  # Would get real data
        safety_analysis = loss_prevention_ai.analyze_market_safety(market_data)
        
        # Get market sentiment
        sentiment_analysis = market_analyzer.analyze_market_sentiment(100.0)
        
        # Enhanced prediction with safety checks
        enhanced_prediction = {
            **prediction,
            'safety_score': safety_analysis.get('safety_score', 0),
            'safe_to_trade': safety_analysis.get('safe_to_trade', False),
            'market_sentiment': sentiment_analysis.get('overall_sentiment', 0),
            'market_direction': sentiment_analysis.get('market_direction', 'NEUTRAL'),
            'risk_level': safety_analysis.get('risk_level', 'HIGH'),
            'recommendation': safety_analysis.get('recommendation', 'WAIT')
        }
        
        return enhanced_prediction
    
    except Exception as e:
        logger.error(f"Enhanced AI prediction failed: {e}")
        from ai.predictor import EnhancedAIPredictor
        ai_predictor = EnhancedAIPredictor()
        return ai_predictor.predict_next_digit()  # Fallback to basic prediction