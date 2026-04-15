import asyncio
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings
from core.exchanges import exchange_manager
from core.trading import check_pending_orders

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self):
        self.running = False
        self.task = None

    async def _loop(self):
        while self.running:
            try:
                await asyncio.gather(
                    exchange_manager.fetch_prices()
                )
                await check_pending_orders()
            except Exception as e:
                logger.error(f"Scheduler error in main loop: {e}")
            await asyncio.sleep(settings.poll_interval)

    def start(self):
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._loop())

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
        await exchange_manager.close_connections()

scheduler = Scheduler()
