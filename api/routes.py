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
            "apr": apr,
            "bybit_price": pb,
            "gate_price": pg,
            "spread": spread            
        })
        
    results.sort(key=lambda x: x["apr"], reverse=True)
    top_5 = results[:5]

    return {
        "data": top_5,
        "latency": {
            "coinalyze": 0,
            "bybit": exchange_manager.latency.get('bybit', 0),
            "gateio": exchange_manager.latency.get('gateio', 0)
        }
    }

@router.get("/portfolio")
async def get_portfolio():
    return {"positions": []}
