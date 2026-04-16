import os
import dotenv
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    bybit_api_key: str = ""
    bybit_secret: str = ""
    gate_api_key: str = ""
    gate_secret: str = ""
    tg_bot_token: str = ""
    tg_chat_id: str = ""
    sqlite_db_url: str = "sqlite+aiosqlite:///./data.sqlite"
    poll_interval: int = 60
    auto_exit_apr_threshold: float = 10.0
    autopilot_enabled: bool = False
    autopilot_min_apr: float = 300.0
    trade_size_pct: float = 0.0  # 0 means fixed usdt size is used
    margin_alert_threshold: float = 80.0
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

def update_env(updates: dict):
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        with open(env_path, 'w') as f:
            pass
    for k, v in updates.items():
        dotenv.set_key(env_path, k.upper(), str(v))
        setattr(settings, k.lower(), v)
