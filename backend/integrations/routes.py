from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from .tradingview import router as tv_router
from .mt5 import mt5_client
from .signal_processor import signal_processor
from .websocket import integration_ws_manager
import logging

logger = logging.getLogger(__name__)

class MT5Config(BaseModel):
    login: int
    password: str
    server: str

router = APIRouter()

# Include TradingView routes
router.include_router(tv_router, prefix="/tradingview", tags=["TradingView"])

@router.post("/mt5/connect")
async def connect_mt5(config: MT5Config):
    """Connect to MetaTrader 5"""
    try:
        success = await mt5_client.connect(config.login, config.password, config.server)
        if success:
            return {"status": "connected", "account": mt5_client.account_info.name}
        else:
            raise HTTPException(status_code=400, detail="MT5 connection failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mt5/positions")
async def get_mt5_positions():
    """Get MT5 positions"""
    try:
        positions = await mt5_client.get_positions()
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mt5/start-monitoring")
async def start_mt5_monitoring(background_tasks: BackgroundTasks):
    """Start monitoring MT5 for new trades"""
    async def process_mt5_signal(position):
        signal = {
            "symbol": position["symbol"],
            "action": position["type"],
            "price": position["price_open"],
            "volume": position["volume"],
            "timestamp": position["time"].isoformat()
        }
        await signal_processor.process_signal(signal, "MT5")
    
    background_tasks.add_task(mt5_client.monitor_trades, process_mt5_signal)
    return {"status": "monitoring_started"}

@router.post("/mt5/disconnect")
async def disconnect_mt5():
    """Disconnect from MT5"""
    mt5_client.disconnect()
    return {"status": "disconnected"}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time integration data"""
    await integration_ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        integration_ws_manager.disconnect(websocket)

@router.get("/status")
async def integration_status():
    """Get integration status"""
    return {
        "tradingview": {"status": "active"},
        "mt5": {"status": "connected" if mt5_client.connected else "disconnected"},
        "signal_processor": {"active_signals": len(signal_processor.active_signals)},
        "websocket_connections": len(integration_ws_manager.active_connections)
    }