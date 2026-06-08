from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    LIMIT = "limit"


@dataclass(frozen=True)
class AccountState:
    portfolio_value: float
    cash: float
    daily_pnl: float
    daily_pnl_pct: float
    buying_power: float
    as_of: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: float
    market_value: float
    average_cost: float
    current_price: float

    @property
    def weight_pct(self) -> float:
        return 0.0


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    bid: float
    ask: float
    avg_daily_dollar_volume: float
    as_of: str = field(default_factory=utc_now_iso)

    @property
    def spread_bps(self) -> float:
        mid = (self.bid + self.ask) / 2
        if mid <= 0:
            return 999999.0
        return ((self.ask - self.bid) / mid) * 10000


@dataclass(frozen=True)
class Candidate:
    symbol: str
    company_name: str
    thesis: str
    technical_score: float
    fundamental_score: float
    catalyst_score: float
    liquidity_score: float
    risk_flags: list[str] = field(default_factory=list)

    @property
    def total_score(self) -> float:
        return (
            self.technical_score * 0.35
            + self.fundamental_score * 0.35
            + self.catalyst_score * 0.2
            + self.liquidity_score * 0.1
        )


@dataclass(frozen=True)
class TradeIdea:
    symbol: str
    side: OrderSide
    target_value: float
    reason: str
    exceptional_conviction: bool = False


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    rejection_reason: str | None
    max_order_value: float
    projected_position_weight_pct: float
    projected_daily_drawdown_pct: float
    exceptional_conviction_required: bool
    exceptional_conviction_passed: bool


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: OrderSide
    quantity: float
    limit_price: float
    order_type: OrderType = OrderType.LIMIT
    time_in_force: str = "day"
    reason: str = ""


@dataclass(frozen=True)
class OrderStatus:
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    limit_price: float
    status: str
    message: str
    as_of: str = field(default_factory=utc_now_iso)

