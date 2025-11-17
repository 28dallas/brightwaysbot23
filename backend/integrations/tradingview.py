from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class TradingViewSignal(BaseModel):
    symbol: str
    action: str  # "buy" or "sell"
    price: float
    strategy: str
    timestamp: str
    contract_type: Optional[str] = "CALL"  # CALL/PUT for Deriv
    duration: Optional[int] = 5  # Duration in ticks

router = APIRouter()

@router.post("/webhook")
async def tradingview_webhook(signal: TradingViewSignal):
    """Process TradingView webhook signals"""
    try:
        logger.info(f"Received TradingView signal: {signal.dict()}")
        
        # Convert TradingView signal to Deriv trade
        trade_params = {
            "symbol": signal.symbol,
            "contract_type": signal.contract_type,
            "duration": signal.duration,
            "basis": "stake",
            "amount": 1.0,  # Will be calculated by risk management
            "barrier": signal.price if signal.action == "buy" else None
        }
        
        # Broadcast signal to WebSocket clients
        from .websocket import integration_ws_manager
        await integration_ws_manager.broadcast_tradingview_signal(signal.dict())
        
        # Execute trade through main trading engine
        from ..trading.engine import execute_trade
        result = await execute_trade(trade_params)
        
        return {"status": "success", "trade_id": result.get("contract_id")}
        
    except Exception as e:
        logger.error(f"TradingView webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status")
async def tradingview_status():
    """Check TradingView integration status"""
    return {"status": "active", "platform": "TradingView"}