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
        "balances": exchange_manager.balances,
        "latency": {
            "coinalyze": 0,
            "bybit": exchange_manager.latency.get('bybit', 0),
            "gateio": exchange_manager.latency.get('gateio', 0)
        }
    }

@router.get("/portfolio")
async def get_portfolio():
    from db.models import ActivePosition
    from db.database import AsyncSessionLocal
    from sqlalchemy.future import select
    
    positions_data = []
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ActivePosition).where(ActivePosition.active == True))
        positions = result.scalars().all()
        
        for pos in positions:
            p_long = exchange_manager.get_price(pos.long_exchange, pos.symbol) or 0.0
            p_short = exchange_manager.get_price(pos.short_exchange, pos.symbol) or 0.0
            
            pnl_long = (p_long - pos.entry_price_long) * pos.qty if pos.entry_price_long else 0
            pnl_short = (pos.entry_price_short - p_short) * pos.qty if pos.entry_price_short else 0
            
            positions_data.append({
                "id": pos.id,
                "symbol": pos.symbol,
                "long_exchange": pos.long_exchange,
                "short_exchange": pos.short_exchange,
                "qty": pos.qty,
                "entry_price_long": pos.entry_price_long,
                "entry_price_short": pos.entry_price_short,
                "current_price_long": p_long,
                "current_price_short": p_short,
                "u_pnl": pnl_long + pnl_short,
                "funding_accrued": pos.funding_accrued
            })
            
    return {"positions": positions_data}

@router.get("/history")
async def get_history():
    from db.models import ActivePosition
    from db.database import AsyncSessionLocal
    from sqlalchemy.future import select
    from sqlalchemy import desc
    
    positions_data = []
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ActivePosition)
            .where(ActivePosition.active == False)
            .order_by(desc(ActivePosition.closed_at))
        )
        positions = result.scalars().all()
        for pos in positions:
            positions_data.append({
                "symbol": pos.symbol,
                "long_exchange": pos.long_exchange,
                "short_exchange": pos.short_exchange,
                "qty": pos.qty,
                "entry_long": pos.entry_price_long,
                "entry_short": pos.entry_price_short,
                "realized_pnl": pos.realized_pnl,
                "funding_accrued": pos.funding_accrued,
                "closed_at": pos.closed_at.isoformat() if pos.closed_at else ""
            })
    return {"history": positions_data}

@router.post("/close_position")
async def api_close_position(data: dict):
    from db.models import ActivePosition
    from db.database import AsyncSessionLocal
    from core.trading import execute_order
    import asyncio
    from datetime import datetime
    
    pos_id = data.get('id')
    if not pos_id: return {"status": "error"}
    
    async with AsyncSessionLocal() as session:
        pos = await session.get(ActivePosition, pos_id)
        if pos and pos.active:
            # calculate realized PnL
            from core.exchanges import exchange_manager
            p_long = exchange_manager.get_price(pos.long_exchange, pos.symbol) or pos.entry_price_long
            p_short = exchange_manager.get_price(pos.short_exchange, pos.symbol) or pos.entry_price_short
            
            pnl_long = (p_long - pos.entry_price_long) * pos.qty if pos.entry_price_long else 0
            pnl_short = (pos.entry_price_short - p_short) * pos.qty if pos.entry_price_short else 0
            
            pos.realized_pnl = pnl_long + pnl_short
            pos.closed_at = datetime.utcnow()
            pos.active = False
            await session.commit()
            
            # Close logically reverses the sides
            asyncio.create_task(execute_order(pos.long_exchange, pos.symbol, "sell", amount=pos.qty))
            asyncio.create_task(execute_order(pos.short_exchange, pos.symbol, "buy", amount=pos.qty))
            return {"status": "ok", "message": f"Closed {pos.symbol}"}
    return {"status": "error", "message": "Position not found"}

from pydantic import BaseModel
from config import update_env, settings

class SettingsUpdate(BaseModel):
    bybit_api_key: str
    bybit_secret: str
    gate_api_key: str
    gate_secret: str
    tg_bot_token: str
    tg_chat_id: str
    autopilot_enabled: bool
    autopilot_min_apr: float
    trade_size_pct: float
    margin_alert_threshold: float

@router.get("/settings")
async def api_get_settings():
    return {
        "bybit_api_key": settings.bybit_api_key,
        "bybit_secret": settings.bybit_secret,
        "gate_api_key": settings.gate_api_key,
        "gate_secret": settings.gate_secret,
        "tg_bot_token": getattr(settings, 'tg_bot_token', ""),
        "tg_chat_id": getattr(settings, 'tg_chat_id', ""),
        "autopilot_enabled": getattr(settings, 'autopilot_enabled', False),
        "autopilot_min_apr": getattr(settings, 'autopilot_min_apr', 300.0),
        "trade_size_pct": getattr(settings, 'trade_size_pct', 0.0),
        "margin_alert_threshold": getattr(settings, 'margin_alert_threshold', 80.0)
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
