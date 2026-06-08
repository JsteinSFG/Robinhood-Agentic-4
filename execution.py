from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    return float(raw)


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    trading_mode: str = os.getenv("TRADING_MODE", "paper")
    broker: str = os.getenv("BROKER", "paper")
    starting_capital: float = _float("STARTING_AGENTIC_CAPITAL", 1000)
    max_daily_loss_pct: float = _float("MAX_DAILY_PORTFOLIO_LOSS_PCT", 5)
    max_daily_loss_dollars: float = _float("MAX_DAILY_LOSS_DOLLARS", 50)
    max_position_weight_pct: float = _float("MAX_POSITION_WEIGHT_PCT", 20)
    max_new_position_weight_pct: float = _float("MAX_NEW_POSITION_WEIGHT_PCT", 10)
    max_daily_deployment_pct: float = _float("MAX_DAILY_DEPLOYMENT_PCT", 25)
    max_trades_per_day: int = _int("MAX_TRADES_PER_DAY", 2)
    stocks_only: bool = _bool("STOCKS_ONLY", True)
    allow_options: bool = _bool("ALLOW_OPTIONS", False)
    allow_crypto: bool = _bool("ALLOW_CRYPTO", False)
    allow_margin: bool = _bool("ALLOW_MARGIN", False)
    allow_shorts: bool = _bool("ALLOW_SHORTS", False)
    robinhood_mcp_url: str = os.getenv("ROBINHOOD_MCP_URL", "")
    robinhood_connector_enabled: bool = _bool("ROBINHOOD_CONNECTOR_ENABLED", False)
    log_path: str = os.getenv("AUDIT_LOG_PATH", "logs/audit.jsonl")
    paper_state_path: str = os.getenv("PAPER_STATE_PATH", "data/paper_state.json")

    @property
    def live_enabled(self) -> bool:
        return self.trading_mode == "live"

