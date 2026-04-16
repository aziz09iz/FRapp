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
        public_opts = {'enableRateLimit': False, 'options': {'defaultType': 'swap'}}
        self.bybit_public = ccxt.bybit(public_opts)
        self.gateio_public = ccxt.gateio(public_opts)
        
        self.bybit_private = None
        self.gateio_private = None
        self._init_private()

        self.last_prices = {'bybit': {}, 'gateio': {}}
        self.last_funding_rates = {'bybit': {}, 'gateio': {}}
        self.next_funding_times = {'bybit': {}, 'gateio': {}}
        self.latency = {'bybit': 0, 'gateio': 0}
        self.balances = {'bybit': 0.0, 'gateio': 0.0}

    def _init_private(self):
        bybit_opts = {'enableRateLimit': False, 'options': {'defaultType': 'swap'}}
        if settings.bybit_api_key:
            bybit_opts['apiKey'] = settings.bybit_api_key
            bybit_opts['secret'] = settings.bybit_secret
        self.bybit_private = ccxt.bybit(bybit_opts)

        gateio_opts = {'enableRateLimit': False, 'options': {'defaultType': 'swap'}}
        if settings.gate_api_key:
            gateio_opts['apiKey'] = settings.gate_api_key
            gateio_opts['secret'] = settings.gate_secret
        self.gateio_private = ccxt.gateio(gateio_opts)

    def _normalize_symbol(self, symbol):
        # e.g. BTC/USDT:USDT -> BTC/USDT -> BTCUSDT
        base_quote = symbol.split(':')[0]
        return base_quote.replace('/', '').upper()

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
                    nxt_funding = 0
                    if 'info' in v:
                        if name == 'bybit':
                            fr_raw = v['info'].get('fundingRate')
                            fr = float(fr_raw) if fr_raw else 0.0
                            nxt_raw = v['info'].get('nextFundingTime')
                            nxt_funding = int(nxt_raw) if nxt_raw else 0
                        elif name == 'gateio':
                            fr_raw = v['info'].get('funding_rate')
                            fr = float(fr_raw) if fr_raw else 0.0
                    self.last_funding_rates[name][sym] = fr
                    if nxt_funding > 0:
                        self.next_funding_times[name][sym] = nxt_funding
            except Exception as e:
                logger.error(f"{name} fetch_tickers error: {e}")
            finally:
                self.latency[name] = int((asyncio.get_event_loop().time() - start) * 1000)

        # Specifically passing the public instances that carry ZERO api keys!
        await asyncio.gather(
            fetch_ex(self.bybit_public, 'bybit'),
            fetch_ex(self.gateio_public, 'gateio')
        )

    async def fetch_balances(self):
        async def fetch_bal(exchange_priv, name):
            if not exchange_priv:
                return
            start = asyncio.get_event_loop().time()
            try:
                bal = await exchange_priv.fetch_balance()
                total_usdt = bal.get('USDT', {}).get('total', 0.0)
                self.balances[name] = float(total_usdt)
            except Exception as e:
                logger.error(f"{name} fetch_balance error: {e}")

        # Fetch balances concurrently for private accounts
        tasks = []
        if self.bybit_private: tasks.append(fetch_bal(self.bybit_private, 'bybit'))
        if self.gateio_private: tasks.append(fetch_bal(self.gateio_private, 'gateio'))
        
        if tasks:
            await asyncio.gather(*tasks)

    def get_price(self, exchange_name, symbol_normalized):
        return self.last_prices.get(exchange_name, {}).get(symbol_normalized)
        
    def get_funding_rate(self, exchange_name, symbol_normalized):
        return self.last_funding_rates.get(exchange_name, {}).get(symbol_normalized)

    async def close_connections(self):
        await self.bybit_public.close()
        await self.gateio_public.close()
        if self.bybit_private:
            await self.bybit_private.close()
        if self.gateio_private:
            await self.gateio_private.close()

    async def reinit(self):
        await self.close_connections()
        # Public connections never change, but we refresh them too
        public_opts = {'enableRateLimit': False, 'options': {'defaultType': 'swap'}}
        self.bybit_public = ccxt.bybit(public_opts)
        self.gateio_public = ccxt.gateio(public_opts)
        
        self._init_private()

exchange_manager = ExchangeManager()
