from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json
import os
import asyncio
from datetime import datetime, timedelta

from models.database import get_db, User, Trade, Strategy
from services.deriv_trader import DerivTrader
from services.risk_manager import RiskManager
from ai.predictor import EnhancedAIPredictor
from utils.auth import get_current_user
from utils.config import Config
from utils.logger import setup_logger
logger = setup_logger(__name__)
router = APIRouter()

# Initialize services
deriv_trader = DerivTrader()
risk_manager = RiskManager()
ai_predictor = EnhancedAIPredictor()

@router.get("/user")
async def get_user(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user['user_id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "api_token_set": user.api_token is not None,
        "app_id": user.app_id,
        "balance": user.balance,
        "account_type": user.account_type
    }

@router.get("/balance")
async def get_balance(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db), api_token: str = None, account_type: str = 'demo'):
    import asyncio
    import os

    user = db.query(User).filter(User.id == current_user['user_id']).first()
    effective_token = api_token or (user.api_token if user else None) or os.getenv('DERIV_API_TOKEN')
    effective_app_id = (user.app_id if user else None) or "1089"  # Default fallback

    logger.info(f"Balance API called with effective_token: {effective_token}, account_type: {account_type}, app_id: {effective_app_id}")

    if effective_token:
        temp_trader = DerivTrader()
        try:
            connected = await asyncio.wait_for(
                temp_trader.connect(api_token=effective_token, app_id=effective_app_id, is_demo=(account_type == 'demo')),
                timeout=15
            )
            if connected and temp_trader.authorized:
                balance = await asyncio.wait_for(temp_trader.get_balance(), timeout=10)
                if balance is not None:
                    await temp_trader.close()
                    logger.info(f"Balance fetched successfully: {balance}")
                    return {"balance": float(balance), "account_type": account_type}
            await temp_trader.close()
        except Exception as e:
            await temp_trader.close()
            logger.error(f"Balance fetch failed: {e}")

    # Fallback to mock balance if no token or connection failed
    if account_type == 'live':
        return {"balance": 5000.0, "account_type": "live"}
    else:
        return {"balance": 10000.0, "account_type": "demo"}

@router.post("/trade")
async def place_trade(trade_request: dict, db: Session = Depends(get_db)):
    import os
    api_token = os.getenv('DERIV_API_TOKEN')
    trading_mode = os.getenv('TRADING_MODE', 'demo')
    is_demo = trading_mode == 'demo'
    actual_stake = trade_request['amount']
    
    try:
        connected = await deriv_trader.connect(api_token, is_demo=is_demo)
        if connected:
            trade_result = await deriv_trader.buy_contract({
                "contract_type": trade_request["contract_type"],
                "symbol": trade_request["symbol"],
                "amount": actual_stake,
                "duration": trade_request["duration"],
                "duration_unit": trade_request["duration_unit"],
                "barrier": trade_request.get("barrier"),
                "currency": "USD"
            })
            
            await deriv_trader.close()
            
            if "error" in trade_result:
                raise HTTPException(status_code=400, detail=trade_result["error"]["message"])
            
            contract_id = trade_result.get("buy", {}).get("contract_id", "unknown")
            
            # Record trade
            trade = Trade(
                user_id=1,
                stake=actual_stake,
                prediction=trade_request.get('prediction', 0),
                result='pending',
                pnl=0,
                contract_id=contract_id,
                contract_type=trade_request["contract_type"],
                is_demo=is_demo,
                confidence=trade_request.get('confidence', 0.5)
            )
            
            db.add(trade)
            db.commit()
            
            return {
                "success": True,
                "contract_id": contract_id,
                "result": "pending",
                "pnl": 0,
                "actual_stake": actual_stake
            }
    except Exception as e:
        logger.error(f"Demo trade failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trade failed: {str(e)}")

@router.get("/ai/prediction")
async def get_ai_prediction():
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
    
    ticks = db.query(Tick).order_by(Tick.timestamp.desc()).limit(100).all()
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

@router.post("/account/api-token")
async def update_api_token(token_data: dict, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user['user_id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    api_token = token_data.get('api_token', '').strip()
    app_id = token_data.get('app_id', '').strip()

    if api_token:
        # Test the API token
        temp_trader = DerivTrader()
        try:
            effective_app_id = app_id or "1089"  # Default fallback
            connected = await temp_trader.connect(api_token=api_token, app_id=effective_app_id, is_demo=False)
            if connected and temp_trader.authorized:
                # Get live balance to verify token works
                balance = await temp_trader.get_balance()
                await temp_trader.close()

                if balance is not None:
                    user.api_token = api_token
                    user.app_id = app_id if app_id else user.app_id
                    user.account_type = 'live'
                    user.balance = balance
                    db.commit()

                    # Update .env file for persistence
                    from utils.env_manager import update_env_file
                    updates = {
                        'DERIV_API_TOKEN': api_token,
                        'TRADING_MODE': 'live'
                    }
                    if app_id:
                        updates['DERIV_APP_ID'] = app_id
                    update_env_file(updates)

                    return {
                        "success": True,
                        "message": "API token updated successfully",
                        "balance": balance,
                        "account_type": "live"
                    }

            await temp_trader.close()
            raise HTTPException(status_code=400, detail="Invalid API token or App ID")

        except Exception as e:
            await temp_trader.close()
            logger.error(f"API token validation failed: {e}")
            raise HTTPException(status_code=400, detail="Failed to validate API token")
    else:
        # Remove API token (switch to demo)
        user.api_token = None
        user.app_id = None
        user.account_type = 'demo'
        user.balance = 10000.0
        db.commit()

        # Update .env file for persistence
        from utils.env_manager import update_env_file
        update_env_file({
            'DERIV_API_TOKEN': '',
            'TRADING_MODE': 'demo'
        })

        return {
            "success": True,
            "message": "Switched to demo account",
            "balance": 10000.0,
            "account_type": "demo"
        }

@router.post("/trading-mode")
async def toggle_trading_mode(mode_data: dict):
    from api.trading_mode import set_trading_mode

    new_mode = mode_data.get('mode', 'demo')
    if new_mode not in ['demo', 'live']:
        raise HTTPException(status_code=400, detail="Mode must be 'demo' or 'live'")

    if new_mode == 'live':
        api_token = os.getenv('DERIV_API_TOKEN')
        if not api_token:
            raise HTTPException(status_code=400, detail="DERIV_API_TOKEN is required for live mode.")

        # Test connection before switching
        temp_trader = DerivTrader()
        try:
            app_id = os.getenv('DERIV_APP_ID', '1089')  # Default fallback
            connected = await asyncio.wait_for(
                temp_trader.connect(api_token=api_token, app_id=app_id, is_demo=False),
                timeout=15
            )
            if not (connected and temp_trader.authorized):
                raise HTTPException(status_code=400, detail="Failed to authorize with the provided API token.")
        except asyncio.TimeoutError:
            raise HTTPException(status_code=408, detail="Connection to Deriv timed out.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")
        finally:
            await temp_trader.close()

    if set_trading_mode(new_mode):
        logger.info(f"Successfully switched trading mode to '{new_mode}'")
        return {"trading_mode": new_mode, "message": f"Switched to {new_mode} mode"}
    else:
        raise HTTPException(status_code=500, detail="Failed to set trading mode in environment.")

@router.get("/trading-mode")
async def get_trading_mode_status():
    from api.trading_mode import get_trading_mode
    return {"trading_mode": get_trading_mode()}

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