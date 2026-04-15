import ccxt.async_support as ccxt
import logging
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings

logger = logging.getLogger(__name__)

class ExchangeManager:
    def __init__(self):
        self.bybit = ccxt.bybit({
            'apiKey': settings.bybit_api_key,
            'secret': settings.bybit_secret,
            'enableRateLimit': False,
            'options': {'defaultType': 'swap'}
        })
        self.gateio = ccxt.gateio({
            'apiKey': settings.gate_api_key,
            'secret': settings.gate_secret,
            'enableRateLimit': False,
            'options': {'defaultType': 'swap'}
        })
        self.last_prices = {'bybit': {}, 'gateio': {}}
        self.latency = {'bybit': 0, 'gateio': 0}

    def _normalize_symbol(self, symbol):
        # Keep only alphanumeric chars (e.g. BTCUSDT)
        return ''.join(e for e in symbol if e.isalnum()).upper()

    async def fetch_prices(self):
        async def fetch_ex(exchange, name):
            start = asyncio.get_event_loop().time()
            try:
                tickers = await exchange.fetch_tickers()
                self.last_prices[name] = {
                    self._normalize_symbol(k): v['last']
                    for k, v in tickers.items() if v.get('last')
                }
            except Exception as e:
                logger.error(f"{name} fetch_tickers error: {e}")
            finally:
                self.latency[name] = int((asyncio.get_event_loop().time() - start) * 1000)

        await asyncio.gather(
            fetch_ex(self.bybit, 'bybit'),
            fetch_ex(self.gateio, 'gateio')
        )

    def get_price(self, exchange_name, symbol_normalized):
        return self.last_prices.get(exchange_name, {}).get(symbol_normalized)

    async def close_connections(self):
        await self.bybit.close()
        await self.gateio.close()

exchange_manager = ExchangeManager()
