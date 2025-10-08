from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json
from datetime import datetime, timedelta

from models.database import get_db, User, Trade, Strategy
from services.deriv_trader import DerivTrader
from services.risk_manager import RiskManager
from ai.predictor import EnhancedAIPredictor
from utils.auth import get_current_user
from utils.logger import setup_logger
logger = setup_logger(__name__)
router = APIRouter()

# Initialize services
deriv_trader = DerivTrader()
risk_manager = RiskManager()
ai_predictor = EnhancedAIPredictor()

@router.get("/balance")
async def get_balance(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == current_user['user_id']).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Ensure user has a balance (set default if None or 0)
        if user.balance is None or user.balance == 0:
            user.balance = 10000.0 if user.account_type == 'demo' else 1000.0
            db.commit()
            logger.info(f"Set default balance for user {user.email}: {user.balance}")
        
        # For live accounts, fetch real balance
        if user.account_type == 'live' and user.api_token:
            try:
                connected = await deriv_trader.connect(user.api_token, is_demo=False)
                if connected:
                    real_balance = await deriv_trader.get_balance()
                    await deriv_trader.close()
                    
                    if real_balance is not None:
                        user.balance = real_balance
                        db.commit()
                        return {"balance": real_balance, "account_type": user.account_type}
            except Exception as e:
                logger.error(f"Live balance fetch failed: {e}")
        
        balance = user.balance if user.balance is not None else 0.0
        return {"balance": balance, "account_type": user.account_type or 'demo'}
        
    except Exception as e:
        logger.error(f"Balance endpoint error: {e}")
        return {"balance": 0.0, "account_type": "demo"}

@router.post("/trade")
async def place_trade(trade_request: dict, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user['user_id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Risk management checks
    recent_trades = db.query(Trade).filter(
        Trade.user_id == user.id,
        Trade.timestamp >= datetime.now() - timedelta(days=1)
    ).all()
    
    daily_pnl = sum(t.pnl or 0 for t in recent_trades)
    
    if not risk_manager.check_daily_risk_limit(daily_pnl, user.balance):
        raise HTTPException(status_code=400, detail="Daily risk limit exceeded")
    
    if risk_manager.should_stop_trading([{"pnl": t.pnl} for t in recent_trades[-20:]]):
        raise HTTPException(status_code=400, detail="Risk management: Trading stopped")
    
    # Calculate optimal position size
    confidence = trade_request.get('confidence', 0.5)
    optimal_stake = risk_manager.calculate_position_size(user.balance, confidence)
    actual_stake = min(trade_request['amount'], optimal_stake)
    
    if user.balance < actual_stake:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Execute trade
    is_demo = user.account_type == 'demo'
    
    if is_demo:
        # Demo trading simulation
        import random
        result = 'win' if random.random() > 0.5 else 'lose'
        pnl = actual_stake * 0.8 if result == 'win' else -actual_stake
        contract_id = f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        user.balance += pnl
    else:
        # Real trading
        if not user.api_token:
            raise HTTPException(status_code=400, detail="API token required")
        
        connected = await deriv_trader.connect(user.api_token, is_demo=False)
        if not connected:
            raise HTTPException(status_code=500, detail="Failed to connect to Deriv")
        
        trade_result = await deriv_trader.buy_contract({
            "contract_type": trade_request["contract_type"],
            "symbol": trade_request["symbol"],
            "amount": actual_stake,
            "duration": trade_request["duration"],
            "duration_unit": trade_request["duration_unit"],
            "barrier": trade_request.get("barrier")
        })
        
        await deriv_trader.close()
        
        if "error" in trade_result:
            raise HTTPException(status_code=400, detail=trade_result["error"]["message"])
        
        contract_id = trade_result.get("buy", {}).get("contract_id", "unknown")
        result = 'pending'
        pnl = 0
    
    # Record trade
    trade = Trade(
        user_id=user.id,
        stake=actual_stake,
        prediction=trade_request.get('prediction', 0),
        result=result,
        pnl=pnl,
        contract_id=contract_id,
        contract_type=trade_request["contract_type"],
        is_demo=is_demo,
        confidence=confidence
    )
    
    db.add(trade)
    db.commit()
    
    return {
        "success": True,
        "contract_id": contract_id,
        "result": result,
        "pnl": pnl,
        "optimal_stake": optimal_stake,
        "actual_stake": actual_stake
    }

@router.get("/ai/prediction")
async def get_ai_prediction(current_user: dict = Depends(get_current_user)):
    prediction = ai_predictor.predict_next_digit()
    return prediction

@router.get("/trades/active")
async def get_active_trades(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    trades = db.query(Trade).filter(
        Trade.user_id == current_user['user_id'],
        Trade.result.in_(['pending', 'win', 'lose'])
    ).order_by(Trade.timestamp.desc()).limit(10).all()
    
    return {
        "trades": [{
            "id": t.id,
            "timestamp": t.timestamp.isoformat(),
            "stake": t.stake,
            "contract_type": t.contract_type,
            "result": t.result,
            "is_demo": t.is_demo
        } for t in trades]
    }

@router.get("/history")
async def get_history(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    from models.database import Tick
    
    # Get recent ticks
    ticks = db.query(Tick).order_by(Tick.timestamp.desc()).limit(100).all()
    
    # Get recent trades
    trades = db.query(Trade).filter(
        Trade.user_id == current_user['user_id']
    ).order_by(Trade.timestamp.desc()).limit(50).all()
    
    return {
        "ticks": [{
            "id": t.id,
            "timestamp": t.timestamp.isoformat(),
            "price": t.price,
            "last_digit": t.last_digit
        } for t in ticks],
        "trades": [{
            "id": t.id,
            "timestamp": t.timestamp.isoformat(),
            "stake": t.stake,
            "prediction": t.prediction,
            "result": t.result,
            "pnl": t.pnl
        } for t in trades]
    }

@router.get("/analytics/advanced")
async def get_advanced_analytics(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    trades = db.query(Trade).filter(
        Trade.user_id == current_user['user_id']
    ).order_by(Trade.timestamp.desc()).limit(100).all()
    
    if not trades:
        return {"total_trades": 0, "win_rate": 0, "profit_factor": 0, "max_drawdown": 0}
    
    pnls = [t.pnl or 0 for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    
    win_rate = len(wins) / len(pnls) * 100 if pnls else 0
    profit_factor = sum(wins) / abs(sum(losses)) if losses else float('inf')
    
    # Calculate Sharpe ratio (simplified)
    returns = pnls
    sharpe_ratio = (sum(returns) / len(returns)) / (sum([(r - sum(returns)/len(returns))**2 for r in returns]) / len(returns))**0.5 if len(returns) > 1 else 0
    
    return {
        "total_trades": len(trades),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "total_pnl": round(sum(pnls), 2),
        "avg_win": round(sum(wins) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0
    }