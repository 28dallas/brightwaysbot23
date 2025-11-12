from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio
import json
import numpy
import websockets
import os
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy.orm import Session

from models.database import create_tables, get_db, User, Tick, Trade, SessionLocal
from api.routes import router as api_router
from api.ai_routes import router as ai_router
from services.contract_monitor import ContractMonitor
from services.notification_service import NotificationService
from services.market_data import MarketDataService
from strategies.auto_trader import AutoTrader
from services.deriv_trader import DerivTrader
from services.risk_manager import RiskManager
from ai.predictor import EnhancedAIPredictor
from ai.multi_model_predictor import MultiModelPredictor
from utils.auth import hash_password, verify_password, create_jwt_token, get_current_user, verify_jwt_token
from fastapi import Depends
from utils.logger import setup_logger
from utils.json_encoder import json_dumps, convert_numpy_types
from utils.error_handler import error_handler
from utils.config import Config

logger = setup_logger(__name__)

app = FastAPI(title="Brightbot Trading API", version="2.0.0")

@app.middleware("http")
async def cors_handler(request, call_next):
    if request.method == "OPTIONS":
        response = JSONResponse(content={})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
create_tables()

def ensure_default_user():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            hashed_password = hash_password("demo")
            user = User(
                id=1,
                email="demo@brightbot.com",
                hashed_password=hashed_password,
                full_name="Demo User",
                balance=10000.0,
                account_type='demo'
            )
            db.add(user)
            db.commit()
    finally:
        db.close()

ensure_default_user()

# Initialize services
deriv_trader = DerivTrader()
risk_manager = RiskManager()
ai_predictor = EnhancedAIPredictor()
ai_predictor.load_model()
multi_predictor = MultiModelPredictor()
multi_predictor.load_models()
contract_monitor = ContractMonitor()
notification_service = NotificationService()
market_data_service = MarketDataService()
auto_trader = AutoTrader()

# Start notification service (will be started in startup event)

class TradeManager:
    def __init__(self):
        self.active_trades = {}
        self.last_trade_time = 0
        self.MIN_TRADE_INTERVAL = 30  # Minimum seconds between trades

    def can_trade(self):
        current_time = asyncio.get_event_loop().time()
        return (current_time - self.last_trade_time) >= self.MIN_TRADE_INTERVAL and len(self.active_trades) < 3

trade_manager = TradeManager()

MAX_STAKE = 5.0  # Maximum stake per trade

# Pydantic models
class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class ApiTokenUpdate(BaseModel):
    api_token: str

# Include API routes
app.include_router(api_router, prefix="/api")
app.include_router(ai_router, prefix="/api/ai")

@app.post("/api/register")
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        balance=10000.0,
        account_type='demo'
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create token
    token = create_jwt_token(new_user.id, new_user.email)
    
    return {
        "token": token,
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "balance": new_user.balance,
            "account_type": new_user.account_type
        }
    }

@app.post("/api/login")
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    # Find user
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = create_jwt_token(user.id, user.email)
    
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "balance": user.balance,
            "account_type": user.account_type
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")

    local_trader = None

    @contextmanager
    def db_session_scope(db_session=None):
        if db_session:
            yield db_session
            return
        
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    try:
        # Authenticate user from token in query param
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008, reason="Token not provided")
            return

        try:
            user_data = verify_jwt_token(token)
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            await websocket.close(code=1008, reason="Invalid token")
            return

        # Get user from database to ensure they exist
        with db_session_scope() as db:
            user = db.query(User).filter(User.id == user_data['user_id']).first()
            if not user:
                await websocket.close(code=1008, reason="User not found")
                return

            api_token = user.api_token if user else os.getenv('DERIV_API_TOKEN')
            app_id = user.app_id if user and user.app_id else os.getenv('DERIV_APP_ID', '1089')

        local_trader = DerivTrader()
        connected = await local_trader.connect(api_token=api_token, app_id=app_id, is_demo=not api_token)
        
        if not connected:
            logger.error("Failed to connect to Deriv")
            await websocket.send_text(json.dumps({"error": "Failed to connect to Deriv"}))
            await _send_simulated_data(websocket)
            return
        
        # Subscribe to ticks with error handling
        if local_trader.ws and (not hasattr(local_trader.ws, 'state') or local_trader.ws.state == websockets.protocol.State.OPEN):
            await local_trader.ws.send(json.dumps({"ticks": "R_100"}))
        
        async for message in local_trader.ws:
            try:
                # Check if websocket is still open
                if websocket.client_state.name != 'CONNECTED':
                    logger.info("Client WebSocket disconnected")
                    break
                    
                tick_data = json.loads(message)
                
                if "tick" in tick_data:
                    price = float(tick_data["tick"]["quote"])
                    last_digit = int(str(price).split('.')[-1][-1])

                    # Add to AI predictors with error handling
                    try:
                        ai_predictor.add_price(price)
                        multi_predictor.add_price(price)
                        prediction = ai_predictor.predict_next_digit()
                    except Exception as e:
                        logger.error(f"AI prediction error: {e}")
                        prediction = {"prediction": 5, "confidence": 0.5}

                    # Check trading mode and place real trades if live mode
                    from api.trading_mode import get_trading_mode
                    trading_mode = get_trading_mode()
                    trade_result = None

                    if trading_mode == 'live' and local_trader.authorized:
                        try:
                            current_time = asyncio.get_event_loop().time()

                            if trade_manager.can_trade():
                                # Simple trading strategy: bet on predicted digit with confidence > 0.7
                                confidence = prediction.get('confidence', 0)
                                if confidence > 0.7:
                                    predicted_digit = prediction.get('prediction', 5)

                                    # Set a fixed stake of $5
                                    stake = 5.0

                                    # Place trade on the predicted digit
                                    contract_request = {
                                        "contract_type": "DIGITMATCH",
                                        "symbol": "R_100",
                                        "amount": stake,
                                        "duration": 1,
                                        "duration_unit": "t",
                                        "barrier": str(predicted_digit)
                                    }

                                    logger.info(f"Placing live trade: {contract_request} (confidence: {confidence:.2f})")
                                    trade_result = await local_trader.buy_contract(contract_request)

                                    if "buy" in trade_result:
                                        contract_id = trade_result['buy']['contract_id']
                                        trade_manager.active_trades[contract_id] = {
                                            'contract_id': contract_id,
                                            'stake': stake,
                                            'predicted_digit': predicted_digit,
                                            'timestamp': datetime.now().isoformat(),
                                            'confidence': confidence
                                        }
                                        trade_manager.last_trade_time = current_time
                                        logger.info(f"Trade placed successfully: {contract_id}")
                                    elif "error" in trade_result:
                                        logger.error(f"Trade failed: {trade_result['error']['message']}")
                        except Exception as e:
                            logger.error(f"Live trading error: {e}")

                    with db_session_scope() as db:
                        tick = Tick(price=price, last_digit=last_digit)
                        db.add(tick)
                        db.commit()

                    data = {
                        "price": price,
                        "last_digit": last_digit,
                        "timestamp": datetime.now().isoformat(),
                        "ai_prediction": prediction,
                        "trading_mode": trading_mode
                    }

                    if trade_result:
                        data["trade_result"] = trade_result

                    data = convert_numpy_types(data)

                    try:
                        await websocket.send_text(json_dumps(data))
                    except Exception as e:
                        error_msg = str(e)
                        if any(msg in error_msg.lower() for msg in ["close", "disconnect", "connection"]):
                            logger.info("WebSocket connection closed by client")
                            break
                        else:
                            logger.error(f"WebSocket send error: {e}")
                            continue
                            
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.error(f"WebSocket processing error: {e}")
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        # Fallback to simulated data
        await _send_simulated_data(websocket)
    finally:
        if local_trader:
            await local_trader.close()

async def _send_simulated_data(websocket: WebSocket):
    """Fallback simulated data when Deriv connection fails"""
    import random
    logger.info("Using simulated data fallback")

    while True:
        try:
            # Check if websocket is still connected
            if websocket.client_state.name != 'CONNECTED':
                logger.info("Client disconnected from simulated data")
                break
                
            price = round(1000 + random.uniform(-50, 50), 5)
            last_digit = int(str(price).split('.')[-1][-1])

            try:
                ai_predictor.add_price(price)
                prediction = ai_predictor.predict_next_digit()
            except Exception as e:
                logger.error(f"AI prediction error in simulation: {e}")
                prediction = {"prediction": 5, "confidence": 0.5}

            data = {
                "price": price,
                "last_digit": last_digit,
                "timestamp": datetime.now().isoformat(),
                "ai_prediction": prediction,
                "simulated": True
            }
            data = convert_numpy_types(data)

            await websocket.send_text(json_dumps(data))
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Simulated data error: {e}")
            break











@app.get("/api/trading-mode")
async def get_trading_mode_status():
    """Get current trading mode"""
    from api.trading_mode import get_trading_mode
    return {"trading_mode": get_trading_mode()}

@app.get("/api/current-user-debug")
async def debug_current_user(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Debug endpoint to check current user and API token status"""
    user = db.query(User).filter(User.id == current_user['user_id']).first()
    if not user:
        return {"error": "User not found"}
    
    return {
        "user_id": user.id,
        "email": user.email,
        "has_api_token": bool(user.api_token),
        "account_type": user.account_type,
        "balance": user.balance,
        "api_token_length": len(user.api_token) if user.api_token else 0
    }

@app.get("/api/test-token")
async def test_api_token():
    """Test API token connection"""
    import os
    import websockets
    
    api_token = os.getenv('DERIV_API_TOKEN')
    if not api_token:
        return {"success": False, "error": "No API token found"}
    
    try:
        ws = await websockets.connect("wss://ws.binaryws.com/websockets/v3?app_id=1089")
        
        await ws.send(json.dumps({"authorize": api_token}))
        response = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(response)
        
        if "authorize" in data:
            await ws.send(json.dumps({"balance": 1}))
            balance_response = await asyncio.wait_for(ws.recv(), timeout=10)
            balance_data = json.loads(balance_response)
            
            await ws.close()
            
            if "balance" in balance_data:
                balance = balance_data["balance"]["balance"]
                return {
                    "success": True,
                    "balance": float(balance),
                    "currency": balance_data["balance"].get("currency", "USD"),
                    "account_type": balance_data["balance"].get("account_type", "unknown")
                }
        
        await ws.close()
        return {"success": False, "error": "Authorization failed", "response": data}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/symbols")
async def get_symbols():
    symbols = await market_data_service.get_active_symbols()
    return {"symbols": symbols}

@app.get("/api/market/status")
async def get_market_status():
    status = await market_data_service.get_market_status()
    return status

@app.post("/api/contract/sell/{contract_id}")
async def sell_contract(contract_id: str):
    result = await contract_monitor.sell_contract(contract_id)
    return result

@app.post("/api/auto-trading/start")
async def start_auto_trading(request_data: dict, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == current_user['user_id']).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        is_demo = user.account_type == 'demo'
        
        logger.info(f"Starting auto trading for user {user.id} in {user.account_type} mode")
        
        # Extract strategy config from request data
        strategy_config = {
            "type": "fixed_stake",
            "fixed_stake_amount": 1.0,
            "min_confidence": request_data.get('min_confidence', 0.6),
            "contract_type": request_data.get('contract_type', 'DIGITEVEN'),
            "symbol": request_data.get('symbol', 'R_100'),
            "duration": request_data.get('duration', 5),
            "duration_unit": request_data.get('duration_unit', 't'),
            "check_interval": request_data.get('check_interval', 30),
            "trade_interval": request_data.get('trade_interval', 30)
        }
        
        logger.info(f"Auto trading strategy: {strategy_config}")
        
        if is_demo:
            # For demo mode, start demo auto trading
            if auto_trader.is_running:
                return {"success": False, "message": "Auto trading is already running"}
            
            auto_trader.is_running = True
            asyncio.create_task(start_demo_auto_trading(user.id))
            return {"success": True, "message": f"Auto trading started successfully in {user.account_type} mode"}
        else:
            # For live mode, require API token
            if not user.api_token:
                raise HTTPException(status_code=400, detail="API token required for live trading. Please set up your API token first.")
            
            # Test connection first
            test_trader = DerivTrader()
            try:
                connected = await test_trader.connect(api_token=user.api_token, is_demo=False)
                if not connected or not test_trader.authorized:
                    await test_trader.close()
                    raise HTTPException(status_code=400, detail="Failed to connect with API token. Please check your token.")
                await test_trader.close()
            except Exception as e:
                logger.error(f"Auto trading connection test failed: {e}")
                raise HTTPException(status_code=400, detail=f"Connection test failed: {str(e)}")
            
            # Start live auto trading using the auto_trader
            if auto_trader.is_running:
                return {"success": False, "message": "Auto trading is already running"}
            
            asyncio.create_task(auto_trader.start_auto_trading(user.id, strategy_config, user.api_token))
            return {"success": True, "message": f"Auto trading started successfully in {user.account_type} mode"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auto trading start error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start auto trading: {str(e)}")

@app.post("/api/auto-trading/stop")
async def stop_auto_trading():
    try:
        logger.info("Stopping auto trading")
        auto_trader.stop_auto_trading()
        return {"success": True, "message": "Auto trading stopped successfully"}
    except Exception as e:
        logger.error(f"Auto trading stop error: {e}")
        return {"success": False, "message": f"Error stopping auto trading: {str(e)}"}

@app.get("/api/auto-trading/status")
async def get_auto_trading_status():
    try:
        is_running = auto_trader.is_running
        return {
            "is_running": is_running,
            "message": "Auto trading is running" if is_running else "Auto trading is stopped"
        }
    except Exception as e:
        logger.error(f"Auto trading status error: {e}")
        return {
            "is_running": False,
            "message": f"Error checking status: {str(e)}"
        }

@app.post("/api/demo-trade")
async def place_demo_trade(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Place a real trade on Deriv"""
    import random
    
    try:
        user = db.query(User).filter(User.id == current_user['user_id']).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        is_demo = user.account_type == 'demo'
        
        if is_demo:
            # Place real demo trade on Deriv demo account
            trader = DerivTrader()
            try:
                connected = await trader.connect(api_token=None, is_demo=True)
                if not connected:
                    raise HTTPException(status_code=400, detail="Failed to connect to Deriv demo")
                
                # Place a DIGITEVEN trade on demo
                trade_request = {
                    "contract_type": "DIGITEVEN",
                    "symbol": "R_100",
                    "amount": 1.0,
                    "duration": 5,
                    "duration_unit": "t"
                }
                
                result = await trader.buy_contract(trade_request)
                
                if "buy" in result:
                    contract_id = result['buy']['contract_id']
                    stake = 1.0
                    
                    # Wait for trade to complete (simulate)
                    await asyncio.sleep(2)
                    
                    # Check contract status
                    contract_info = await trader.get_contract_info(contract_id)
                    
                    if contract_info and "proposal_open_contract" in contract_info:
                        contract = contract_info["proposal_open_contract"]
                        payout = float(contract.get("payout", 0))
                        
                        if payout > 0:
                            # Win
                            pnl = payout - stake
                            user.balance += pnl
                            result_text = "WIN"
                        else:
                            # Loss
                            pnl = -stake
                            user.balance -= stake
                            result_text = "LOSS"
                    else:
                        # Assume loss if can't get status
                        pnl = -stake
                        user.balance -= stake
                        result_text = "LOSS"
                    
                    db.commit()
                    await trader.close()
                    
                    return {
                        "success": True,
                        "contract_id": contract_id,
                        "result": result_text.lower(),
                        "pnl": pnl,
                        "new_balance": user.balance,
                        "message": f"Demo trade: {result_text} - P&L: ${pnl:.2f} - Balance: ${user.balance:.2f}"
                    }
                else:
                    await trader.close()
                    error_msg = result.get('error', {}).get('message', 'Unknown error')
                    raise HTTPException(status_code=400, detail=f"Demo trade failed: {error_msg}")
                    
            except Exception as e:
                await trader.close()
                raise HTTPException(status_code=500, detail=f"Demo trading error: {str(e)}")
        else:
            # Place real trade on Deriv for live mode
            if not user.api_token:
                raise HTTPException(status_code=400, detail="API token required for live trading")
            
            trader = DerivTrader()
            try:
                connected = await trader.connect(api_token=user.api_token, is_demo=False)
                if not connected or not trader.authorized:
                    raise HTTPException(status_code=400, detail="Failed to connect to Deriv")
                
                # Place a DIGITEVEN trade
                trade_request = {
                    "contract_type": "DIGITEVEN",
                    "symbol": "R_100",
                    "amount": 1.0,
                    "duration": 5,
                    "duration_unit": "t"
                }
                
                result = await trader.buy_contract(trade_request)
                
                if "buy" in result:
                    contract_id = result['buy']['contract_id']
                    
                    # Get updated balance
                    new_balance = await trader.get_balance()
                    if new_balance:
                        user.balance = new_balance
                        db.commit()
                    
                    await trader.close()
                    
                    return {
                        "success": True,
                        "contract_id": contract_id,
                        "new_balance": new_balance or user.balance,
                        "message": f"Live trade placed: {contract_id} - Balance: ${new_balance or user.balance:.2f}"
                    }
                else:
                    await trader.close()
                    error_msg = result.get('error', {}).get('message', 'Unknown error')
                    raise HTTPException(status_code=400, detail=f"Trade failed: {error_msg}")
                    
            except Exception as e:
                await trader.close()
                raise HTTPException(status_code=500, detail=f"Trading error: {str(e)}")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade error: {e}")
        raise HTTPException(status_code=500, detail="Trade failed")

@app.get("/api/ai/multi-predictions")
async def get_multi_predictions():
    """Get predictions from all AI models"""
    try:

        predictions = multi_predictor.predict_all_models()

        predictions = convert_numpy_types(predictions)
        return {"success": True, "predictions": predictions}
    except Exception as e:
        logger.error(f"Multi-prediction error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/ai/add-price")
async def add_price_data(price_data: dict):
    """Add price data to AI models"""
    try:
        price = price_data.get('price', 0)
        multi_predictor.add_price(price)
        return {"success": True}
    except Exception as e:
        logger.error(f"Add price error: {e}")
        return {"success": False, "error": str(e)}

async def monitor_trades():
    """Background task to monitor active trades and update their status"""
    while True:
        try:
            if trade_manager.active_trades:
                # Create a temporary trader instance to check trade status
                temp_trader = DerivTrader()
                api_token = os.getenv('DERIV_API_TOKEN')

                if api_token:
                    connected = await temp_trader.connect(api_token=api_token, is_demo=False)
                    if connected and temp_trader.authorized and trade_manager.active_trades:
                        # Check each active trade
                        completed_trades = []
                        for contract_id, trade_info in list(trade_manager.active_trades.items()):
                            try:
                                # Get contract details
                                contract_info = await temp_trader.get_contract_info(contract_id)
                                if contract_info and "contract" in contract_info:
                                    contract = contract_info["contract"]
                                    status = contract.get("status")

                                    if status in ["won", "lost", "sold"]:
                                        # Trade is completed
                                        payout = float(contract.get("payout", 0))
                                        stake = trade_info['stake']
                                        profit_loss = payout - stake

                                        trade_info.update({
                                            'status': status,
                                            'payout': payout,
                                            'profit_loss': profit_loss,
                                            'completed_at': datetime.now().isoformat()
                                        })

                                        logger.info(f"Trade {contract_id} completed: {status}, P/L: {profit_loss:.2f}")

                                        # Move to completed trades (we'll keep them for now)
                                        completed_trades.append(contract_id)

                            except Exception as e:
                                logger.error(f"Error checking trade {contract_id}: {e}")

                        # Remove completed trades from active list
                        for contract_id in completed_trades:
                            del trade_manager.active_trades[contract_id]

                    await temp_trader.close()

        except Exception as e:
            logger.error(f"Trade monitoring error: {e}")

        # Check every 10 seconds
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    """Start background tasks on startup"""
    asyncio.create_task(monitor_trades())
    asyncio.create_task(notification_service.start_notification_worker())

@app.post("/api/update-balance")
async def update_balance(amount_data: dict, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == current_user['user_id']).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        amount = amount_data.get('amount', -1.0)
        user.balance += amount
        db.commit()
        
        return {
            "success": True,
            "new_balance": user.balance,
            "change": amount
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Balance update failed")

async def start_demo_auto_trading(user_id: int):
    """Demo auto trading with simulated trades"""
    logger.info(f"Starting DEMO auto trading for user {user_id}")
    
    import random
    demo_balance = 10000.0
    
    try:
        for i in range(5):
            if not auto_trader.is_running:
                break
                
            # Simulate trade
            stake = 1.0
            win = random.random() > 0.5
            
            if win:
                payout = stake * 1.8
                demo_balance += (payout - stake)
                result = "WIN"
            else:
                demo_balance -= stake
                result = "LOSS"
            
            logger.info(f"DEMO trade {i+1}/5: {result} - Balance: ${demo_balance:.2f}")
            
            # Update user balance in database
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.balance = demo_balance
                    db.commit()
            finally:
                db.close()
            
            await asyncio.sleep(10)
            
    finally:
        auto_trader.is_running = False
        logger.info("Demo auto trading completed")

async def start_simple_auto_trading(user_id: int, api_token: str):
    """Auto trading - tries real trades, falls back to simulation"""
    logger.info(f"Starting auto trading for user {user_id}")
    
    trader = DerivTrader()
    use_real_trading = False
    
    # Force real trading connection
    if not api_token:
        logger.error("No API token provided - cannot trade")
        auto_trader.is_running = False
        return
    
    try:
        logger.info(f"Connecting to Deriv with token: {api_token[:10]}...")
        connected = await trader.connect(api_token=api_token, app_id="1089", is_demo=False)
        
        if connected and trader.authorized:
            use_real_trading = True
            logger.info("SUCCESS: Connected to REAL Deriv account for trading")
        else:
            logger.error("FAILED: Could not authorize with Deriv")
            auto_trader.is_running = False
            return
    except Exception as e:
        logger.error(f"Connection error: {e}")
        auto_trader.is_running = False
        return
    
    import random
    
    try:
        for i in range(5):
            if not auto_trader.is_running:
                break
                
            try:
                # Place REAL trade on Deriv
                trade_request = {
                    "contract_type": "DIGITEVEN",
                    "symbol": "R_100",
                    "amount": 1.0,
                    "duration": 5,
                    "duration_unit": "t"
                }
                
                logger.info(f"Placing REAL trade {i+1}/5 on Deriv")
                result = await trader.buy_contract(trade_request)
                
                if "buy" in result:
                    contract_id = result['buy']['contract_id']
                    logger.info(f"SUCCESS: REAL trade placed on Deriv - Contract ID: {contract_id}")
                    
                    # Get updated balance from Deriv
                    await asyncio.sleep(3)
                    real_balance = await trader.get_balance()
                    
                    if real_balance is not None:
                        db = SessionLocal()
                        try:
                            user = db.query(User).filter(User.id == user_id).first()
                            if user:
                                old_balance = user.balance
                                user.balance = real_balance
                                db.commit()
                                logger.info(f"Balance updated: ${old_balance:.2f} -> ${real_balance:.2f}")
                        finally:
                            db.close()
                else:
                    logger.error(f"TRADE FAILED: {result}")
                
                await asyncio.sleep(15)
                
            except Exception as e:
                logger.error(f"Trade error: {e}")
                
    finally:
        await trader.close()
        auto_trader.is_running = False
        logger.info("Live auto trading completed")

if __name__ == "__main__":
    import uvicorn
    print("Starting server with live trading capabilities...")
    uvicorn.run("main_new:app", host="127.0.0.1", port=8001, reload=True)
