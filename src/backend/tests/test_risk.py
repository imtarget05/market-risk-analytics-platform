from fastapi.testclient import TestClient
import os
os.environ["DATABASE_URL"] = "sqlite:///./test_risk.db"
os.environ["TESTING"] = "true"

from app.main import app
from app.db.session import SessionLocal, engine, Base
from app.models import Portfolio, Position, PriceData, RiskCalculation
from decimal import Decimal


def setup_module(module):
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)


import time
_counter = 0


def _unique(prefix: str) -> str:
    global _counter
    _counter += 1
    return f"{prefix}-{int(time.time() * 1000000)}-{_counter}"


def _auth_headers(client: TestClient) -> dict:
    acc_num = _unique("ACC-AUTH")
    client.post("/api/v1/auth/register", json={
        "account_number": acc_num,
        "account_holder_name": "Auth User",
        "role": "analyst",
    })
    resp = client.post("/api/v1/auth/login", json={"account_number": acc_num})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_portfolio_and_position():
    client = TestClient(app)
    db = SessionLocal()
    headers = _auth_headers(client)

    resp = client.post("/api/v1/portfolios", json={
        "name": "Test Portfolio",
        "description": "Test portfolio for risk calculations",
        "base_currency": "USD",
    }, headers=headers)
    assert resp.status_code == 201
    portfolio = resp.json()
    assert portfolio["name"] == "Test Portfolio"

    resp = client.post(f"/api/v1/portfolios/{portfolio['id']}/positions", json={
        "symbol": "AAPL",
        "quantity": "100",
        "average_cost": "150.00",
    }, headers=headers)
    assert resp.status_code == 201
    position = resp.json()
    assert position["symbol"] == "AAPL"
    assert position["quantity"] == "100.000000"

    resp = client.post("/api/v1/prices", json={
        "symbol": "AAPL",
        "price": "160.00",
    }, headers=headers)
    assert resp.status_code == 201

    resp = client.get(f"/api/v1/portfolios/{portfolio['id']}/value", headers=headers)
    assert resp.status_code == 200
    assert Decimal(resp.json()["value"]) == Decimal("16000.0000")

    db.close()


def test_list_portfolios():
    client = TestClient(app)
    db = SessionLocal()
    headers = _auth_headers(client)

    resp = client.get("/api/v1/portfolios", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    db.close()


def test_calculate_risk():
    client = TestClient(app)
    db = SessionLocal()
    headers = _auth_headers(client)

    resp = client.post("/api/v1/portfolios", json={
        "name": "Risk Test Portfolio",
    }, headers=headers)
    assert resp.status_code == 201
    portfolio = resp.json()

    resp = client.post(f"/api/v1/portfolios/{portfolio['id']}/positions", json={
        "symbol": "MSFT",
        "quantity": "50",
        "average_cost": "300.00",
    }, headers=headers)
    assert resp.status_code == 201

    for price in ["290", "295", "300", "305", "310", "305", "300", "295", "290", "285"]:
        client.post("/api/v1/prices", json={"symbol": "MSFT", "price": price}, headers=headers)

    resp = client.post("/api/v1/risk/calculate", json={
        "portfolio_id": portfolio["id"],
        "confidence_level": 0.95,
        "time_horizon_days": 1,
        "monte_carlo_paths": 1000,
    }, headers=headers)
    assert resp.status_code == 200
    result = resp.json()
    assert "var_historical" in result
    assert "var_parametric" in result
    assert "var_monte_carlo" in result
    assert "expected_shortfall" in result

    db.close()


def test_stress_test():
    client = TestClient(app)
    db = SessionLocal()
    headers = _auth_headers(client)

    resp = client.post("/api/v1/portfolios", json={
        "name": "Stress Test Portfolio",
    }, headers=headers)
    assert resp.status_code == 201
    portfolio = resp.json()

    resp = client.post(f"/api/v1/portfolios/{portfolio['id']}/positions", json={
        "symbol": "GOOGL",
        "quantity": "10",
        "average_cost": "2500.00",
    }, headers=headers)
    assert resp.status_code == 201

    resp = client.post("/api/v1/prices", json={"symbol": "GOOGL", "price": "2600.00"}, headers=headers)
    assert resp.status_code == 201

    resp = client.post("/api/v1/risk/stress-test", json={
        "portfolio_id": portfolio["id"],
        "shock_percentage": -0.10,
    }, headers=headers)
    assert resp.status_code == 200
    result = resp.json()
    assert result["shock_percentage"] == -0.10
    assert Decimal(result["pnl_impact"]) < Decimal("0")

    db.close()
