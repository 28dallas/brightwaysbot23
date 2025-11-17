import MetaTrader5 as mt5
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MT5Integration:
    def __init__(self):
        self.connected = False
        self.account_info = None
        
    async def connect(self, login: int, password: str, server: str):
        """Connect to MT5 terminal"""
        try:
            if not mt5.initialize():
                logger.error("MT5 initialization failed")
                return False
                
            if not mt5.login(login, password=password, server=server):
                logger.error(f"MT5 login failed: {mt5.last_error()}")
                return False
                
            self.connected = True
            self.account_info = mt5.account_info()
            logger.info(f"Connected to MT5: {self.account_info.name}")
            return True
            
        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            return False
    
    async def get_positions(self) -> List[Dict]:
        """Get open positions from MT5"""
        if not self.connected:
            return []
            
        positions = mt5.positions_get()
        return [
            {
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "type": "buy" if pos.type == 0 else "sell",
                "volume": pos.volume,
                "price_open": pos.price_open,
                "profit": pos.profit,
                "time": datetime.fromtimestamp(pos.time)
            }
            for pos in positions or []
        ]
    
    async def get_signals(self) -> List[Dict]:
        """Monitor MT5 for new signals/trades"""
        positions = await self.get_positions()
        
        # Convert MT5 positions to Deriv signals
        signals = []
        for pos in positions:
            signal = {
                "symbol": self._convert_symbol(pos["symbol"]),
                "action": pos["type"],
                "price": pos["price_open"],
                "volume": pos["volume"],
                "source": "MT5",
                "timestamp": pos["time"].isoformat()
            }
            signals.append(signal)
            
        return signals
    
    def _convert_symbol(self, mt5_symbol: str) -> str:
        """Convert MT5 symbol to Deriv symbol"""
        symbol_map = {
            "EURUSD": "frxEURUSD",
            "GBPUSD": "frxGBPUSD", 
            "USDJPY": "frxUSDJPY",
            "AUDUSD": "frxAUDUSD",
            "USDCAD": "frxUSDCAD"
        }
        return symbol_map.get(mt5_symbol, mt5_symbol)
    
    async def monitor_trades(self, callback):
        """Monitor MT5 for new trades and execute callback"""
        last_positions = set()
        
        while self.connected:
            try:
                current_positions = await self.get_positions()
                current_tickets = {pos["ticket"] for pos in current_positions}
                
                # Check for new positions
                new_tickets = current_tickets - last_positions
                for ticket in new_tickets:
                    pos = next(p for p in current_positions if p["ticket"] == ticket)
                    await callback(pos)
                
                last_positions = current_tickets
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"MT5 monitoring error: {e}")
                await asyncio.sleep(5)
    
    def disconnect(self):
        """Disconnect from MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from MT5")

# Global MT5 instance
mt5_client = MT5Integration()