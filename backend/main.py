from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
import os
import websockets
from dotenv import load_dotenv
import numpy as np
from typing import Optional
import uuid
from services.deriv_trader import DerivTrader
from api import auth

load_dotenv()

app = FastAPI()

# Include auth routes
app.include_router(auth.router, prefix="", tags=["auth"])

# Pydantic models
class TradeRequest(BaseModel):
    contract_type: str  # 'DIGITDIFF', 'DIGITEVEN', 'DIGITODD', 'CALL', 'PUT'
    symbol: str
    amount: float
    duration: int
    duration_unit: str  # 't' for ticks, 's' for seconds
    barrier: Optional[str] = None
    prediction: Optional[int] = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
def init_db():
    conn = sqlite3.connect('trading.db')
    conn.execute('DROP TABLE IF EXISTS trades')
    conn.execute('DROP TABLE IF EXISTS users')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT,
            full_name TEXT,
            account_type TEXT DEFAULT 'demo',
            balance REAL DEFAULT 1221.95,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            timestamp DATETIME,
            stake REAL,
            prediction INTEGER,
            result TEXT,
            pnl REAL,
            contract_id TEXT,
            contract_type TEXT,
            is_demo BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# AI Prediction Engine
class AIPredictor:
    def __init__(self):
        self.price_history = []
        
    def add_price(self, price: float):
        self.price_history.append(price)
        if len(self.price_history) > 100:
            self.price_history.pop(0)
    
    def predict_next_digit(self) -> dict:
        if len(self.price_history) < 10:
            return {'prediction': 5, 'confidence': 0.65, 'signal': 'neutral'}
        
        recent_prices = np.array(self.price_history[-10:])
        price_changes = np.diff(recent_prices)
        
        trend = np.mean(price_changes)
        volatility = np.std(price_changes)
        
        last_digits = [int(str(p).split('.')[-1][-1]) for p in self.price_history[-20:] if '.' in str(p)]
        if last_digits:
            digit_freq = np.bincount(last_digits, minlength=10)
            least_common = np.argmin(digit_freq)
            
            prediction = least_common
            confidence = min(0.9, 0.5 + abs(trend) * 10 + volatility * 5)
            signal = 'buy' if trend > 0 else 'sell' if trend < 0 else 'neutral'
            
            return {
                'prediction': prediction,
                'confidence': confidence,
                'signal': signal,
                'trend': trend,
                'volatility': volatility
            }
        
        return {'prediction': 5, 'confidence': 0.65, 'signal': 'neutral'}

ai_predictor = AIPredictor()

# Deriv Trading Class
class DerivTrader:
    def __init__(self):
        self.ws = None
        self.is_connected = False
        
    async def connect(self):
        try:
            self.ws = await websockets.connect('wss://ws.binaryws.com/websockets/v3?app_id=1089')
            self.is_connected = True
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    async def buy_contract(self, contract_request: TradeRequest):
        if not self.is_connected:
            return {"error": "Not connected to Deriv"}
        
        try:
            buy_request = {
                "buy": 1,
                "price": contract_request.amount,
                "parameters": {
                    "contract_type": contract_request.contract_type,
                    "symbol": contract_request.symbol,
                    "duration": contract_request.duration,
                    "duration_unit": contract_request.duration_unit
                }
            }
            
            if contract_request.barrier:
                buy_request["parameters"]["barrier"] = contract_request.barrier
            
            await self.ws.send(json.dumps(buy_request))
            response = await self.ws.recv()
            return json.loads(response)
        except Exception as e:
            return {"error": str(e)}

trader = DerivTrader()

# Create default user
def ensure_default_user():
    conn = sqlite3.connect('trading.db')
    cursor = conn.execute("SELECT id FROM users WHERE id = 1")
    if not cursor.fetchone():
        conn.execute(
            "INSERT INTO users (id, email, full_name, account_type, balance) VALUES (1, 'demo@brightbot.com', 'Demo User', 'demo', 1221.95)"
        )
        conn.commit()
    conn.close()

ensure_default_user()

# API Routes
@app.post("/api/trade")
async def place_trade(trade: TradeRequest):
    if not trader.is_connected:
        await trader.connect()
    
    result = await trader.buy_contract(trade)
    
    if "buy" in result:
        conn = sqlite3.connect('trading.db')
        conn.execute(
            "INSERT INTO trades (user_id, timestamp, stake, contract_type, contract_id, is_demo) VALUES (?, ?, ?, ?, ?, ?)",
            (1, datetime.now(), trade.amount, trade.contract_type, result.get("buy", {}).get("contract_id"), True)
        )
        conn.commit()
        conn.close()
    
    return result

@app.get("/api/balance")
async def get_balance():
    import logging
    logger = logging.getLogger("uvicorn.error")
    api_token = os.getenv('DERIV_API_TOKEN')

    logger.info(f"Fetching balance with API token: {'set' if api_token else 'not set'}")

    trader = None
    conn = None
    
    try:
        if api_token:
            # Try to get real balance from Deriv
            trader = DerivTrader()
            
            # Try live account first with timeout
            try:
                logger.info("Connecting to Deriv live account")
                connected = await asyncio.wait_for(
                    trader.connect(api_token=api_token, is_demo=False), 
                    timeout=10
                )
                
                if connected and trader.authorized:
                    balance = await asyncio.wait_for(trader.get_balance(), timeout=10)
                    if balance is not None and isinstance(balance, (int, float)):
                        # Update DB balance safely
                        conn = sqlite3.connect('trading.db')
                        conn.execute(
                            "UPDATE users SET balance = ?, account_type = 'live' WHERE id = 1", 
                            (float(balance),)
                        )
                        conn.commit()
                        conn.close()
                        conn = None
                        
                        await trader.close()
                        return {"balance": float(balance), "currency": "USD", "account_type": "live"}
                        
            except asyncio.TimeoutError:
                logger.warning("Live account connection timeout")
            except Exception as e:
                logger.error(f"Live account error: {e}")
            finally:
                if trader:
                    await trader.close()

            # Try demo account
            try:
                logger.info("Connecting to Deriv demo account")
                trader = DerivTrader()
                connected = await asyncio.wait_for(
                    trader.connect(api_token=api_token, is_demo=True), 
                    timeout=10
                )
                
                if connected and trader.authorized:
                    balance = await asyncio.wait_for(trader.get_balance(), timeout=10)
                    if balance is not None and isinstance(balance, (int, float)):
                        # Update DB balance safely
                        conn = sqlite3.connect('trading.db')
                        conn.execute(
                            "UPDATE users SET balance = ?, account_type = 'demo' WHERE id = 1", 
                            (float(balance),)
                        )
                        conn.commit()
                        conn.close()
                        conn = None
                        
                        await trader.close()
                        return {"balance": float(balance), "currency": "USD", "account_type": "demo"}
                        
            except asyncio.TimeoutError:
                logger.warning("Demo account connection timeout")
            except Exception as e:
                logger.error(f"Demo account error: {e}")
            finally:
                if trader:
                    await trader.close()

    except Exception as e:
        logger.error(f"Unexpected error in balance fetch: {e}")
    finally:
        # Ensure cleanup
        if trader:
            await trader.close()
        if conn:
            conn.close()

    # Fallback to DB balance with error handling
    try:
        conn = sqlite3.connect('trading.db')
        cursor = conn.execute("SELECT balance, account_type FROM users WHERE id = 1")
        row = cursor.fetchone()
        balance = float(row[0]) if row and row[0] is not None else 10000.0
        account_type = row[1] if row and row[1] else "demo"
        conn.close()
        
        logger.info(f"Returning fallback balance: {balance} ({account_type})")
        return {"balance": balance, "currency": "USD", "account_type": account_type}
        
    except Exception as e:
        logger.error(f"Database fallback error: {e}")
        return {"balance": 10000.0, "currency": "USD", "account_type": "demo"}

@app.get("/api/ai/prediction")
async def get_ai_prediction():
    prediction = ai_predictor.predict_next_digit()
    return prediction

@app.get("/api/trades/active")
async def get_active_trades():
    conn = sqlite3.connect('trading.db')
    cursor = conn.execute(
        "SELECT * FROM trades WHERE user_id = 1 AND result IS NULL ORDER BY timestamp DESC LIMIT 10"
    )
    trades = cursor.fetchall()
    conn.close()
    
    return {"trades": trades}

@app.get("/api/analytics/advanced")
async def get_analytics():
    conn = sqlite3.connect('trading.db')
    cursor = conn.execute(
        "SELECT stake, pnl FROM trades WHERE user_id = 1 AND pnl IS NOT NULL"
    )
    trades = cursor.fetchall()
    conn.close()
    
    if not trades:
        return {"win_rate": 0, "profit_factor": 0, "total_trades": 0}
    
    wins = len([t for t in trades if t[1] > 0])
    total = len(trades)
    win_rate = wins / total * 100
    
    total_profit = sum([t[1] for t in trades if t[1] > 0])
    total_loss = abs(sum([t[1] for t in trades if t[1] < 0]))
    profit_factor = total_profit / total_loss if total_loss > 0 else 0
    
    return {
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_trades": total,
        "total_profit": total_profit,
        "total_loss": total_loss
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)