# Market Risk Analytics Platform

Portfolio risk analytics with VaR, Expected Shortfall, Monte Carlo simulation and stress-testing dashboards.

## Features

- **Portfolio management**: Create portfolios, add positions (symbol, quantity, average cost)
- **Price data**: Import and store historical price data for symbols
- **VaR calculations**:
  - Historical simulation VaR
  - Parametric VaR (normal distribution)
  - Monte Carlo VaR simulation
- **Expected Shortfall** (Conditional VaR)
- **Stress testing**: Apply market shock scenarios and measure P&L impact
- **Risk calculation history**: Store and retrieve past risk calculations

## Tech Stack

- Python 3.11 + FastAPI
- PostgreSQL 16
- NumPy, Pandas, SciPy for numerical calculations
- SQLAlchemy 2.0
- Pytest

## Run Locally

```bash
# Backend
pip install -r requirements.txt  # or pip install -e .
uvicorn src.backend.app.main:app --reload

# Or with Docker
docker-compose up

# Run tests
pytest src/backend/tests -v
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/portfolios` | Create portfolio |
| GET | `/api/v1/portfolios` | List portfolios |
| GET | `/api/v1/portfolios/{id}` | Get portfolio |
| GET | `/api/v1/portfolios/{id}/value` | Get portfolio value |
| POST | `/api/v1/portfolios/{id}/positions` | Add position |
| GET | `/api/v1/portfolios/{id}/positions` | List positions |
| POST | `/api/v1/prices` | Add price data |
| GET | `/api/v1/prices/{symbol}` | Get price history |
| POST | `/api/v1/risk/calculate` | Calculate VaR/ES |
| GET | `/api/v1/risk/portfolios/{id}/calculations` | Get risk calculations |
| POST | `/api/v1/risk/stress-test` | Stress test portfolio |

## Architecture Decisions

See `docs/ADR-0001.md` for architecture and methodology decisions.