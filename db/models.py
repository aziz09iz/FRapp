from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import Base

class ActivePosition(Base):
    __tablename__ = "active_positions"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    long_exchange = Column(String)
    short_exchange = Column(String)
    entry_price_long = Column(Float, default=0.0)
    entry_price_short = Column(Float, default=0.0)
    current_spread = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    qty = Column(Float, default=0.0)
    funding_accrued = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)

class SettingsModel(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)

class PendingOrder(Base):
    __tablename__ = "pending_orders"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    target_spread_min = Column(Float)
    long_exchange = Column(String)
    short_exchange = Column(String)
    qty_usdt = Column(Float, default=100.0)
    leverage = Column(Integer, default=10)
    margin_mode = Column(String, default="cross")
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)
