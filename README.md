# Funding Rate Farming & Arbitrage Web App

This is a production-oriented web application designed to identify funding rate opportunities and arbitrage spreads between Bybit and Gate.io perpetual futures. The application uses a Fast Python + FastAPI backend integrated with CCXT and an asynchronous SQLite datastore to ensure optimal performance and minimal API latency. 

## Key Features
- **Top 5 Funding Rates Dashboard:** Powered natively by the public CCXT payloads from Bybit and Gate (polls every 60 seconds to avoid limit bans without sacrificing speed).
- **Full Autopilot Automation [NEW]:** Configurable background scanner that directly dispatches hedge operations asynchronously when the specified APR bounds and Spread conditions are satisfied, 100% hands-free.
- **Dynamic Portfolio & Auto-Exit [NEW]:** Live monitoring of hedge states with unrealized PnL readouts. Automatically dispatches emergency Close limit orders when the APR dips below a threshold limits to preserve overall profitability.
- **Telegram Notification Bot [NEW]:** Configurable bot listener to ping your phone immediately upon order executions and danger-zone auto-exit triggers.
- **Realized Trade Ledger (History) [NEW]:** A comprehensive ledger view recording exact long vs short entry costs, harvested funding fees, and final realized PnL.
- **Balance-Aware Dynamic Sizing [NEW]:** Extrapolates optimal position lot sizes by fetching live Bybit & Gateio available margin and clamping trade deployments down to a percentage scale (e.g. 10% of portfolio size) rather than fixed USDT.
- **Simultaneous Arbitrage Execution:** Built-in dashboard configuration bounds locking exact Margin, Size, and Leverage profiles routing parallel dual-exchange orders via asyncio.
- **Modern Institutional UI:** Rebuilt utilizing deep-dark glass aesthetics and background CSS gradients without relying on intense framework bloat. Integrated countdown timers sync seamlessly in Javascript.

## Project Structure

```text
/
├── main.py                # FastAPI entry point & app lifecycle manager
├── config.py              # Environment configuration loading via Pydantic
├── requirements.txt       # Python dependencies
├── db/                    # SQLite SQLAlchemy integration (database.py, models.py)
├── core/                  # Core modules (trading, scheduler, ccxt wrapper)
├── api/                   # FastAPI Endpoints (routes.py, views.py)
└── templates/             # Jinja2 and Tailwind HTML templates
```

## Setup & Run Instructions

### 1. Prerequisites
Ensure you have Python 3.11+ installed and the path is globally accessible.

### 2. Create the Virtual Environment
Using PowerShell inside the project directory:
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a file named `.env` in the root directory. You can specify the API Keys there or use the Settings page in the UI to manage Gate.io and Bybit keys:

```text
BYBIT_API_KEY=YOUR_BYBIT_KEY
BYBIT_SECRET=YOUR_BYBIT_SECRET
GATE_API_KEY=YOUR_GATE_KEY
GATE_SECRET=YOUR_GATE_SECRET
```

### 5. Launch the Server
To launch the FastAPI server using Uvicorn, execute the following command:
```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6. View the App
Navigate to [http://localhost:8000](http://localhost:8000) in your web browser.
