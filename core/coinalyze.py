import httpx
import logging
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings

logger = logging.getLogger(__name__)

class CoinalyzeClient:
    def __init__(self):
        self.api_key = settings.coinalyze_api_key
        self.base_url = "https://api.coinalyze.net/v1"
        self.client = httpx.AsyncClient(timeout=10.0)
        self.top_funding_rates = []
        self.latency = 0
        
        self.base_assets = [
            "BTC", "ETH", "SOL", "XRP", "DOGE", 
            "ADA", "AVAX", "LINK", "MATIC", "DOT", 
            "BCH", "LTC", "NEAR", "STX", "AAVE"
        ]
        symbols = []
        for base in self.base_assets:
            symbols.append(f"{base}USDT.6") # Bybit USDT perp
            symbols.append(f"{base}_USDT.Y") # Gate USDT perp
        self.symbols_param = ",".join(symbols)

    async def fetch_and_compute(self):
        start = asyncio.get_event_loop().time()
        try:
            res = await self.client.get(
                f"{self.base_url}/funding-rate", 
                params={"symbols": self.symbols_param},
                headers={"api_key": self.api_key}
            )
            res.raise_for_status()
            data = res.json()
            self._process_data(data)
        except Exception as e:
            logger.error(f"Coinalyze fetch error: {e}")
            if not self.top_funding_rates:
                self._mock_data()
        finally:
            self.latency = int((asyncio.get_event_loop().time() - start) * 1000)

    def _process_data(self, data):
        rates = {}
        for item in data:
            sym = item.get("symbol", "")
            val = float(item.get("value", 0))

            if sym.endswith(".6"):
                base = sym.replace("USDT.6", "")
                if base not in rates:
                    rates[base] = {"symbol": f"{base}USDT", "bybit_fr": 0.0, "gate_fr": 0.0, "interval": 8, "apr": 0.0}
                rates[base]["bybit_fr"] = val
            elif sym.endswith(".Y"):
                base = sym.replace("_USDT.Y", "")
                if base not in rates:
                    rates[base] = {"symbol": f"{base}USDT", "bybit_fr": 0.0, "gate_fr": 0.0, "interval": 8, "apr": 0.0}
                rates[base]["gate_fr"] = val

        results = []
        for r in rates.values():
            diff = abs(r["bybit_fr"] - r["gate_fr"])
            r["apr"] = round(diff * 3 * 365 * 100, 2)
            results.append(r)
        
        results.sort(key=lambda x: x["apr"], reverse=True)
        # Berikan top 5 rate dengan selisih terbesar
        self.top_funding_rates = results[:5]

    def _mock_data(self):
        self.top_funding_rates = [
            {"symbol": "BTCUSDT", "bybit_fr": 0.0001, "gate_fr": -0.00005, "interval": 8, "apr": 54.75},
            {"symbol": "ETHUSDT", "bybit_fr": 0.00008, "gate_fr": -0.00002, "interval": 8, "apr": 32.85},
            {"symbol": "SOLUSDT", "bybit_fr": 0.00015, "gate_fr": 0.00005, "interval": 8, "apr": 36.5},
            {"symbol": "XRPUSDT", "bybit_fr": 0.00005, "gate_fr": 0.00005, "interval": 8, "apr": 0},
            {"symbol": "DOGEUSDT", "bybit_fr": -0.0001, "gate_fr": 0.0001, "interval": 8, "apr": 73.0},
        ]

    async def close(self):
        await self.client.aclose()

coinalyze_client = CoinalyzeClient()
