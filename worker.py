from strategy import candidate_to_dict, candidate_to_order, propose_paper_candidate
import json
import os
import time
from datetime import datetime, timezone

from main import AccountState, OrderRequest, OrderSide, Position
from market_data import build_market_data_provider
from risk import evaluate_order_risk

WORKER_VERSION = "market-data-risk-wired-2026-06-09"

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))

TRADING_MODE = os.getenv("TRADING_MODE", "paper")
BROKER = os.getenv("BROKER", "paper")

MAX_DAILY_PORTFOLIO_LOSS_PCT = float(os.getenv("MAX_DAILY_PORTFOLIO_LOSS_PCT", "5"))
MAX_POSITION_WEIGHT_PCT = float(os.getenv("MAX_POSITION_WEIGHT_PCT", "20"))
MAX_NEW_POSITION_WEIGHT_PCT = float(os.getenv("MAX_NEW_POSITION_WEIGHT_PCT", "5"))

STOCKS_ONLY = os.getenv("STOCKS_ONLY", "true").lower() == "true"
ALLOW_OPTIONS = os.getenv("ALLOW_OPTIONS", "false").lower() == "true"
ALLOW_CRYPTO = os.getenv("ALLOW_CRYPTO", "false").lower() == "true"
ALLOW_MARGIN = os.getenv("ALLOW_MARGIN", "false").lower() == "true"
ALLOW_SHORTS = os.getenv("ALLOW_SHORTS", "false").lower() == "true"


def build_paper_account():
    return AccountState(
        portfolio_value=10000,
        cash=2000,
        daily_pnl=0,
        daily_pnl_pct=0,
        buying_power=2000,
    )


def build_paper_positions():
    nvda_quote = build_market_data_provider().get_quote("NVDA")

    return [
        Position(
            symbol="NVDA",
            quantity=10,
            market_value=round(10 * nvda_quote.price, 2),
            average_cost=150,
            current_price=nvda_quote.price,
        )
    ]


def build_paper_order(market_data):
    quote = market_data.get_quote("MSFT")

    return OrderRequest(
        symbol="MSFT",
        side=OrderSide.BUY,
        quantity=1,
        limit_price=quote.ask,
        reason="Paper-mode market data and risk integration test.",
    ), quote


def risk_decision_to_dict(decision):
    return {
        "approved": decision.approved,
        "rejection_reason": decision.rejection_reason,
        "max_order_value": decision.max_order_value,
        "projected_position_weight_pct": decision.projected_position_weight_pct,
        "projected_daily_drawdown_pct": decision.projected_daily_drawdown_pct,
        "exceptional_conviction_required": decision.exceptional_conviction_required,
        "exceptional_conviction_passed": decision.exceptional_conviction_passed,
    }


def quote_to_dict(quote):
    return {
        "symbol": quote.symbol,
        "price": quote.price,
        "bid": quote.bid,
        "ask": quote.ask,
        "as_of": quote.as_of,
        "source": quote.source,
    }


def run_agent_cycle():
    now = datetime.now(timezone.utc).isoformat()

    market_data = build_market_data_provider()
    account = build_paper_account()
    positions = build_paper_positions()
    proposed_order, quote = build_paper_order(market_data)

    risk_decision = evaluate_order_risk(
        account,
        positions,
        proposed_order,
        max_daily_loss_pct=MAX_DAILY_PORTFOLIO_LOSS_PCT,
        max_position_weight_pct=MAX_POSITION_WEIGHT_PCT,
        max_new_position_weight_pct=MAX_NEW_POSITION_WEIGHT_PCT,
    )

    audit_event = {
        "timestamp": now,
        "worker_version": WORKER_VERSION,
        "service": "Robinhood autonomous stock agent",
        "mode": TRADING_MODE,
        "broker": BROKER,
        "status": "paper_cycle_ok",
        "market_quote": quote_to_dict(quote),
        "risk_limits": {
            "max_daily_portfolio_loss_pct": MAX_DAILY_PORTFOLIO_LOSS_PCT,
            "max_position_weight_pct": MAX_POSITION_WEIGHT_PCT,
            "max_new_position_weight_pct": MAX_NEW_POSITION_WEIGHT_PCT,
        },
        "asset_class_rules": {
            "stocks_only": STOCKS_ONLY,
            "allow_options": ALLOW_OPTIONS,
            "allow_crypto": ALLOW_CRYPTO,
            "allow_margin": ALLOW_MARGIN,
            "allow_shorts": ALLOW_SHORTS,
        },
        "paper_account": {
            "portfolio_value": account.portfolio_value,
            "daily_pnl_pct": account.daily_pnl_pct,
            "buying_power": account.buying_power,
        },
        "paper_positions": [
            {
                "symbol": position.symbol,
                "quantity": position.quantity,
                "market_value": position.market_value,
                "average_cost": position.average_cost,
                "current_price": position.current_price,
            }
            for position in positions
        ],
        "paper_order_proposed": {
            "symbol": proposed_order.symbol,
            "side": proposed_order.side.value,
            "quantity": proposed_order.quantity,
            "limit_price": proposed_order.limit_price,
            "reason": proposed_order.reason,
        },
        "risk_decision": risk_decision_to_dict(risk_decision),
        "orders_submitted": 0,
        "live_execution_enabled": TRADING_MODE == "live",
        "message": "Worker is alive, market_data.py is wired in, and risk.py is checking the paper order. No live orders are submitted.",
    }

    if TRADING_MODE == "live":
        audit_event["status"] = "live_blocked"
        audit_event["orders_submitted"] = 0
        audit_event["message"] = (
            "Live mode is blocked until an approved Robinhood stock execution connector, "
            "fresh account data, fresh market data, and deterministic risk gates are implemented."
        )

    print(
        f"MARKET DATA | symbol={quote.symbol} | price={quote.price} | "
        f"bid={quote.bid} | ask={quote.ask} | source={quote.source}",
        flush=True,
    )

    print(
        f"RISK CHECK | worker_version={WORKER_VERSION} | "
        f"approved={risk_decision.approved} | "
        f"orders_submitted=0 | "
        f"projected_drawdown={risk_decision.projected_daily_drawdown_pct:.2f}% | "
        f"projected_weight={risk_decision.projected_position_weight_pct:.2f}%",
        flush=True,
    )

    print(json.dumps(audit_event), flush=True)


def main():
    print(f"Starting Robinhood 24/7 worker | version={WORKER_VERSION}", flush=True)

    while True:
        try:
            run_agent_cycle()
        except Exception as exc:
            error_event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "worker_version": WORKER_VERSION,
                "status": "cycle_error",
                "error": str(exc),
            }
            print(json.dumps(error_event), flush=True)

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
