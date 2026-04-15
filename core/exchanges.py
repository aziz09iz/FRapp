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
        self.last_funding_rates = {'bybit': {}, 'gateio': {}}
        self.latency = {'bybit': 0, 'gateio': 0}

    def _normalize_symbol(self, symbol):
        # Keep only alphanumeric chars (e.g. BTCUSDT)
        return ''.join(e for e in symbol if e.isalnum()).upper()

    async def fetch_prices(self):
        async def fetch_ex(exchange, name):
            start = asyncio.get_event_loop().time()
            try:
                tickers = await exchange.fetch_tickers()
                self.last_prices[name] = {}
                self.last_funding_rates[name] = {}
                for k, v in tickers.items():
                    if not v.get('last'):
                        continue
                    sym = self._normalize_symbol(k)
                    self.last_prices[name][sym] = float(v['last'])
                    
                    # Extract funding rate from info object avoiding extra api limits
                    fr = 0.0
                    if 'info' in v:
                        if name == 'bybit':
                            fr_raw = v['info'].get('fundingRate')
                            fr = float(fr_raw) if fr_raw else 0.0
                        elif name == 'gateio':
                            fr_raw = v['info'].get('funding_rate')
                            fr = float(fr_raw) if fr_raw else 0.0
                    self.last_funding_rates[name][sym] = fr
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
        
    def get_funding_rate(self, exchange_name, symbol_normalized):
        return self.last_funding_rates.get(exchange_name, {}).get(symbol_normalized)

    async def close_connections(self):
        await self.bybit.close()
        await self.gateio.close()

    async def reinit(self):
        await self.close_connections()
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

exchange_manager = ExchangeManager()
