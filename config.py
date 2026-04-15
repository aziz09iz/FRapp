import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    coinalyze_api_key: str = "5ac7435e-8aa0-4f1a-abb8-daa96820cb51"
    bybit_api_key: str = ""
    bybit_secret: str = ""
    gate_api_key: str = ""
    gate_secret: str = ""
    sqlite_db_url: str = "sqlite+aiosqlite:///./data.sqlite"
    poll_interval: int = 5
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
