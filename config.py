import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    bybit_api_key: str = ""
    bybit_secret: str = ""
    gate_api_key: str = ""
    gate_secret: str = ""
    sqlite_db_url: str = "sqlite+aiosqlite:///./data.sqlite"
    poll_interval: int = 60
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
