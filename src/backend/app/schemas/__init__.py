from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import datetime
from typing import Optional, List


class PortfolioBase(BaseModel):
    name: str
    description: Optional[str] = None
    base_currency: str = "USD"


class PortfolioCreate(PortfolioBase):
    pass


class PortfolioResponse(PortfolioBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class PositionBase(BaseModel):
    symbol: str
    quantity: Decimal
    average_cost: Decimal


class PositionCreate(PositionBase):
    pass


class PositionResponse(PositionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    created_at: datetime


class PriceDataCreate(BaseModel):
    symbol: str
    price: Decimal


class PriceDataResponse(PriceDataCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime


class RiskCalculationRequest(BaseModel):
    portfolio_id: int
    confidence_level: float = 0.95
    time_horizon_days: int = 1
    monte_carlo_paths: int = 10000


class RiskCalculationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    var_historical: Optional[Decimal]
    var_parametric: Optional[Decimal]
    var_monte_carlo: Optional[Decimal]
    expected_shortfall: Optional[Decimal]
    confidence_level: Decimal
    time_horizon_days: int
    calculated_at: datetime


class StressTestRequest(BaseModel):
    portfolio_id: int
    shock_percentage: float  # e.g. -0.10 for -10% market shock


class StressTestResponse(BaseModel):
    portfolio_id: int
    shock_percentage: float
    original_value: Decimal
    shocked_value: Decimal
    pnl_impact: Decimal


# --- Auth schemas ---

class Token(BaseModel):
    access_token: str
    token_type: str


class AuthLoginRequest(BaseModel):
    account_number: str


class AuthRegisterRequest(BaseModel):
    account_number: str
    account_holder_name: str
    role: str = "viewer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_number: str
    account_holder_name: str
    role: str