import asyncio
import logging
from core.exchanges import exchange_manager
from db.database import AsyncSessionLocal
from db.models import PendingOrder, ActivePosition

logger = logging.getLogger(__name__)

async def execute_order(exchange_name, symbol, side, type="market", amount=1):
    logger.info(f"Submitting {side} {type} order for {amount} {symbol} on {exchange_name}")
    start = asyncio.get_event_loop().time()
    try:
        if exchange_name == "bybit":
            # order = await exchange_manager.bybit.create_order(symbol, type, side, amount)
            pass
        elif exchange_name == "gateio":
            # order = await exchange_manager.gateio.create_order(symbol, type, side, amount)
            pass
        await asyncio.sleep(0.1) # Simulate network time for mockup
    except Exception as e:
        logger.error(f"Order error: {e}")
    finally:
        latency = (asyncio.get_event_loop().time() - start) * 1000
        logger.info(f"Order on {exchange_name} completed in {latency:.2f}ms")

async def check_pending_orders():
    async with AsyncSessionLocal() as session:
        # Fetch active pending orders
        # For simplicity in this script, we'll query all
        # Normally: orders = await session.execute(select(PendingOrder).where(PendingOrder.active == True))
        pass

async def process_instant_entry(symbol, long_exchange, short_exchange):
    # Execute simultaneously
    await asyncio.gather(
        execute_order(long_exchange, symbol, "buy"),
        execute_order(short_exchange, symbol, "sell")
    )
    # Save to ActivePositions
    async with AsyncSessionLocal() as session:
        pos = ActivePosition(
            symbol=symbol,
            long_exchange=long_exchange,
            short_exchange=short_exchange,
            qty=1.0
        )
        session.add(pos)
        await session.commit()
