from __future__ import annotations

import json
import uuid
from pathlib import Path

from rh_agent.config import Settings
from rh_agent.models import AccountState, OrderRequest, OrderSide, OrderStatus, Position, utc_now_iso


class LiveExecutionBlocked(RuntimeError):
    pass


class PaperBroker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.path = Path(settings.paper_state_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(
                {
                    "cash": settings.starting_capital,
                    "daily_pnl": 0.0,
                    "positions": {},
                    "orders": [],
                }
            )

    def _read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, state: dict) -> None:
        self.path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    def get_account(self) -> AccountState:
        state = self._read()
        positions_value = sum(p["market_value"] for p in state["positions"].values())
        portfolio_value = state["cash"] + positions_value
        daily_pnl = state.get("daily_pnl", 0.0)
        daily_pnl_pct = 0.0 if portfolio_value <= 0 else (daily_pnl / portfolio_value) * 100
        return AccountState(
            portfolio_value=portfolio_value,
            cash=state["cash"],
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            buying_power=state["cash"],
        )

    def get_positions(self) -> list[Position]:
        state = self._read()
        return [
            Position(
                symbol=symbol,
                quantity=raw["quantity"],
                market_value=raw["market_value"],
                average_cost=raw["average_cost"],
                current_price=raw["current_price"],
            )
            for symbol, raw in sorted(state["positions"].items())
        ]

    def get_trades_today(self) -> int:
        state = self._read()
        today = utc_now_iso()[:10]
        return sum(
            1
            for order in state.get("orders", [])
            if order.get("status") == "filled" and order.get("as_of", "")[:10] == today
        )

    def place_order(self, order: OrderRequest) -> OrderStatus:
        state = self._read()
        cost = round(order.quantity * order.limit_price, 2)
        symbol = order.symbol.upper()

        if order.side == OrderSide.BUY:
            if cost > state["cash"]:
                return OrderStatus(
                    str(uuid.uuid4()),
                    symbol,
                    order.side,
                    order.quantity,
                    order.limit_price,
                    "rejected",
                    "Paper broker rejected order: not enough cash.",
                )
            state["cash"] = round(state["cash"] - cost, 2)
            existing = state["positions"].get(symbol)
            if existing:
                new_qty = existing["quantity"] + order.quantity
                new_value = existing["market_value"] + cost
                avg_cost = new_value / new_qty
            else:
                new_qty = order.quantity
                new_value = cost
                avg_cost = order.limit_price
            state["positions"][symbol] = {
                "quantity": new_qty,
                "market_value": round(new_value, 2),
                "average_cost": round(avg_cost, 4),
                "current_price": order.limit_price,
            }
        else:
            existing = state["positions"].get(symbol)
            if not existing or order.quantity > existing["quantity"]:
                return OrderStatus(
                    str(uuid.uuid4()),
                    symbol,
                    order.side,
                    order.quantity,
                    order.limit_price,
                    "rejected",
                    "Paper broker rejected order: not enough shares.",
                )
            state["cash"] = round(state["cash"] + cost, 2)
            remaining = existing["quantity"] - order.quantity
            if remaining <= 0:
                state["positions"].pop(symbol)
            else:
                existing["quantity"] = remaining
                existing["market_value"] = round(remaining * order.limit_price, 2)
                existing["current_price"] = order.limit_price

        status = OrderStatus(
            str(uuid.uuid4()),
            symbol,
            order.side,
            order.quantity,
            order.limit_price,
            "filled",
            f"Paper {order.side.value} filled.",
        )
        state["orders"].append(status.__dict__ | {"side": status.side.value})
        self._write(state)
        return status


class RobinhoodAgenticBroker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if not settings.robinhood_connector_enabled or not settings.robinhood_mcp_url:
            raise LiveExecutionBlocked(
                "Live trading is blocked until the Robinhood Agentic MCP connector is configured."
            )

    def get_account(self) -> AccountState:
        raise LiveExecutionBlocked("Robinhood MCP adapter is a placeholder in this scaffold.")

    def get_positions(self) -> list[Position]:
        raise LiveExecutionBlocked("Robinhood MCP adapter is a placeholder in this scaffold.")

    def get_trades_today(self) -> int:
        raise LiveExecutionBlocked("Robinhood MCP adapter is a placeholder in this scaffold.")

    def place_order(self, order: OrderRequest) -> OrderStatus:
        raise LiveExecutionBlocked("Robinhood MCP adapter is a placeholder in this scaffold.")


def build_broker(settings: Settings):
    if settings.live_enabled:
        return RobinhoodAgenticBroker(settings)
    return PaperBroker(settings)
