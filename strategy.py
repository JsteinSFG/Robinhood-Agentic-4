# Robinhood Autonomous Stock Agent Rewrite Spec

## Purpose

Rewrite `The-Swarm-Corporation/AutoHedge` into a Robinhood-focused autonomous U.S. stock trading agent.

The new agent must trade only U.S.-listed stocks in the user's Robinhood account, screen the full U.S. equity universe for qualifying opportunities, and execute autonomously only when all risk gates pass.

This is not a Solana, crypto, options, futures, margin, short-selling, or leveraged ETF system.

## Operating Mode

- Primary mode: fully autonomous stock execution under hard risk limits.
- Default safe mode for development: paper trading.
- Live mode must be explicitly enabled by configuration.
- Live execution must use a supported, approved Robinhood stock execution connector.
- If no supported Robinhood stock execution connector is available, the system must block live orders and fall back to paper/recommendation mode.
- The agent must never use an unofficial login scraper or credential-sharing workflow for live execution.

## Key User Decisions

- Broker/account: Robinhood stocks only.
- Execution target: fully autonomous execution under risk limits.
- Hard daily loss limit: maximum 5% daily portfolio loss.
- Concentration rule: do not add to any position above 20% of portfolio value unless the trade is explicitly labeled `exceptional conviction`.
- Trade universe: any U.S. stock that passes the model's screens.

## Non-Negotiable Risk Gates

Every candidate order must pass these gates before submission:

1. Daily drawdown gate
   - Block all new opening/add trades if current or projected same-day portfolio loss is greater than or equal to 5%.
   - Estimate projected loss using current P/L plus an adverse move scenario for the proposed order.
   - If broker/account P/L is unavailable, block live trading.

2. Concentration gate
   - Do not add to a position that is already above 20% of portfolio value.
   - Exception: allow only if `exceptional_conviction = true` and the risk manager explains:
     - current position weight,
     - proposed new position weight,
     - one-day adverse move assumption,
     - estimated portfolio drawdown impact,
     - why the incremental risk is justified.

3. Asset-class gate
   - Allow common stocks and approved U.S.-listed ADRs only.
   - Block options, crypto, futures, short selling, margin expansion, leveraged ETFs, inverse ETFs, penny stocks below the configured liquidity threshold, and OTC names unless explicitly allowed later.

4. Liquidity gate
   - Require minimum average daily dollar volume.
   - Require bounded bid/ask spread.
   - Use limit orders by default in live mode.

5. Position-size gate
   - Cap new positions by configured max initial position size.
   - Cap total same-day capital deployment.
   - Cap trade count per day.

6. Kill-switch gate
   - Stop live trading immediately if:
     - broker connection is stale,
     - market data is stale,
     - order status cannot be confirmed,
     - portfolio value cannot be fetched,
     - daily drawdown limit is breached,
     - model output is malformed,
     - risk manager rejects the trade.

## Replace AutoHedge Components

Remove or disable:

- Solana execution.
- Jupiter API dependencies.
- Wallet private key flow.
- Crypto market assumptions.
- Generic "hedge fund" language.
- Any automatic execution path that bypasses the risk manager.

Replace with:

- Robinhood stock broker adapter.
- U.S. equity screener.
- Portfolio and position monitor.
- Risk manager with hard gates.
- Order planner.
- Execution adapter with paper/live modes.
- Audit log for every decision and rejected order.

## Proposed Architecture

### 1. Data Layer

Responsibilities:

- Fetch portfolio value, cash, positions, buying power, and today's realized/unrealized P/L.
- Fetch current U.S. equity quotes.
- Fetch fundamentals, earnings dates, analyst revisions, sector/industry metadata, and market-cap data.
- Fetch historical OHLCV for technical indicators.
- Mark data freshness timestamps.

Required interface:

```python
class MarketDataProvider:
    def get_quote(self, symbol: str) -> Quote: ...
    def get_history(self, symbol: str, lookback_days: int) -> list[Bar]: ...
    def get_fundamentals(self, symbol: str) -> Fundamentals: ...
    def screen_us_stocks(self, filters: ScreenFilters) -> list[str]: ...
```

### 2. Broker Layer

Responsibilities:

- Read Robinhood account state.
- Submit, cancel, and monitor stock orders only when live mode is enabled and the connector is approved.
- Provide paper broker simulation for development.

Required interface:

```python
class BrokerAdapter:
    mode: str  # "paper" or "live"

    def get_account(self) -> AccountState: ...
    def get_positions(self) -> list[Position]: ...
    def get_orders(self) -> list[OrderStatus]: ...
    def place_order(self, order: OrderRequest) -> OrderStatus: ...
    def cancel_order(self, order_id: str) -> OrderStatus: ...
```

Live broker rule:

```python
if broker.mode == "live" and not broker.supports_robinhood_stock_execution:
    raise LiveExecutionBlocked("No approved Robinhood stock execution connector is configured.")
```

### 3. Screening Engine

The agent may consider any U.S. stock that passes model screens.

Default screens:

- Market cap above configured minimum.
- Average daily dollar volume above configured minimum.
- Spread below configured maximum.
- Price above configured minimum.
- Positive or improving earnings/revenue quality, unless strategy explicitly permits turnarounds.
- Technical trend score above threshold.
- Relative strength above threshold.
- Catalyst present or valuation dislocation identified.
- Exclude names with imminent binary risk unless explicitly approved by the strategy.

Output:

```python
class Candidate:
    symbol: str
    company_name: str
    thesis: str
    technical_score: float
    fundamental_score: float
    catalyst_score: float
    liquidity_score: float
    risk_flags: list[str]
```

### 4. Strategy Director

Responsibilities:

- Rank screened candidates.
- Compare candidates against existing holdings.
- Decide whether to buy, add, trim, exit, hold, or do nothing.
- Prefer no trade when edge is unclear.

The director may propose orders but must not submit them.

### 5. Risk Manager

Responsibilities:

- Enforce all non-negotiable risk gates.
- Compute position sizing.
- Compute daily drawdown impact.
- Approve or reject each proposed order.
- Add `exceptional_conviction` review for adds above 20% position weight.

Risk manager output:

```python
class RiskDecision:
    approved: bool
    rejection_reason: str | None
    max_order_value: float
    projected_position_weight: float
    projected_daily_drawdown_pct: float
    exceptional_conviction_required: bool
    exceptional_conviction_passed: bool
```

### 6. Order Planner

Responsibilities:

- Convert approved decisions into concrete stock orders.
- Prefer limit orders.
- Attach time-in-force rules.
- Create cancel/replace logic for stale orders.
- Never create options, crypto, short, margin, or leveraged ETF orders.

Default live order policy:

- Use limit orders.
- Avoid first 5-15 minutes after market open unless configured otherwise.
- Avoid last 5 minutes before close unless risk-reduction order.
- Do not chase gaps beyond configured slippage.

### 7. Execution Engine

Responsibilities:

- Re-check account state immediately before order submission.
- Re-run risk gates using latest quote and account values.
- Submit only approved stock orders.
- Log every submission, rejection, fill, partial fill, cancellation, and error.
- Halt on unknown order status.

### 8. Audit Logger

Every cycle must write a structured log:

```json
{
  "timestamp": "ISO-8601",
  "mode": "paper|live",
  "portfolio_value": 100000,
  "daily_pnl_pct": -1.2,
  "candidates_reviewed": 50,
  "orders_proposed": 3,
  "orders_approved": 1,
  "orders_submitted": 1,
  "orders_rejected": [
    {
      "symbol": "XYZ",
      "reason": "Projected daily drawdown exceeds 5%"
    }
  ]
}
```

## Configuration

Replace `.env.example` with:

```bash
# Model providers
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Runtime
TRADING_MODE=paper  # paper or live
WORKSPACE_DIR=agent_workspace
LOG_LEVEL=INFO

# Broker
BROKER=robinhood
ROBINHOOD_STOCK_EXECUTION_CONNECTOR=

# Risk limits
MAX_DAILY_PORTFOLIO_LOSS_PCT=5
MAX_POSITION_WEIGHT_PCT=20
ALLOW_EXCEPTIONAL_CONVICTION_ADDS=true
MAX_NEW_POSITION_WEIGHT_PCT=5
MAX_DAILY_DEPLOYMENT_PCT=10
MAX_TRADES_PER_DAY=5

# Liquidity and universe
MIN_PRICE=5
MIN_MARKET_CAP=1000000000
MIN_AVG_DAILY_DOLLAR_VOLUME=25000000
MAX_BID_ASK_SPREAD_BPS=30

# Order controls
DEFAULT_ORDER_TYPE=limit
DEFAULT_TIME_IN_FORCE=day
MAX_SLIPPAGE_BPS=25
AVOID_OPEN_MINUTES=10
AVOID_CLOSE_MINUTES=5
```

## CLI Commands

Replace the generic AutoHedge CLI with:

```bash
rh-agent preflight
rh-agent screen
rh-agent review
rh-agent trade-cycle --mode paper
rh-agent trade-cycle --mode live
rh-agent positions
rh-agent orders
rh-agent halt
```

`trade-cycle --mode live` must fail unless:

- `TRADING_MODE=live`,
- approved Robinhood stock execution connector is configured,
- account state is fresh,
- market data is fresh,
- daily loss is below 5%,
- no kill switch is active.

## Agent System Prompt

Use this as the main trading agent instruction:

```text
You are a Robinhood autonomous U.S. stock trading agent.

Your job is to screen U.S.-listed stocks, compare them against current Robinhood holdings, propose trades, run strict risk checks, and submit only approved common-stock orders when live mode is enabled.

You must enforce these hard limits:
- Maximum daily portfolio loss: 5%.
- Do not add to positions above 20% portfolio weight unless exceptional conviction is explicitly documented and risk math passes.
- Stocks only. No options, crypto, futures, short selling, margin expansion, leveraged ETFs, inverse ETFs, or unsupported OTC names.
- Block live trading when broker data, market data, account value, or order status is stale or unavailable.
- Prefer no trade when edge is unclear.

You may consider any U.S. stock that passes the configured model, liquidity, technical, and fundamental screens.

You must never bypass the risk manager. You must never submit orders from malformed model output. You must log every decision and every rejected trade.
```

## Development Milestones

1. Fork or copy AutoHedge into a new repo named `robinhood-stock-agent`.
2. Remove Solana, Jupiter, wallet, and crypto execution code.
3. Add typed domain models for account state, positions, quotes, candidates, risk decisions, and orders.
4. Build paper broker first.
5. Build market data provider and U.S. stock screener.
6. Build deterministic risk manager and tests.
7. Build order planner with stocks-only validation.
8. Add live broker adapter only after confirming a supported Robinhood stock execution path.
9. Add audit logs and kill switch.
10. Run paper trading for at least 30 sessions before enabling live mode.

## Required Tests

- Blocks all live trades when daily loss is greater than or equal to 5%.
- Blocks adds above 20% position weight unless exceptional conviction passes.
- Blocks options, crypto, short, margin, leveraged ETF, inverse ETF, and OTC trades by default.
- Blocks live orders when Robinhood stock connector is missing.
- Blocks live orders when market/account data is stale.
- Uses limit orders by default.
- Logs every rejected trade with a reason.
- Allows no-trade output without error.

## Final Design Principle

The model may generate ideas, but deterministic code must control execution.

No model output should be trusted directly as an order. Every order must be parsed, validated, risk-checked, converted into a constrained order request, rechecked against fresh account data, and logged before submission.
