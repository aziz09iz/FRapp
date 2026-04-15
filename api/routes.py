from fastapi import APIRouter
from core.coinalyze import coinalyze_client
from core.exchanges import exchange_manager

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard():
    enriched = []
    for item in coinalyze_client.top_funding_rates:
        symbol = item["symbol"]
        pb = exchange_manager.get_price('bybit', symbol) or 0
        pg = exchange_manager.get_price('gateio', symbol) or 0
        spread = pb - pg if pb and pg else 0
        enriched.append({
            **item,
            "bybit_price": pb,
            "gate_price": pg,
            "spread": spread
        })
    return {
        "data": enriched,
        "latency": {
            "coinalyze": coinalyze_client.latency,
            "bybit": exchange_manager.latency['bybit'],
            "gateio": exchange_manager.latency['gateio']
        }
    }

@router.get("/portfolio")
async def get_portfolio():
    return {"positions": []}
