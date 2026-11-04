from app.api.v1.auth import router as auth_router
from app.auth import create_access_token, get_current_user, require_role
from app.core.config import settings
from app.db.session import get_db
from app.middleware.rate_limit import RateLimitMiddleware
from app.models import Account, Portfolio, Position, PriceData, RiskCalculation
from app.schemas import (
    AuthLoginRequest,
    AuthRegisterRequest,
    PortfolioCreate,
    PortfolioResponse,
    PositionCreate,
    PositionResponse,
    PriceDataCreate,
    PriceDataResponse,
    RiskCalculationRequest,
    RiskCalculationResponse,
    StressTestRequest,
    StressTestResponse,
    Token,
    UserResponse,
)
from app.services import PortfolioService, PriceService, RiskService
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

app = FastAPI(
    title="Market Risk Analytics Platform",
    description=(
        "Portfolio risk analytics with VaR, Expected Shortfall, "
        "Monte Carlo simulation and stress-testing dashboards."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware, calls=100, period=60)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "market-risk-analytics-platform"}


@app.get("/api/v1/users/me", response_model=UserResponse)
def get_current_user_info(current_user: Account = Depends(get_current_user)):
    return current_user


# --- Portfolios ---

@app.post("/api/v1/portfolios", response_model=PortfolioResponse, status_code=201)
def create_portfolio(
    portfolio_in: PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_role("analyst")),
):
    portfolio = PortfolioService.create_portfolio(
        db=db,
        name=portfolio_in.name,
        description=portfolio_in.description,
        base_currency=portfolio_in.base_currency,
    )
    return portfolio


@app.get("/api/v1/portfolios", response_model=list[PortfolioResponse])
def list_portfolios(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    portfolios = db.query(Portfolio).offset(offset).limit(limit).all()
    return portfolios


@app.get("/api/v1/portfolios/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    portfolio = PortfolioService.get_portfolio(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@app.get("/api/v1/portfolios/{portfolio_id}/value")
def get_portfolio_value(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    portfolio = PortfolioService.get_portfolio(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    value = PortfolioService.get_portfolio_value(db, portfolio_id)
    return {"portfolio_id": portfolio_id, "value": str(value)}


# --- Positions ---

@app.post(
    "/api/v1/portfolios/{portfolio_id}/positions",
    response_model=PositionResponse,
    status_code=201,
)
def add_position(
    portfolio_id: int,
    position_in: PositionCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_role("analyst")),
):
    portfolio = PortfolioService.get_portfolio(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    position = PortfolioService.add_position(
        db=db,
        portfolio_id=portfolio_id,
        symbol=position_in.symbol,
        quantity=position_in.quantity,
        average_cost=position_in.average_cost,
    )
    return position


@app.get("/api/v1/portfolios/{portfolio_id}/positions", response_model=list[PositionResponse])
def list_positions(
    portfolio_id: int,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    positions = (
        db.query(Position)
        .filter(Position.portfolio_id == portfolio_id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return positions


# --- Price Data ---

@app.post("/api/v1/prices", response_model=PriceDataResponse, status_code=201)
def add_price(
    price_in: PriceDataCreate,
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_role("analyst")),
):
    price = PriceService.add_price(db=db, symbol=price_in.symbol, price=price_in.price)
    return price


@app.get("/api/v1/prices/{symbol}")
def get_price_history(
    symbol: str,
    limit: int = Query(default=252, le=1000),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    prices = PriceService.get_price_history(db, symbol, limit)
    return {"symbol": symbol, "prices": prices}


# --- Risk Calculations ---

@app.post("/api/v1/risk/calculate", response_model=RiskCalculationResponse)
def calculate_risk(
    req: RiskCalculationRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_role("analyst")),
):
    calc = RiskService.calculate_risk(db=db, req=req)
    return calc


@app.get("/api/v1/risk/portfolios/{portfolio_id}/calculations", response_model=list[RiskCalculationResponse])
def get_risk_calculations(
    portfolio_id: int,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    calculations = (
        db.query(RiskCalculation)
        .filter(RiskCalculation.portfolio_id == portfolio_id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return calculations


# --- Stress Testing ---

@app.post("/api/v1/risk/stress-test", response_model=StressTestResponse)
def stress_test(
    req: StressTestRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_role("analyst")),
):
    result = RiskService.stress_test(db=db, req=req)
    return result
