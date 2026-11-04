-- market-risk-analytics-platform schema (Neon DB)
CREATE TABLE IF NOT EXISTS portfolios (
  id SERIAL PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  description TEXT,
  base_currency VARCHAR(3) DEFAULT 'USD' NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS positions (
  id SERIAL PRIMARY KEY,
  portfolio_id INTEGER NOT NULL REFERENCES portfolios(id),
  symbol VARCHAR(20) NOT NULL,
  quantity NUMERIC(18, 6) NOT NULL,
  average_cost NUMERIC(18, 4) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS price_data (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(20) NOT NULL,
  price NUMERIC(18, 4) NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_calculations (
  id SERIAL PRIMARY KEY,
  portfolio_id INTEGER NOT NULL REFERENCES portfolios(id),
  var_historical NUMERIC(18, 4),
  var_parametric NUMERIC(18, 4),
  var_monte_carlo NUMERIC(18, 4),
  expected_shortfall NUMERIC(18, 4),
  confidence_level NUMERIC(5, 4) DEFAULT 0.95 NOT NULL,
  time_horizon_days INTEGER DEFAULT 1 NOT NULL,
  calculated_at TIMESTAMPTZ DEFAULT NOW()
);