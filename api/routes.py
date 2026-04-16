from fastapi import APIRouter
from core.exchanges import exchange_manager

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard():
    bybit_symbols = set(exchange_manager.last_prices.get('bybit', {}).keys())
    gateio_symbols = set(exchange_manager.last_prices.get('gateio', {}).keys())
    
    # Target overlapping symbols
    common_symbols = bybit_symbols.intersection(gateio_symbols)
    
    results = []
    for symbol in common_symbols:
        pb = exchange_manager.get_price('bybit', symbol) or 0
        pg = exchange_manager.get_price('gateio', symbol) or 0
        fb = exchange_manager.get_funding_rate('bybit', symbol) or 0
        fg = exchange_manager.get_funding_rate('gateio', symbol) or 0
        nxt = exchange_manager.next_funding_times.get('bybit', {}).get(symbol, 0)
        
        # Only consider symbols where we actually extracted funding rate realistically
        # E.g. avoid clutter if both are exactly 0 in info
        if fb == 0 and fg == 0:
            continue
            
        spread = pb - pg if pb and pg else 0
        diff = abs(fb - fg)
        apr = round(diff * 3 * 365 * 100, 2)
        
        results.append({
            "symbol": symbol,
            "bybit_fr": fb,
            "gate_fr": fg,
            "interval": 8,
            "next_funding_time": nxt,
            "apr": apr,
            "bybit_price": pb,
            "gate_price": pg,
            "spread": spread            
        })
        
    results.sort(key=lambda x: x["apr"], reverse=True)
    top_5 = results[:5]

    return {
        "data": top_5,
        "latency": {
            "coinalyze": 0,
            "bybit": exchange_manager.latency.get('bybit', 0),
            "gateio": exchange_manager.latency.get('gateio', 0)
        }
    }

@router.get("/portfolio")
async def get_portfolio():
    return {"positions": []}

from pydantic import BaseModel
from config import update_env, settings

class SettingsUpdate(BaseModel):
    bybit_api_key: str
    bybit_secret: str
    gate_api_key: str
    gate_secret: str

@router.get("/settings")
async def api_get_settings():
    return {
        "bybit_api_key": settings.bybit_api_key,
        "bybit_secret": settings.bybit_secret,
        "gate_api_key": settings.gate_api_key,
        "gate_secret": settings.gate_secret
    }

@router.post("/settings")
async def api_post_settings(data: SettingsUpdate):
    update_env(data.model_dump())
    await exchange_manager.reinit()
    return {"status": "ok", "message": "Settings saved to .env"}

class TradeRequest(BaseModel):
    symbol: str
    size_usdt: float
    leverage: int
    margin_mode: str
    long_exchange: str
    short_exchange: str
    mode: str = "instant"

@router.post("/execute")
async def execute_trade(data: TradeRequest):
    if data.mode == "instant":
        from core.trading import process_instant_entry
        import asyncio
        asyncio.create_task(
            process_instant_entry(
                data.symbol, 
                data.long_exchange, 
                data.short_exchange, 
                data.size_usdt, 
                data.leverage, 
                data.margin_mode
            )
        )
        return {"status": "ok", "message": f"Instant Execution triggered for {data.symbol}"}
    else:
        from db.models import PendingOrder
        from db.database import AsyncSessionLocal
        import asyncio
        async def save_pending():
            async with AsyncSessionLocal() as session:
                po = PendingOrder(
                    symbol=data.symbol,
                    target_spread_min=0.0,
                    long_exchange=data.long_exchange,
                    short_exchange=data.short_exchange,
                    qty_usdt=data.size_usdt,
                    leverage=data.leverage,
                    margin_mode=data.margin_mode,
                    active=True
                )
                session.add(po)
                await session.commit()
                
        asyncio.create_task(save_pending())
        return {"status": "ok", "message": f"Delayed execution scheduled for {data.symbol} (Waiting for positive spread)"}
