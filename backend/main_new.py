from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio
import json
import numpy
import websockets
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy.orm import Session

from models.database import create_tables, get_db, User, Tick
from api.routes import router as api_router
from services.contract_monitor import ContractMonitor
from services.notification_service import NotificationService
from services.market_data import MarketDataService
from strategies.auto_trader import AutoTrader
from services.deriv_trader import DerivTrader
from services.risk_manager import RiskManager
from ai.predictor import EnhancedAIPredictor
from ai.multi_model_predictor import MultiModelPredictor
from utils.auth import hash_password, verify_password, create_jwt_token, get_current_user
from utils.logger import setup_logger
from utils.json_encoder import json_dumps, convert_numpy_types
from utils.error_handler import error_handler
from utils.config import Config

logger = setup_logger(__name__)

app = FastAPI(title="Brightbot Trading API", version="2.0.0")

@app.middleware("http")
async def cors_handler(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
create_tables()

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
    def db_session_scope():
        db = next(get_db())
        try:
            yield db
        finally:
            db.close()

    try:
        # Create local trader instance to avoid conflicts
        local_trader = DerivTrader()
        
        # Connect to Deriv with API token
        from utils.config import Config
        api_token = getattr(Config, 'DERIV_API_TOKEN', None)
        app_id = getattr(Config, 'DERIV_APP_ID', '1089')  # Default fallback
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









@app.get("/api/trades/active")
async def get_active_trades():
    """Get active trades placed by the bot"""
    return {"trades": list(trade_manager.active_trades.values()), "count": len(trade_manager.active_trades)}

@app.get("/api/trading-mode")
async def get_trading_mode_status():
    """Get current trading mode"""
    from api.trading_mode import get_trading_mode
    return {"trading_mode": get_trading_mode()}

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
async def start_auto_trading(strategy_config: dict):
    asyncio.create_task(auto_trader.start_auto_trading(1, strategy_config))
    return {"success": True}

@app.post("/api/auto-trading/stop")
async def stop_auto_trading():
    auto_trader.stop_auto_trading()

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

if __name__ == "__main__":
    import uvicorn
    print("Starting server with live trading capabilities...")
    uvicorn.run("main_new:app", host="127.0.0.1", port=8001, reload=True)
