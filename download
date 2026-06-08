from __future__ import annotations

from rh_agent.audit import AuditLogger
from rh_agent.broker import build_broker
from rh_agent.config import Settings
from rh_agent.market_data import DemoMarketDataProvider
from rh_agent.models import OrderRequest
from rh_agent.risk import RiskManager
from rh_agent.strategy import StrategyDirector


class TradingEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.broker = build_broker(settings)
        self.market_data = DemoMarketDataProvider()
        self.risk = RiskManager(settings)
        self.strategy = StrategyDirector(settings)
        self.audit = AuditLogger(settings.log_path)

    def preflight(self) -> dict:
        account = self.broker.get_account()
        payload = {
            "mode": self.settings.trading_mode,
            "portfolio_value": account.portfolio_value,
            "cash": account.cash,
            "daily_pnl": account.daily_pnl,
            "daily_pnl_pct": account.daily_pnl_pct,
            "safe_to_trade": account.daily_pnl > -abs(self.settings.max_daily_loss_dollars),
        }
        self.audit.write("preflight", payload)
        return payload

    def screen(self) -> list[dict]:
        candidates = self.market_data.screen_us_stocks()
        payload = [
            {
                "symbol": c.symbol,
                "company_name": c.company_name,
                "score": round(c.total_score, 3),
                "thesis": c.thesis,
            }
            for c in candidates
        ]
        self.audit.write("screen", {"candidates": payload})
        return payload

    def trade_cycle(self) -> dict:
        account = self.broker.get_account()
        positions = self.broker.get_positions()
        trades_today = self.broker.get_trades_today()
        candidates = self.market_data.screen_us_stocks()
        idea = self.strategy.choose_trade(candidates)

        if idea is None:
            payload = {"action": "no_trade", "reason": "No candidate passed the strategy screen."}
            self.audit.write("trade_cycle", payload)
            return payload

        quote = self.market_data.get_quote(idea.symbol)
        decision = self.risk.evaluate(idea, quote, account, positions, trades_today=trades_today)
        if not decision.approved:
            payload = {
                "action": "rejected",
                "symbol": idea.symbol,
                "reason": decision.rejection_reason,
                "projected_daily_drawdown_pct": round(decision.projected_daily_drawdown_pct, 2),
            }
            self.audit.write("trade_rejected", payload)
            return payload

        quantity = round(decision.max_order_value / quote.ask, 6)
        order = OrderRequest(
            symbol=idea.symbol,
            side=idea.side,
            quantity=quantity,
            limit_price=quote.ask,
            reason=idea.reason,
        )
        status = self.broker.place_order(order)
        payload = {
            "action": "submitted",
            "mode": self.settings.trading_mode,
            "symbol": status.symbol,
            "side": status.side.value,
            "quantity": status.quantity,
            "limit_price": status.limit_price,
            "status": status.status,
            "message": status.message,
            "risk": {
                "projected_position_weight_pct": round(decision.projected_position_weight_pct, 2),
                "projected_daily_drawdown_pct": round(decision.projected_daily_drawdown_pct, 2),
            },
        }
        self.audit.write("order_status", payload)
        return payload
