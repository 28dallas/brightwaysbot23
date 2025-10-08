from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
from datetime import datetime
from sqlalchemy.orm import Session

from models.database import create_tables, get_db, User, Tick
from api.routes import router as api_router
from services.contract_monitor import ContractMonitor
from services.notification_service import NotificationService
from services.market_data import MarketDataService
from strategies.auto_trader import AutoTrader
from services.deriv_trader import DerivTrader
from ai.predictor import EnhancedAIPredictor
from ai.multi_model_predictor import MultiModelPredictor
from utils.auth import hash_password, verify_password, create_jwt_token, get_current_user
from utils.logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(title="Brightbot Trading API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
create_tables()

# Initialize services
deriv_trader = DerivTrader()
ai_predictor = EnhancedAIPredictor()
ai_predictor.load_model()
multi_predictor = MultiModelPredictor()
multi_predictor.load_models()
contract_monitor = ContractMonitor()
notification_service = NotificationService()
market_data_service = MarketDataService()
auto_trader = AutoTrader()

# Pydantic models
class ApiTokenUpdate(BaseModel):
    api_token: str

# Include API routes
app.include_router(api_router, prefix="/api")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        # Connect to Deriv with API token
        from utils.config import Config
        api_token = Config.DERIV_API_TOKEN
        connected = await deriv_trader.connect(api_token=api_token, is_demo=not api_token)
        if not connected:
            logger.error("Failed to connect to Deriv")
            await websocket.send_text(json.dumps({"error": "Failed to connect to Deriv"}))
            return
        
        # Subscribe to ticks
        await deriv_trader.ws.send(json.dumps({"ticks": "R_100"}))
        
        async for message in deriv_trader.ws:
            try:
                tick_data = json.loads(message)
                
                if "tick" in tick_data:
                    price = float(tick_data["tick"]["quote"])
                    last_digit = int(str(price).split('.')[-1][-1])
                    
                    # Add to AI predictors
                    ai_predictor.add_price(price)
                    multi_predictor.add_price(price)
                    prediction = ai_predictor.predict_next_digit()
                    
                    # Store tick data
                    db = next(get_db())
                    try:
                        tick = Tick(price=price, last_digit=last_digit)
                        db.add(tick)
                        db.commit()
                    except Exception as e:
                        logger.error(f"Database error: {e}")
                        db.rollback()
                    finally:
                        db.close()
                    
                    data = {
                        "price": price,
                        "last_digit": last_digit,
                        "timestamp": datetime.now().isoformat(),
                        "ai_prediction": prediction
                    }
                    
                    await websocket.send_text(json.dumps(data))
                    
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.error(f"WebSocket processing error: {e}")
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        # Fallback to simulated data
        await _send_simulated_data(websocket)
    finally:
        await deriv_trader.close()

async def _send_simulated_data(websocket: WebSocket):
    """Fallback simulated data when Deriv connection fails"""
    import random
    logger.info("Using simulated data fallback")
    
    while True:
        try:
            price = 1000 + random.uniform(-50, 50)
            last_digit = int(str(price).split('.')[-1][-1])
            
            ai_predictor.add_price(price)
            prediction = ai_predictor.predict_next_digit()
            
            data = {
                "price": round(price, 5),
                "last_digit": last_digit,
                "timestamp": datetime.now().isoformat(),
                "ai_prediction": prediction,
                "simulated": True
            }
            
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Simulated data error: {e}")
            break





@app.get("/api/balance")
async def get_balance():
    try:
        from utils.config import Config
        
        if Config.DERIV_API_TOKEN:
            # Create new connection for live balance check
            temp_trader = DerivTrader()
            connected = await temp_trader.connect(api_token=Config.DERIV_API_TOKEN, is_demo=False)
            
            if connected and temp_trader.authorized:
                balance = await temp_trader.get_balance()
                await temp_trader.close()
                
                if balance is not None:
                    logger.info(f"Live balance fetched: {balance}")
                    return {
                        "balance": balance,
                        "account_type": "live",
                        "ticks": [],
                        "trades": []
                    }
            
            await temp_trader.close()
        
        # Fallback to demo
        logger.info("Using demo balance")
        return {"balance": 10000, "account_type": "demo", "ticks": [], "trades": []}
        
    except Exception as e:
        logger.error(f"Balance fetch error: {e}")
        return {"balance": 10000, "account_type": "demo", "ticks": [], "trades": []}

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
    return {"success": True}

@app.get("/api/ai/multi-predictions")
async def get_multi_predictions():
    """Get predictions from all AI models"""
    try:
        predictions = multi_predictor.predict_all_models()
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_new:app", host="127.0.0.1", port=8001, reload=True)