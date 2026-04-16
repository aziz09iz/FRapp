import asyncio
import logging
from core.exchanges import exchange_manager
from core.exchanges import exchange_manager
from db.database import AsyncSessionLocal
from db.models import PendingOrder, ActivePosition
from core.notify import send_tg_message
from config import settings

logger = logging.getLogger(__name__)

async def execute_order(exchange_name, symbol, side, type="market", amount=1, params=None):
    if params is None:
        params = {}
    logger.info(f"Submitting {side} {type} order for {amount} {symbol} on {exchange_name} with {params}")
    start = asyncio.get_event_loop().time()
    try:
        if exchange_name == "bybit":
            # Set leverage/margin mode (mockup for now, ccxt supports it via param/specific methods)
            # await exchange_manager.bybit_private.set_leverage(leverage, symbol)
            # order = await exchange_manager.bybit_private.create_order(symbol, type, side, amount, params=params)
            pass
        elif exchange_name == "gateio":
            # order = await exchange_manager.gateio_private.create_order(symbol, type, side, amount, params=params)
            pass
        await asyncio.sleep(0.1) # Simulate network time for mockup
    except Exception as e:
        logger.error(f"Order error: {e}")
    finally:
        latency = (asyncio.get_event_loop().time() - start) * 1000
        logger.info(f"Order on {exchange_name} completed in {latency:.2f}ms")

async def check_pending_orders():
    from sqlalchemy.future import select
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(PendingOrder).where(PendingOrder.active == True))
            orders = result.scalars().all()
            
            for order in orders:
                p_long = exchange_manager.get_price(order.long_exchange, order.symbol)
                p_short = exchange_manager.get_price(order.short_exchange, order.symbol)
                
                if not p_long or not p_short:
                    continue
                    
                # positive absolute spread (short selling price minus long buying price)
                # target is p_short >= p_long, so p_short - p_long >= 0
                favorable_spread = p_short - p_long
                
                if favorable_spread >= order.target_spread_min:
                    logger.info(f"Executing pending order {order.symbol}, spread {favorable_spread} >= {order.target_spread_min}")
                order.active = False
                await session.commit()
                
                size = getattr(order, 'qty_usdt', 100.0)
                lev = getattr(order, 'leverage', 10)
                margin = getattr(order, 'margin_mode', 'cross')
                
                asyncio.create_task(
                    process_instant_entry(
                        symbol=order.symbol,
                        long_exchange=order.long_exchange,
                        short_exchange=order.short_exchange,
                        size_usdt=size,
                        leverage=lev,
                        margin_mode=margin
                    )
                )
    except Exception as e:
        logger.error(f"Error checking pending orders: {e}")

async def check_active_positions():
    from sqlalchemy.future import select
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ActivePosition).where(ActivePosition.active == True))
            positions = result.scalars().all()
            
            for pos in positions:
                pb = exchange_manager.get_price('bybit', pos.symbol)
                pg = exchange_manager.get_price('gateio', pos.symbol)
                fb = exchange_manager.get_funding_rate('bybit', pos.symbol)
                fg = exchange_manager.get_funding_rate('gateio', pos.symbol)
                
                if not pb or not pg:
                    continue
                
                # Check Auto-Exit APR Logic
                apr = abs((fb or 0) - (fg or 0)) * 3 * 365 * 100
                threshold = getattr(settings, 'auto_exit_apr_threshold', 10.0)
                if apr < threshold:
                    pos.active = False
                    # calculate realized PnL
                    from datetime import datetime
                    pos.closed_at = datetime.utcnow()
                    pnl_long = (pb - pos.entry_price_long) * pos.qty if pos.entry_price_long else 0
                    pnl_short = (pos.entry_price_short - pg) * pos.qty if pos.entry_price_short else 0
                    pos.realized_pnl = pnl_long + pnl_short
                    await session.commit()
                    
                    msg = f"🚨 <b>Auto-Exit Triggered</b> for {pos.symbol}.\nAPR dropped to {apr:.2f}% (Below {threshold}%)."
                    await send_tg_message(msg)
                    logger.info(f"Auto exited {pos.symbol}")
                    # Simulate Close order here
                    asyncio.create_task(execute_order(pos.long_exchange, pos.symbol, "sell", amount=pos.qty))
                    asyncio.create_task(execute_order(pos.short_exchange, pos.symbol, "buy", amount=pos.qty))
    except Exception as e:
        logger.error(f"Error checking active positions: {e}")

async def run_autopilot():
    if not getattr(settings, 'autopilot_enabled', False):
        return
        
    try:
        from core.exchanges import exchange_manager
        
        # Scrape all common
        bybit_symbols = set(exchange_manager.last_prices.get('bybit', {}).keys())
        gateio_symbols = set(exchange_manager.last_prices.get('gateio', {}).keys())
        common_symbols = bybit_symbols.intersection(gateio_symbols)
        
        min_apr = getattr(settings, 'autopilot_min_apr', 300.0)
        
        best_sym = None
        best_apr = 0
        best_long = ""
        best_short = ""
        
        from sqlalchemy.future import select
        async with AsyncSessionLocal() as session:
            # Get existing active symbols
            result = await session.execute(select(ActivePosition.symbol).where(ActivePosition.active == True))
            active_symbols = set(result.scalars().all())
            
            for symbol in common_symbols:
                if symbol in active_symbols:
                    continue
                
                pb = exchange_manager.get_price('bybit', symbol) or 0
                pg = exchange_manager.get_price('gateio', symbol) or 0
                fb = exchange_manager.get_funding_rate('bybit', symbol) or 0
                fg = exchange_manager.get_funding_rate('gateio', symbol) or 0
                
                if not pb or not pg or (fb == 0 and fg == 0):
                    continue
                    
                diff = abs(fb - fg)
                apr = diff * 3 * 365 * 100
                
                if apr >= min_apr:
                    # check spread to be non negative
                    longEx = "gateio" if fb > fg else "bybit"
                    shortEx = "bybit" if fb > fg else "gateio"
                    pl = pg if longEx == "gateio" else pb
                    ps = pb if shortEx == "bybit" else pg
                    
                    if (ps - pl) >= 0:
                        if apr > best_apr:
                            best_apr = apr
                            best_sym = symbol
                            best_long = longEx
                            best_short = shortEx
                            
            if best_sym:
                logger.info(f"Autopilot triggered for {best_sym} with {best_apr}% APR")
                
                size_pct = getattr(settings, 'trade_size_pct', 0.0)
                amount = 100.0 # Default fallback
                if size_pct > 0:
                    b1 = exchange_manager.balances.get('bybit', 0)
                    b2 = exchange_manager.balances.get('gateio', 0)
                    min_bal = min(b1, b2)
                    if min_bal > 10:
                        amount = min_bal * (size_pct / 100.0)
                        
                await process_instant_entry(
                    symbol=best_sym,
                    long_exchange=best_long,
                    short_exchange=best_short,
                    size_usdt=amount,
                    leverage=10,
                    margin_mode="cross"
                )
                
    except Exception as e:
        logger.error(f"Autopilot error: {e}")

async def process_instant_entry(symbol, long_exchange, short_exchange, size_usdt: float = 100.0, leverage: int = 10, margin_mode: str = "cross"):
    # Mockup of fetching price to convert USDT size to Asset Size
    # bybit_price = exchange_manager.get_price('bybit', symbol) or 1
    # amount = size_usdt / bybit_price
    amount = 0.01 # Mocked
    
    # Execute simultaneously
    # Pass leverage and margin mode into params
    params = {"leverage": leverage, "marginMode": margin_mode}
    
    await asyncio.gather(
        execute_order(long_exchange, symbol, "buy", amount=amount, params=params),
        execute_order(short_exchange, symbol, "sell", amount=amount, params=params)
    )
    # Save to ActivePositions
    async with AsyncSessionLocal() as session:
        pos = ActivePosition(
            symbol=symbol,
            long_exchange=long_exchange,
            short_exchange=short_exchange,
            entry_price_long=exchange_manager.get_price(long_exchange, symbol) or 0.0,
            entry_price_short=exchange_manager.get_price(short_exchange, symbol) or 0.0,
            qty=amount,
            active=True
        )
        session.add(pos)
        await session.commit()
        await send_tg_message(f"✅ <b>Hedge Executed</b>: {symbol}\nLong: {long_exchange}\nShort: {short_exchange}\nSize: {amount} / Lev: {leverage}x")
