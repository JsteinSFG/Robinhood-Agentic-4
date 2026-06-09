import json
import os
import time
from datetime import datetime, timezone

WORKER_VERSION = "crash-safe-broker-read-2026-06-09"

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))

TRADING_MODE = os.getenv("TRADING_MODE", "paper")
BROKER = os.getenv("BROKER", "paper")

MAX_DAILY_PORTFOLIO_LOSS_PCT = float(os.getenv("MAX_DAILY_PORTFOLIO_LOSS_PCT", "5"))
MAX_POSITION_WEIGHT_PCT = float(os.getenv("MAX_POSITION_WEIGHT_PCT", "20"))
MAX_NEW_POSITION_WEIGHT_PCT = float(os.getenv("MAX_NEW_POSITION_WEIGHT_PCT", "5"))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def dict_from_object(obj):
    if obj is None:
        return None

    output = {}
    for key, value in obj.__dict__.items():
        if hasattr(value, "value"):
            output[key] = value.value
        else:
            output[key] = value
    return output


def run_agent_cycle():
    broker_error = None

    from main import AccountState, OrderRequest, OrderSide, Position
    from market_data import build_market_data_provider
    from risk import evaluate_order_risk
    from strategy import candidate_to_dict, candidate_to_order, propose_paper_candidate

    market_data = build_market_data_provider()

    try:
        from broker import build_broker
        from config import Settings

        settings = Settings()
        broker = build_broker(settings)
        account = broker.get_account()
        positions = broker.get_positions()
        broker_status = "paper_broker_read_ok"
    except Exception as exc:
        broker_error = str(exc)
        broker_status = "paper_broker_fallback"

        account = AccountState(
            portfolio_value=10000,
            cash=2000,
            daily_pnl=0,
            daily_pnl_pct=0,
            buying_power=2000,
        )

        nvda_quote = market_data.get_quote("NVDA")
        positions = [
            Position(
                symbol="NVDA",
                quantity=10,
                market_value=round(10 * nvda_quote.price, 2),
                average_cost=150,
                current_price=nvda_quote.price,
            )
        ]

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
        "timestamp": now_iso(),
        "worker_version": WORKER_VERSION,
        "service": "Robinhood autonomous stock agent",
        "mode": TRADING_MODE,
        "broker": BROKER,
        "status": broker_status,
        "broker_error": broker_error,
        "account": dict_from_object(account),
        "positions": [dict_from_object(position) for position in positions],
        "market_quote": dict_from_object(quote),
        "strategy_candidate": candidate_to_dict(candidate),
        "paper_order_proposed": dict_from_object(proposed_order),
        "risk_decision": dict_from_object(risk_decision),
        "orders_submitted": 0,
        "message": "Worker is alive. Broker read is attempted; fallback paper data is used if broker/config crashes.",
    }

    print(
        f"BROKER READ | status={broker_status} | "
        f"cash={account.cash:.2f} | "
        f"portfolio_value={account.portfolio_value:.2f} | "
        f"positions={len(positions)}",
        flush=True,
    )

    if broker_error:
        print(f"BROKER ERROR | {broker_error}", flush=True)

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
            print(
                json.dumps(
                    {
                        "timestamp": now_iso(),
                        "worker_version": WORKER_VERSION,
                        "status": "cycle_error",
                        "error": str(exc),
                    }
                ),
                flush=True,
            )

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
