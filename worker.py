import json
import os
import time
from datetime import datetime, timezone

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


def run_agent_cycle():
    now = datetime.now(timezone.utc).isoformat()

    audit_event = {
        "timestamp": now,
        "service": "Robinhood autonomous stock agent",
        "mode": TRADING_MODE,
        "broker": BROKER,
        "status": "paper_cycle_ok",
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
        "orders_submitted": 0,
        "live_execution_enabled": TRADING_MODE == "live",
        "message": "Worker is alive. Real portfolio, market data, strategy, and risk checks are not wired in yet.",
    }

    if TRADING_MODE == "live":
        audit_event["status"] = "live_blocked"
        audit_event["message"] = (
            "Live mode is blocked until an approved Robinhood stock execution connector, "
            "fresh account data, fresh market data, and deterministic risk gates are implemented."
        )

    print(json.dumps(audit_event), flush=True)


def main():
    print("Starting Robinhood 24/7 worker...", flush=True)

    while True:
        try:
            run_agent_cycle()
        except Exception as exc:
            error_event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "cycle_error",
                "error": str(exc),
            }
            print(json.dumps(error_event), flush=True)

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
    main()
