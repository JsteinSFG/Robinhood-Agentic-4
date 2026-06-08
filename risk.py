from __future__ import annotations

import json
import sys
import time

from rh_agent.broker import LiveExecutionBlocked, build_broker
from rh_agent.config import Settings
from rh_agent.execution import TradingEngine


def _print(data) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    command = argv[0] if argv else "help"
    settings = Settings()

    try:
        if command == "help":
            print("Commands: preflight, screen, review, trade-cycle, positions, worker, halt")
            return 0
        if command == "preflight":
            _print(TradingEngine(settings).preflight())
            return 0
        if command == "screen":
            _print(TradingEngine(settings).screen())
            return 0
        if command in {"review", "trade-cycle"}:
            _print(TradingEngine(settings).trade_cycle())
            return 0
        if command == "positions":
            broker = build_broker(settings)
            account = broker.get_account()
            positions = [p.__dict__ for p in broker.get_positions()]
            _print({"account": account.__dict__, "positions": positions})
            return 0
        if command == "worker":
            engine = TradingEngine(settings)
            _print({"status": "worker_started", "mode": settings.trading_mode})
            while True:
                _print(engine.trade_cycle())
                time.sleep(60 * 60)
        if command == "halt":
            _print({"status": "halt_requested", "message": "Stop the Railway service to halt the agent."})
            return 0
    except LiveExecutionBlocked as exc:
        _print({"status": "blocked", "reason": str(exc)})
        return 2

    _print({"status": "error", "reason": f"Unknown command: {command}"})
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

