from __future__ import annotations

from rh_agent.config import Settings
from rh_agent.models import AccountState, OrderSide, Position, Quote, RiskDecision, TradeIdea


class RiskManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(
        self,
        idea: TradeIdea,
        quote: Quote,
        account: AccountState,
        positions: list[Position],
        trades_today: int,
    ) -> RiskDecision:
        if account.daily_pnl <= -abs(self.settings.max_daily_loss_dollars):
            return self._reject("Daily dollar loss limit already reached.", account)

        if account.daily_pnl_pct <= -abs(self.settings.max_daily_loss_pct):
            return self._reject("Daily percentage loss limit already reached.", account)

        if trades_today >= self.settings.max_trades_per_day:
            return self._reject("Maximum trades per day reached.", account)

        if idea.side != OrderSide.BUY:
            return RiskDecision(True, None, idea.target_value, 0, abs(account.daily_pnl_pct), False, False)

        if quote.spread_bps > 30:
            return self._reject("Bid/ask spread is too wide.", account)

        if quote.avg_daily_dollar_volume < 25_000_000:
            return self._reject("Liquidity is too low.", account)

        max_daily_deployment = account.portfolio_value * (self.settings.max_daily_deployment_pct / 100)
        if idea.target_value > max_daily_deployment:
            return self._reject("Order is larger than the daily deployment cap.", account)

        max_new_position = account.portfolio_value * (self.settings.max_new_position_weight_pct / 100)
        capped_order_value = min(idea.target_value, max_new_position, account.cash)
        if capped_order_value <= 0:
            return self._reject("No cash is available for this order.", account)

        current_value = sum(p.market_value for p in positions if p.symbol == idea.symbol)
        projected_value = current_value + capped_order_value
        projected_weight_pct = (projected_value / account.portfolio_value) * 100
        current_weight_pct = (current_value / account.portfolio_value) * 100

        exceptional_required = current_weight_pct >= self.settings.max_position_weight_pct
        exceptional_passed = bool(idea.exceptional_conviction)
        if exceptional_required and not exceptional_passed:
            return RiskDecision(
                False,
                "Position is already above 20%; add blocked without exceptional conviction.",
                0.0,
                projected_weight_pct,
                abs(account.daily_pnl_pct),
                True,
                False,
            )

        adverse_move_pct = 8.0
        projected_loss = abs(account.daily_pnl) + (projected_value * adverse_move_pct / 100)
        projected_drawdown_pct = (projected_loss / account.portfolio_value) * 100
        if projected_drawdown_pct > self.settings.max_daily_loss_pct:
            return RiskDecision(
                False,
                "Projected adverse-move drawdown exceeds 5%.",
                0.0,
                projected_weight_pct,
                projected_drawdown_pct,
                exceptional_required,
                exceptional_passed,
            )

        return RiskDecision(
            True,
            None,
            round(capped_order_value, 2),
            projected_weight_pct,
            projected_drawdown_pct,
            exceptional_required,
            exceptional_passed,
        )

    @staticmethod
    def _reject(reason: str, account: AccountState) -> RiskDecision:
        return RiskDecision(False, reason, 0.0, 0.0, abs(account.daily_pnl_pct), False, False)

