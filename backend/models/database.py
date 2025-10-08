from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from utils.config import Config

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    account_type = Column(String, default='demo')
    balance = Column(Float, default=10000.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    api_token = Column(String)
    subscription_plan = Column(String, default='free')
    
    trades = relationship("Trade", back_populates="user")
    strategies = relationship("Strategy", back_populates="user")

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    stake = Column(Float, nullable=False)
    prediction = Column(Integer)
    result = Column(String)
    pnl = Column(Float)
    strategy_id = Column(Integer, ForeignKey('strategies.id'))
    confidence = Column(Float)
    contract_id = Column(String)
    contract_type = Column(String)
    is_demo = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="trades")
    strategy = relationship("Strategy", back_populates="trades")

class Strategy(Base):
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    risk_percent = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    trade_frequency = Column(String)
    parameters = Column(Text)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="strategies")
    trades = relationship("Trade", back_populates="strategy")

class Tick(Base):
    __tablename__ = "ticks"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    price = Column(Float, nullable=False)
    last_digit = Column(Integer)
    symbol = Column(String, default='R_100')

# Database setup
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()