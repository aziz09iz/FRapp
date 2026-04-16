import asyncio
import logging
from core.exchanges import exchange_manager
from db.database import AsyncSessionLocal
from db.models import PendingOrder, ActivePosition

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
            qty=amount
        )
        session.add(pos)
        await session.commit()
