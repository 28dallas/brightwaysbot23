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
from ai.auto_trading_controller import AutoTradingController
from ai.loss_prevention_ai import LossPreventionAI
from ai.market_sentiment_analyzer import MarketSentimentAnalyzer
from strategies.auto_trader import AutoTrader
from utils.auth import get_current_user
from utils.config import Config
from utils.logger import setup_logger
logger = setup_logger(__name__)
router = APIRouter()

# Initialize services
deriv_trader = DerivTrader()
risk_manager = RiskManager()
ai_predictor = EnhancedAIPredictor()
trading_controller = AutoTradingController()
loss_prevention_ai = LossPreventionAI()
market_analyzer = MarketSentimentAnalyzer()
auto_trader = AutoTrader()

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

@router.post("/balance")
async def get_balance(balance_request: dict, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    import asyncio
    import os

    user = db.query(User).filter(User.id == current_user['user_id']).first()
    
    # Extract token and app_id from request
    api_token = balance_request.get('api_token', '').strip()
    app_id = balance_request.get('app_id', '1089').strip()
    account_type = balance_request.get('account_type', 'demo')

    logger.info(f"Balance API called with token provided: {bool(api_token)}, account_type: {account_type}, app_id: {app_id}")

    # If no token provided, return error asking for token
    if not api_token:
        return {
            "success": False,
            "error": "API token required",
            "message": "Please provide your Deriv API token to fetch balance",
            "balance": 0.0,
            "account_type": account_type
        }

    # Always try to fetch from Deriv API with provided token
    temp_trader = DerivTrader()
    try:
        # Connect with the provided token
        connected = await asyncio.wait_for(
            temp_trader.connect(api_token=api_token, app_id=app_id, is_demo=False),
            timeout=15
        )
        
        if connected and temp_trader.authorized:
            balance = await asyncio.wait_for(temp_trader.get_balance(), timeout=10)
            if balance is not None:
                await temp_trader.close()
                logger.info(f"Balance fetched successfully: {balance}")
                
                # Update user's stored token and balance if successful
                if user:
                    user.api_token = api_token
                    user.app_id = app_id
                    user.balance = balance
                    # Determine account type based on response
                    user.account_type = 'demo' if 'VRT' in str(temp_trader.ws) or account_type == 'demo' else 'live'
                    db.commit()
                
                return {
                    "success": True,
                    "balance": float(balance),
                    "account_type": user.account_type if user else account_type,
                    "message": "Balance retrieved successfully"
                }
        
        await temp_trader.close()
        return {
            "success": False,
            "error": "Authorization failed",
            "message": "Invalid API token or connection failed",
            "balance": 0.0,
            "account_type": account_type
        }
        
    except asyncio.TimeoutError:
        await temp_trader.close()
        return {
            "success": False,
            "error": "Connection timeout",
            "message": "Connection to Deriv timed out. Please try again.",
            "balance": 0.0,
            "account_type": account_type
        }
    except Exception as e:
        await temp_trader.close()
        logger.error(f"Balance fetch failed: {e}")
        return {
            "success": False,
            "error": "Connection error",
            "message": f"Failed to fetch balance: {str(e)}",
            "balance": 0.0,
            "account_type": account_type
        }

@router.get("/balance")
async def get_balance_prompt(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """GET endpoint that always prompts for API token"""
    return {
        "success": False,
        "error": "API token required",
        "message": "Please provide your Deriv API token to fetch balance. Use POST /api/balance with api_token in request body.",
        "balance": 0.0,
        "requires_token": True
    }

@router.post("/trade")
async def place_trade(trade_request: dict, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    import os
    api_token = os.getenv('DERIV_API_TOKEN')
    trading_mode = os.getenv('TRADING_MODE', 'demo')
    is_demo = trading_mode == 'demo'
    actual_stake = trade_request['amount']

    # For demo mode, don't use API token
    effective_api_token = None if is_demo else api_token

    try:
        connected = await deriv_trader.connect(effective_api_token, is_demo=is_demo)
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
                user_id=current_user['user_id'],
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
        logger.error(f"Trade failed: {e}")
        raise HTTPException(status_code=500, detail=f"Trade failed: {str(e)}")

@router.get("/ai/prediction")
async def get_ai_prediction():
    prediction = ai_predictor.predict_next_digit()
    return prediction

@router.options("/trades/active")
async def options_active_trades():
    return {}

@router.get("/trades/active")
async def get_active_trades(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        trades = db.query(Trade).filter(
            Trade.user_id == current_user['user_id'],
            Trade.result.in_(['pending', 'win', 'lose'])
        ).order_by(Trade.timestamp.desc()).limit(10).all()
        
        return {
            "success": True,
            "trades": [{
                "id": t.id,
                "timestamp": t.timestamp.isoformat(),
                "stake": t.stake,
                "contract_type": t.contract_type,
                "result": t.result,
                "is_demo": t.is_demo
            } for t in trades],
            "count": len(trades)
        }
    except Exception as e:
        logger.error(f"Error in get_active_trades: {e}")
        return {
            "success": True,
            "trades": [],
            "count": 0
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
            logger.info(f"Testing API token with app_id: {effective_app_id}")
            connected = await asyncio.wait_for(
                temp_trader.connect(api_token=api_token, app_id=effective_app_id, is_demo=False),
                timeout=15
            )
            if connected and temp_trader.authorized:
                # Get live balance to verify token works
                balance = await asyncio.wait_for(temp_trader.get_balance(), timeout=10)
                await temp_trader.close()

                if balance is not None:
                    user.api_token = api_token
                    user.app_id = app_id if app_id else user.app_id
                    user.account_type = 'live'
                    user.balance = balance
                    db.commit()

                    # Update .env file for persistence
                    from api.env_manager import update_env_file
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
            raise HTTPException(status_code=400, detail="Invalid API token. Please check your token and try again.")

        except asyncio.TimeoutError:
            await temp_trader.close()
            raise HTTPException(status_code=408, detail="Connection to Deriv timed out. Please try again.")
        except Exception as e:
            await temp_trader.close()
            logger.error(f"API token validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to validate API token: {str(e)}")
    else:
        # Remove API token (switch to demo)
        user.api_token = None
        user.app_id = None
        user.account_type = 'demo'
        user.balance = 10000.0
        db.commit()

        # Update .env file for persistence
        from api.env_manager import update_env_file
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

@router.post("/account/toggle")
async def toggle_account_type(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user['user_id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.account_type == 'demo':
        # Switch to live - need API token
        if not user.api_token:
            raise HTTPException(status_code=400, detail="API token required to switch to live account")

        # Test the API token
        temp_trader = DerivTrader()
        try:
            effective_app_id = user.app_id or "1089"
            connected = await temp_trader.connect(api_token=user.api_token, app_id=effective_app_id, is_demo=False)
            if connected and temp_trader.authorized:
                balance = await temp_trader.get_balance()
                await temp_trader.close()

                if balance is not None:
                    user.account_type = 'live'
                    user.balance = balance
                    db.commit()

                    # Update .env file for persistence
                    from utils.env_manager import update_env_file
                    update_env_file({
                        'TRADING_MODE': 'live'
                    })

                    return {
                        "account_type": "live",
                        "balance": balance,
                        "message": "Switched to live account"
                    }

            await temp_trader.close()
            raise HTTPException(status_code=400, detail="Failed to connect with API token")

        except Exception as e:
            await temp_trader.close()
            logger.error(f"Live account switch failed: {e}")
            raise HTTPException(status_code=400, detail="Failed to switch to live account")
    else:
        # Switch to demo
        user.account_type = 'demo'
        user.balance = 10000.0
        db.commit()

        # Update .env file for persistence
        from utils.env_manager import update_env_file
        update_env_file({
            'TRADING_MODE': 'demo'
        })

        return {
            "account_type": "demo",
            "balance": 10000.0,
            "message": "Switched to demo account"
        }

@router.post("/trading-mode")
async def toggle_trading_mode(mode_data: dict, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    from api.trading_mode import set_trading_mode

    new_mode = mode_data.get('mode', 'demo')
    if new_mode not in ['demo', 'live']:
        raise HTTPException(status_code=400, detail="Mode must be 'demo' or 'live'")

    user = db.query(User).filter(User.id == current_user['user_id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if new_mode == 'live':
        # For live mode, user must have API token
        if not user.api_token:
            raise HTTPException(status_code=400, detail="API token required for live mode. Please set up your API token first.")

        # Test connection before switching
        temp_trader = DerivTrader()
        try:
            app_id = user.app_id or '1089'
            connected = await asyncio.wait_for(
                temp_trader.connect(api_token=user.api_token, app_id=app_id, is_demo=False),
                timeout=15
            )
            if not (connected and temp_trader.authorized):
                raise HTTPException(status_code=400, detail="Failed to authorize with your API token.")
        except asyncio.TimeoutError:
            raise HTTPException(status_code=408, detail="Connection to Deriv timed out.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")
        finally:
            await temp_trader.close()

    # Update user's trading mode
    user.account_type = new_mode
    if new_mode == 'demo':
        user.balance = 10000.0  # Reset demo balance
    db.commit()

    # Update global trading mode
    if set_trading_mode(new_mode):
        logger.info(f"Successfully switched trading mode to '{new_mode}' for user {user.id}")
        return {"trading_mode": new_mode, "message": f"Switched to {new_mode} mode"}
    else:
        raise HTTPException(status_code=500, detail="Failed to set trading mode in environment.")

@router.get("/trading-mode")
async def get_trading_mode_status(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user['user_id']).first()
    if user:
        return {"trading_mode": user.account_type or 'demo'}
    return {"trading_mode": 'demo'}

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