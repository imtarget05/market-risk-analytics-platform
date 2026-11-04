import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { neon } from '@neondatabase/serverless';

const app = new Hono();
app.use('*', cors());

const sql = neon(process.env.DATABASE_URL!);

async function initDb() {
  await sql`
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
  `;
}
initDb().catch(console.error);

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
}
function err(message: string, status = 400) {
  return json({ detail: message }, status);
}

app.get('/health', (c) => json({ status: 'healthy', service: 'market-risk-analytics-platform' }));

app.post('/api/v1/portfolios', async (c) => {
  const body = await c.req.json<{ name: string; description?: string; base_currency?: string }>();
  const [p] = await sql`INSERT INTO portfolios (name, description, base_currency) VALUES (${body.name}, ${body.description || null}, ${body.base_currency || 'USD'}) RETURNING *`;
  return json(p, 201);
});

app.get('/api/v1/portfolios', async (c) => {
  const ps = await sql`SELECT * FROM portfolios ORDER BY created_at DESC`;
  return json(ps);
});

app.get('/api/v1/portfolios/:id', async (c) => {
  const id = Number(c.req.param('id'));
  const [p] = await sql`SELECT * FROM portfolios WHERE id = ${id}`;
  if (!p) return err('Portfolio not found', 404);
  return json(p);
});

app.get('/api/v1/portfolios/:id/value', async (c) => {
  const id = Number(c.req.param('id'));
  const positions = await sql`SELECT * FROM positions WHERE portfolio_id = ${id}`;
  let total = 0;
  for (const pos of positions) {
    const [latest] = await sql`SELECT price FROM price_data WHERE symbol = ${pos.symbol} ORDER BY timestamp DESC LIMIT 1`;
    if (latest) total += Number(pos.quantity) * Number(latest.price);
  }
  return json({ portfolio_id: id, value: total.toFixed(4) });
});

app.post('/api/v1/portfolios/:id/positions', async (c) => {
  const portfolioId = Number(c.req.param('id'));
  const body = await c.req.json<{ symbol: string; quantity: string; average_cost: string }>();
  const [pos] = await sql`INSERT INTO positions (portfolio_id, symbol, quantity, average_cost) VALUES (${portfolioId}, ${body.symbol}, ${body.quantity}, ${body.average_cost}) RETURNING *`;
  return json(pos, 201);
});

app.get('/api/v1/portfolios/:id/positions', async (c) => {
  const id = Number(c.req.param('id'));
  const ps = await sql`SELECT * FROM positions WHERE portfolio_id = ${id}`;
  return json(ps);
});

app.post('/api/v1/prices', async (c) => {
  const body = await c.req.json<{ symbol: string; price: string }>();
  const [p] = await sql`INSERT INTO price_data (symbol, price) VALUES (${body.symbol}, ${body.price}) RETURNING *`;
  return json(p, 201);
});

app.get('/api/v1/prices/:symbol', async (c) => {
  const symbol = c.req.param('symbol');
  const limit = Number(c.req.query('limit') || 252);
  const prices = await sql`SELECT price FROM price_data WHERE symbol = ${symbol} ORDER BY timestamp DESC LIMIT ${limit}`;
  return json({ symbol, prices: prices.map(p => p.price).reverse() });
});

function varHistorical(returns: number[], cl = 0.95) {
  if (!returns.length) return 0;
  const s = [...returns].sort((a, b) => a - b);
  const idx = Math.max(0, Math.min(Math.floor((1 - cl) * s.length), s.length - 1));
  return Math.abs(s[idx]);
}
function varParametric(returns: number[], cl = 0.95) {
  if (!returns.length) return 0;
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
  const std = Math.sqrt(returns.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / returns.length);
  const z = cl === 0.99 ? -2.326 : cl === 0.999 ? -3.090 : -1.645;
  return Math.abs(mean + z * std);
}
function varMonteCarlo(returns: number[], cl = 0.95, horizon = 1, paths = 10000) {
  if (!returns.length) return 0;
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
  const std = Math.sqrt(returns.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / returns.length);
  const sim: number[] = [];
  for (let i = 0; i < paths; i++) sim.push(mean * horizon + std * Math.sqrt(horizon) * (Math.random() - 0.5) * 2);
  sim.sort((a, b) => a - b);
  return Math.abs(sim[Math.floor((1 - cl) * paths)]);
}
function expectedShortfall(returns: number[], cl = 0.95) {
  if (!returns.length) return 0;
  const s = [...returns].sort((a, b) => a - b);
  const idx = Math.max(0, Math.floor((1 - cl) * s.length));
  const tail = s.slice(0, Math.max(1, idx));
  return Math.abs(tail.reduce((a, b) => a + b, 0) / tail.length);
}

app.post('/api/v1/risk/calculate', async (c) => {
  const body = await c.req.json<{ portfolio_id: number; confidence_level?: number; time_horizon_days?: number; monte_carlo_paths?: number }>();
  const portfolioId = body.portfolio_id;
  const [p] = await sql`SELECT * FROM portfolios WHERE id = ${portfolioId}`;
  if (!p) return err('Portfolio not found', 404);

  const positions = await sql`SELECT * FROM positions WHERE portfolio_id = ${portfolioId}`;
  const symbolReturns: Record<string, number[]> = {};
  for (const pos of positions) {
    const rows = await sql`SELECT price FROM price_data WHERE symbol = ${pos.symbol} ORDER BY timestamp ASC`;
    const prices = rows.map(r => Number(r.price));
    symbolReturns[pos.symbol] = prices.slice(1).map((p, i) => (p - prices[i]) / prices[i]);
  }
  const minLen = Math.min(...Object.values(symbolReturns).map(r => r.length));
  let portfolioReturns: number[] = [];
  if (minLen > 0) {
    const totalQty = positions.reduce((sum, pos) => sum + Number(pos.quantity), 0);
    for (let i = 0; i < minLen; i++) {
      let dr = 0;
      for (const pos of positions) {
        const w = Number(pos.quantity) / totalQty;
        dr += symbolReturns[pos.symbol][i] * w;
      }
      portfolioReturns.push(dr);
    }
  }

  const cl = body.confidence_level ?? 0.95;
  const horizon = body.time_horizon_days ?? 1;
  const paths = body.monte_carlo_paths ?? 10000;

  const vh = varHistorical(portfolioReturns, cl);
  const vp = varParametric(portfolioReturns, cl);
  const vm = varMonteCarlo(portfolioReturns, cl, horizon, paths);
  const es = expectedShortfall(portfolioReturns, cl);

  const [calc] = await sql`
    INSERT INTO risk_calculations (portfolio_id, var_historical, var_parametric, var_monte_carlo, expected_shortfall, confidence_level, time_horizon_days)
    VALUES (${portfolioId}, ${vh}, ${vp}, ${vm}, ${es}, ${cl}, ${horizon})
    RETURNING *
  `;
  return json(calc);
});

app.get('/api/v1/risk/portfolios/:id/calculations', async (c) => {
  const id = Number(c.req.param('id'));
  const cs = await sql`SELECT * FROM risk_calculations WHERE portfolio_id = ${id} ORDER BY calculated_at DESC`;
  return json(cs);
});

app.post('/api/v1/risk/stress-test', async (c) => {
  const body = await c.req.json<{ portfolio_id: number; shock_percentage: number }>();
  const id = body.portfolio_id;
  const shock = body.shock_percentage;
  const [p] = await sql`SELECT * FROM portfolios WHERE id = ${id}`;
  if (!p) return err('Portfolio not found', 404);

  const positions = await sql`SELECT * FROM positions WHERE portfolio_id = ${id}`;
  let original = 0;
  for (const pos of positions) {
    const [latest] = await sql`SELECT price FROM price_data WHERE symbol = ${pos.symbol} ORDER BY timestamp DESC LIMIT 1`;
    if (latest) original += Number(pos.quantity) * Number(latest.price);
  }
  const shocked = original * (1 + shock);
  const pnl = shocked - original;

  return json({ portfolio_id: id, shock_percentage: shock, original_value: original.toFixed(4), shocked_value: shocked.toFixed(4), pnl_impact: pnl.toFixed(4) });
});

export default app;