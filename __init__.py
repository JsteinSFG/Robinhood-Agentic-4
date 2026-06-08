from __future__ import annotations

from rh_agent.config import Settings
from rh_agent.models import Candidate, OrderSide, TradeIdea


class StrategyDirector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def choose_trade(self, candidates: list[Candidate]) -> TradeIdea | None:
        for candidate in candidates:
            if candidate.risk_flags:
                continue
            if candidate.total_score < 0.72:
                continue
            target = self.settings.starting_capital * (self.settings.max_new_position_weight_pct / 100)
            return TradeIdea(
                symbol=candidate.symbol,
                side=OrderSide.BUY,
                target_value=round(target, 2),
                reason=f"{candidate.company_name}: {candidate.thesis}",
            )
        return None

