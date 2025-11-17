from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
import logging
from typing import List
from .mt5 import mt5_client
from .signal_processor import signal_processor

logger = logging.getLogger(__name__)

class IntegrationWebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.is_broadcasting = False

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Integration WebSocket connected. Total: {len(self.active_connections)}")
        
        if not self.is_broadcasting:
            asyncio.create_task(self.start_broadcasting())

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Integration WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast_mt5_data(self, data):
        """Broadcast MT5 position data to all connected clients"""
        if self.active_connections:
            message = {
                "type": "mt5_position",
                "data": data,
                "timestamp": data.get("time")
            }
            await self._broadcast_message(message)

    async def broadcast_tradingview_signal(self, signal):
        """Broadcast TradingView signal to all connected clients"""
        if self.active_connections:
            message = {
                "type": "tradingview_signal", 
                "data": signal,
                "timestamp": signal.get("timestamp")
            }
            await self._broadcast_message(message)

    async def _broadcast_message(self, message):
        """Send message to all connected clients"""
        if not self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def start_broadcasting(self):
        """Start broadcasting MT5 data if connected"""
        self.is_broadcasting = True
        logger.info("Started integration broadcasting")
        
        while self.active_connections:
            try:
                if mt5_client.connected:
                    # Get current MT5 positions
                    positions = await mt5_client.get_positions()
                    for position in positions:
                        await self.broadcast_mt5_data(position)
                
                await asyncio.sleep(2)  # Broadcast every 2 seconds
                
            except Exception as e:
                logger.error(f"Broadcasting error: {e}")
                await asyncio.sleep(5)
        
        self.is_broadcasting = False
        logger.info("Stopped integration broadcasting")

# Global WebSocket manager
integration_ws_manager = IntegrationWebSocketManager()