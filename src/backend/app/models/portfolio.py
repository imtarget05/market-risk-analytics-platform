from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(String, nullable=True)
    base_currency = Column(String(3), default="USD", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    positions = relationship("Position", back_populates="portfolio")


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Numeric(18, 6), nullable=False)
    average_cost = Column(Numeric(18, 4), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    portfolio = relationship("Portfolio", back_populates="positions")


class PriceData(Base):
    __tablename__ = "price_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Numeric(18, 4), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class RiskCalculation(Base):
    __tablename__ = "risk_calculations"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    var_historical = Column(Numeric(18, 4), nullable=True)
    var_parametric = Column(Numeric(18, 4), nullable=True)
    var_monte_carlo = Column(Numeric(18, 4), nullable=True)
    expected_shortfall = Column(Numeric(18, 4), nullable=True)
    confidence_level = Column(Numeric(5, 4), default=0.95, nullable=False)
    time_horizon_days = Column(Integer, default=1, nullable=False)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

    portfolio = relationship("Portfolio")