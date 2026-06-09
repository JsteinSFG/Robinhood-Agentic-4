import json
import os
import time
from datetime import datetime, timezone

from broker import build_broker
from config import Settings
from market_data import build_market_data_provider
from risk import evaluate_order_risk
from strategy import candidate_to_dict, candidate_to_order, propose_paper_candidate

WORKER_VERSION = "broker-read-risk-strategy-2026-06-09"

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))

TRADING_MODE = os.getenv("TRADING_MODE", "paper")
BROKER = os.getenv("BROKER", "paper")

MAX_DAILY_PORTFOLIO_LOSS_PCT = float(os.getenv("MAX_DAILY_PORTFOLIO_LOSS_PCT", "5"))
MAX_POSITION_WEIGHT_PCT = float(os.getenv("MAX_POSITION_WEIGHT_PCT", "20"))
MAX_NEW_POSITION_WEIGHT_PCT = float(os.getenv("MAX_NEW_POSITION_WEIGHT_PCT", "5"))


def risk_decision_to_dict(decision):
    if decision is None:
        return None

    return {
        "approved": decision.approved,
        "rejection_reason": decision.rejection_reason,
        "max_order_value": decision.max_order_value,
        "projected_position_weight_pct": decision.projected_position_weight_pct,
        "projected_daily_drawdown_pct": decision.projected_daily_drawdown_pct,
        "exceptional_conviction_required": decision.exceptional_conviction_required,
        "exceptional_conviction_passed": decision.exceptional_conviction_passed,
    }


def account_to_dict(account):
    return {
        "portfolio_value": account.portfolio_value,
        "cash": account.cash,
        "daily_pnl": account.daily_pnl,
        "daily_pnl_pct": account.daily_pnl_pct,
        "buying_power": account.buying_power,
        "as_of": account.as_of,
    }


def positions_to_dict(positions):
    return [
        {
            "symbol": position.symbol,
            "quantity": position.quantity,
            "market_value": position.market_value,
            "average_cost": position.average_cost,
            "current_price": position.current_price,
        }
        for position in positions
    ]


def order_to_dict(order):
    if order is None:
        return None

    return {
        "symbol": order.symbol,
        "side": order.side.value,
        "quantity": order.quantity,
        "limit_price": order.limit_price,
        "reason": order.reason,
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

    settings = Settings()
    broker = build_broker(settings)
    market_data = build_market_data_provider()

    account = broker.get_account()
    positions = broker.get_positions()

    candidate = propose_paper_candidate(account, positions, market_data)
    proposed_order = candidate_to_order(candidate)
    quote = market_data.get_quote(candidate.symbol) if candidate else market_data.get_quote("MSFT")

    risk_decision = None
    if proposed_order:
        risk_decision = evaluate_order_risk(
            account,
            positions,
            proposed_order,
            exceptional_conviction=candidate.exceptional_conviction if candidate else False,
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
        "status": "paper_broker_read_ok",
        "account": account_to_dict(account),
        "positions": positions_to_dict(positions),
        "market_quote": quote_to_dict(quote),
        "strategy_candidate": candidate_to_dict(candidate),
        "paper_order_proposed": order_to_dict(proposed_order),
        "risk_decision": risk_decision_to_dict(risk_decision),
        "orders_submitted": 0,
        "message": "Worker is reading the paper broker, running strategy, and checking risk. No orders are submitted.",
    }

    print(
        f"BROKER READ | cash={account.cash:.2f} | "
        f"portfolio_value={account.portfolio_value:.2f} | "
        f"positions={len(positions)}",
        flush=True,
    )

    print(
        f"STRATEGY | candidate={candidate.symbol if candidate else 'none'} | "
        f"action={candidate.action if candidate else 'none'} | "
        f"orders_submitted=0",
        flush=True,
    )

    if risk_decision:
        print(
            f"RISK CHECK | worker_version={WORKER_VERSION} | "
            f"approved={risk_decision.approved} | "
            f"orders_submitted=0 | "
            f"projected_drawdown={risk_decision.projected_daily_drawdown_pct:.2f}% | "
            f"projected_weight={risk_decision.projected_position_weight_pct:.2f}%",
            flush=True,
        )
    else:
        print(
            f"RISK CHECK | worker_version={WORKER_VERSION} | "
            "no_order_proposed=True | orders_submitted=0",
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
