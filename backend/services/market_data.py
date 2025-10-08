import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from utils.logger import setup_logger
from services.deriv_trader import DerivTrader

logger = setup_logger(__name__)

class MarketDataService:
    def __init__(self):
        self.trader = DerivTrader()
        self.price_cache = {}
        self.candle_cache = {}
        
    async def get_active_symbols(self) -> List[Dict]:
        """Get list of active trading symbols"""
        try:
            await self.trader.connect(is_demo=True)
            
            request = {"active_symbols": "brief"}
            await self.trader.ws.send(json.dumps(request))
            
            response = await self.trader.ws.recv()
            data = json.loads(response)
            
            await self.trader.close()
            
            if "active_symbols" in data:
                return data["active_symbols"]
                
        except Exception as e:
            logger.error(f"Active symbols error: {e}")
            
        return []
    
    async def get_candles(self, symbol: str, granularity: int = 60, count: int = 100) -> List[Dict]:
        """Get historical candle data"""
        try:
            await self.trader.connect(is_demo=True)
            
            # Calculate start time
            end_time = int(datetime.now().timestamp())
            start_time = end_time - (count * granularity)
            
            request = {
                "ticks_history": symbol,
                "start": start_time,
                "end": end_time,
                "style": "candles",
                "granularity": granularity,
                "count": count
            }
            
            await self.trader.ws.send(json.dumps(request))
            response = await self.trader.ws.recv()
            data = json.loads(response)
            
            await self.trader.close()
            
            if "candles" in data:
                candles = []
                for candle in data["candles"]:
                    candles.append({
                        "timestamp": candle["epoch"],
                        "open": float(candle["open"]),
                        "high": float(candle["high"]),
                        "low": float(candle["low"]),
                        "close": float(candle["close"])
                    })
                return candles
                
        except Exception as e:
            logger.error(f"Candles error: {e}")
            
        return []
    
    async def get_tick_history(self, symbol: str, count: int = 1000) -> List[Dict]:
        """Get historical tick data"""
        try:
            await self.trader.connect(is_demo=True)
            
            end_time = int(datetime.now().timestamp())
            start_time = end_time - (count * 2)  # Approximate 2 seconds per tick
            
            request = {
                "ticks_history": symbol,
                "start": start_time,
                "end": end_time,
                "count": count
            }
            
            await self.trader.ws.send(json.dumps(request))
            response = await self.trader.ws.recv()
            data = json.loads(response)
            
            await self.trader.close()
            
            if "history" in data:
                ticks = []
                prices = data["history"]["prices"]
                times = data["history"]["times"]
                
                for i, price in enumerate(prices):
                    ticks.append({
                        "timestamp": times[i],
                        "price": float(price),
                        "last_digit": int(str(price).split('.')[-1][-1]) if '.' in str(price) else 0
                    })
                    
                return ticks
                
        except Exception as e:
            logger.error(f"Tick history error: {e}")
            
        return []
    
    async def get_market_status(self) -> Dict:
        """Get current market status"""
        try:
            await self.trader.connect(is_demo=True)
            
            request = {"website_status": 1}
            await self.trader.ws.send(json.dumps(request))
            
            response = await self.trader.ws.recv()
            data = json.loads(response)
            
            await self.trader.close()
            
            if "website_status" in data:
                return {
                    "market_open": data["website_status"]["site_status"] == "up",
                    "server_time": data["website_status"]["server_time"],
                    "supported_languages": data["website_status"]["supported_languages"]
                }
                
        except Exception as e:
            logger.error(f"Market status error: {e}")
            
        return {"market_open": False}
    
    async def calculate_volatility(self, symbol: str, period: int = 20) -> float:
        """Calculate price volatility"""
        try:
            ticks = await self.get_tick_history(symbol, period)
            if len(ticks) < 2:
                return 0.0
                
            prices = [tick["price"] for tick in ticks]
            returns = []
            
            for i in range(1, len(prices)):
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
            
            if not returns:
                return 0.0
                
            # Calculate standard deviation
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            volatility = variance ** 0.5
            
            return volatility
            
        except Exception as e:
            logger.error(f"Volatility calculation error: {e}")
            return 0.0