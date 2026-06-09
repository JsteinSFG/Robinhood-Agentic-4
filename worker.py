import json
import os
import time
from datetime import datetime, timezone

WORKER_VERSION = "daily-trade-limit-2026-06-09"

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))

TRADING_MODE = os.getenv("TRADING_MODE", "paper")
BROKER = os.getenv("BROKER", "paper")

MAX_DAILY_PORTFOLIO_LOSS_PCT = float(os.getenv("MAX_DAILY_PORTFOLIO_LOSS_PCT", "5"))
MAX_POSITION_WEIGHT_PCT = float(os.getenv("MAX_POSITION_WEIGHT_PCT", "20"))
MAX_NEW_POSITION_WEIGHT_PCT = float(os.getenv("MAX_NEW_POSITION_WEIGHT_PCT", "5"))
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "2"))


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
    from broker import build_broker
    from config import Settings
    from market_data import build_market_data_provider
    from risk import evaluate_order_risk
    from strategy import candidate_to_dict, candidate_to_order, propose_paper_candidate

    settings = Settings()
    broker = build_broker(settings)
    market_data = build_market_data_provider()

    account = broker.get_account()
    positions = broker.get_positions()
    trades_today = broker.get_trades_today()

    candidate = propose_paper_candidate(account, positions, market_data)
    proposed_order = candidate_to_order(candidate)
    quote = market_data.get_quote(candidate.symbol) if candidate else market_data.get_quote("MSFT")

    risk_decision = None
    order_status = None
    orders_submitted = 0
    execution_block_reason = None

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

        if trades_today >= MAX_TRADES_PER_DAY:
            execution_block_reason = "Daily trade limit reached."

        elif TRADING_MODE != "paper":
            execution_block_reason = "Live execution is blocked."

        elif risk_decision.approved:
            order_status = broker.place_order(proposed_order)
            orders_submitted = 1 if order_status.status == "filled" else 0

    audit_event = {
        "timestamp": now_iso(),
        "worker_version": WORKER_VERSION,
        "service": "Robinhood autonomous stock agent",
        "mode": TRADING_MODE,
        "broker": BROKER,
        "status": "paper_execution_cycle_ok",
        "account_before": dict_from_object(account),
        "positions_before": [dict_from_object(position) for position in positions],
        "trades_today": trades_today,
        "max_trades_per_day": MAX_TRADES_PER_DAY,
        "market_quote": dict_from_object(quote),
        "strategy_candidate": candidate_to_dict(candidate),
        "paper_order_proposed": dict_from_object(proposed_order),
        "risk_decision": dict_from_object(risk_decision),
        "execution_block_reason": execution_block_reason,
        "order_status": dict_from_object(order_status),
        "orders_submitted": orders_submitted,
        "live_execution_enabled": TRADING_MODE == "live",
        "message": "Paper execution is enabled with a daily trade limit. Live execution remains blocked.",
    }

    print(
        f"BROKER READ | cash={account.cash:.2f} | "
        f"portfolio_value={account.portfolio_value:.2f} | "
        f"positions={len(positions)} | "
        f"trades_today={trades_today}/{MAX_TRADES_PER_DAY}",
        flush=True,
    )

    print(
        f"STRATEGY | candidate={candidate.symbol if candidate else 'none'} | "
        f"action={candidate.action if candidate else 'none'}",
        flush=True,
    )

    if risk_decision:
        print(
            f"RISK CHECK | worker_version={WORKER_VERSION} | "
            f"approved={risk_decision.approved} | "
            f"projected_drawdown={risk_decision.projected_daily_drawdown_pct:.2f}% | "
            f"projected_weight={risk_decision.projected_position_weight_pct:.2f}%",
            flush=True,
        )
    else:
        print(
            f"RISK CHECK | worker_version={WORKER_VERSION} | "
            "no_order_proposed=True",
            flush=True,
        )

    if execution_block_reason:
        print(f"EXECUTION BLOCKED | reason={execution_block_reason}", flush=True)

    if order_status:
        print(
            f"PAPER ORDER | status={order_status.status} | "
            f"symbol={order_status.symbol} | "
            f"side={order_status.side.value} | "
            f"quantity={order_status.quantity} | "
            f"limit_price={order_status.limit_price}",
            flush=True,
        )
    else:
        print("PAPER ORDER | status=none | orders_submitted=0", flush=True)

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
