import os
import time
from datetime import datetime, timezone

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
TRADING_MODE = os.getenv("TRADING_MODE", "paper")


def run_agent_cycle():
    now = datetime.now(timezone.utc).isoformat()
    print(f"[{now}] Robinhood agent heartbeat | mode={TRADING_MODE}", flush=True)

    # TODO:
    # 1. Pull latest account/market data
    # 2. Run strategy checks
    # 3. Run risk guardrails
    # 4. Produce recommendation
    # 5. Never execute live trades unless explicitly built/enabled later


def main():
    print("Starting Robinhood 24/7 worker...", flush=True)

    while True:
        try:
            run_agent_cycle()
        except Exception as exc:
            print(f"Agent cycle failed: {exc}", flush=True)

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
