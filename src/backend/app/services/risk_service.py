from decimal import Decimal
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import numpy as np

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Portfolio, Position, PriceData, RiskCalculation
from app.schemas import (
    PortfolioCreate, PortfolioResponse,
    PositionCreate, PositionResponse,
    PriceDataCreate, PriceDataResponse,
    RiskCalculationRequest, RiskCalculationResponse,
    StressTestRequest, StressTestResponse,
)


class PortfolioService:
    @staticmethod
    def create_portfolio(db: Session, name: str, description: Optional[str], base_currency: str) -> Portfolio:
        portfolio = Portfolio(
            name=name,
            description=description,
            base_currency=base_currency,
        )
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
        return portfolio

    @staticmethod
    def get_portfolios(db: Session) -> List[Portfolio]:
        return db.query(Portfolio).all()

    @staticmethod
    def get_portfolio(db: Session, portfolio_id: int) -> Optional[Portfolio]:
        return db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()

    @staticmethod
    def add_position(db: Session, portfolio_id: int, symbol: str, quantity: Decimal, average_cost: Decimal) -> Position:
        position = Position(
            portfolio_id=portfolio_id,
            symbol=symbol,
            quantity=quantity,
            average_cost=average_cost,
        )
        db.add(position)
        db.commit()
        db.refresh(position)
        return position

    @staticmethod
    def get_portfolio_positions(db: Session, portfolio_id: int) -> List[Position]:
        return db.query(Position).filter(Position.portfolio_id == portfolio_id).all()

    @staticmethod
    def get_portfolio_value(db: Session, portfolio_id: int) -> Decimal:
        positions = db.query(Position).filter(Position.portfolio_id == portfolio_id).all()
        total = Decimal("0")
        for pos in positions:
            latest_price = (
                db.query(PriceData)
                .filter(PriceData.symbol == pos.symbol)
                .order_by(desc(PriceData.timestamp))
                .first()
            )
            if latest_price:
                total += pos.quantity * latest_price.price
        return total


class PriceService:
    @staticmethod
    def add_price(db: Session, symbol: str, price: Decimal) -> PriceData:
        price_data = PriceData(symbol=symbol, price=price)
        db.add(price_data)
        db.commit()
        db.refresh(price_data)
        return price_data

    @staticmethod
    def get_price_history(db: Session, symbol: str, limit: int = 252) -> List[float]:
        rows = (
            db.query(PriceData)
            .filter(PriceData.symbol == symbol)
            .order_by(desc(PriceData.timestamp))
            .limit(limit)
            .all()
        )
        return [float(r.price) for r in reversed(rows)]


class RiskService:
    """Market risk calculations: VaR, Expected Shortfall, Monte Carlo, Stress Testing."""

    @staticmethod
    def calculate_var_historical(returns: list[float], confidence_level: float = 0.95) -> float:
        """Historical simulation VaR."""
        if not returns:
            return 0.0
        sorted_returns = sorted(returns)
        index = int((1 - confidence_level) * len(sorted_returns))
        index = max(0, min(index, len(sorted_returns) - 1))
        return abs(sorted_returns[index])

    @staticmethod
    def calculate_var_parametric(returns: list[float], confidence_level: float = 0.95) -> float:
        """Parametric VaR using normal distribution assumption."""
        if not returns:
            return 0.0
        mean = np.mean(returns)
        std = np.std(returns)
        z = -1.645  # Approximate z-score for 95% confidence (one-tailed)
        if confidence_level == 0.99:
            z = -2.326
        elif confidence_level == 0.999:
            z = -3.090
        return abs(mean + z * std)

    @staticmethod
    def calculate_var_monte_carlo(
        returns: list[float],
        confidence_level: float = 0.95,
        time_horizon: int = 1,
        paths: int = 10000,
    ) -> float:
        """Monte Carlo VaR simulation."""
        if not returns:
            return 0.0
        mean = np.mean(returns)
        std = np.std(returns)
        simulated = np.random.normal(mean * time_horizon, std * np.sqrt(time_horizon), paths)
        var = np.percentile(simulated, (1 - confidence_level) * 100)
        return abs(var)

    @staticmethod
    def calculate_expected_shortfall(returns: list[float], confidence_level: float = 0.95) -> float:
        """Expected Shortfall (Conditional VaR)."""
        if not returns:
            return 0.0
        sorted_returns = sorted(returns)
        index = int((1 - confidence_level) * len(sorted_returns))
        tail = sorted_returns[:index] if index > 0 else sorted_returns[:1]
        return abs(np.mean(tail))

    @staticmethod
    def calculate_portfolio_returns(db: Session, portfolio_id: int) -> list[float]:
        """Calculate historical returns for a portfolio based on price history."""
        positions = db.query(Position).filter(Position.portfolio_id == portfolio_id).all()
        if not positions:
            return []

        # Get price history for each symbol
        symbol_returns: dict[str, list[float]] = {}
        for pos in positions:
            prices = PriceService.get_price_history(db, pos.symbol)
            if len(prices) > 1:
                symbol_returns[pos.symbol] = [
                    (prices[i + 1] - prices[i]) / prices[i] for i in range(len(prices) - 1)
                ]

        if not symbol_returns:
            return []

        # Weight by position value
        min_len = min(len(r) for r in symbol_returns.values())
        portfolio_returns = []
        total_weight = Decimal("0")
        weights = {}
        for pos in positions:
            weights[pos.symbol] = float(pos.quantity)  # Simplified: weight by quantity
            total_weight += pos.quantity

        for i in range(min_len):
            daily_return = 0.0
            for symbol, rets in symbol_returns.items():
                weight = float(weights.get(symbol, 0)) / float(total_weight) if total_weight > 0 else 0
                daily_return += rets[i] * weight
            portfolio_returns.append(daily_return)

        return portfolio_returns

    @staticmethod
    def calculate_risk(db: Session, req: RiskCalculationRequest) -> RiskCalculation:
        """Calculate VaR, Expected Shortfall, Monte Carlo for a portfolio."""
        returns = RiskService.calculate_portfolio_returns(db, req.portfolio_id)

        var_hist = RiskService.calculate_var_historical(returns, req.confidence_level)
        var_param = RiskService.calculate_var_parametric(returns, req.confidence_level)
        var_mc = RiskService.calculate_var_monte_carlo(
            returns, req.confidence_level, req.time_horizon_days, req.monte_carlo_paths
        )
        es = RiskService.calculate_expected_shortfall(returns, req.confidence_level)

        calc = RiskCalculation(
            portfolio_id=req.portfolio_id,
            var_historical=Decimal(str(round(var_hist, 4))),
            var_parametric=Decimal(str(round(var_param, 4))),
            var_monte_carlo=Decimal(str(round(var_mc, 4))),
            expected_shortfall=Decimal(str(round(es, 4))),
            confidence_level=Decimal(str(req.confidence_level)),
            time_horizon_days=req.time_horizon_days,
        )
        db.add(calc)
        db.commit()
        db.refresh(calc)
        return calc

    @staticmethod
    def stress_test(db: Session, req: StressTestRequest) -> StressTestResponse:
        """Stress test portfolio under market shock."""
        portfolio = db.query(Portfolio).filter(Portfolio.id == req.portfolio_id).first()
        if not portfolio:
            raise ValueError(f"Portfolio {req.portfolio_id} not found")

        original_value = PortfolioService.get_portfolio_value(db, req.portfolio_id)
        shock = Decimal(str(req.shock_percentage))
        shocked_value = original_value * (1 + shock)
        pnl_impact = shocked_value - original_value

        return StressTestResponse(
            portfolio_id=req.portfolio_id,
            shock_percentage=req.shock_percentage,
            original_value=original_value,
            shocked_value=shocked_value,
            pnl_impact=pnl_impact,
        )

    @staticmethod
    def get_risk_calculations(db: Session, portfolio_id: int) -> List[RiskCalculation]:
        return (
            db.query(RiskCalculation)
            .filter(RiskCalculation.portfolio_id == portfolio_id)
            .order_by(desc(RiskCalculation.calculated_at))
            .all()
        )