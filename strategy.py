from __future__ import annotations

from dataclasses import dataclass

from main import AccountState, OrderRequest, OrderSide, Position


@dataclass(frozen=True)
class StrategyCandidate:
    symbol: str
    company_name: str
    action: str
    thesis: str
    confidence: str
    quantity: float
    limit_price: float
    reason: str
    exceptional_conviction: bool = False


def existing_symbols(positions: list[Position]) -> set[str]:
    return {position.symbol.upper() for position in positions}


def propose_paper_candidate(
    account: AccountState,
    positions: list[Position],
    market_data,
) -> StrategyCandidate | None:
    symbols = existing_symbols(positions)

    if account.buying_power <= 0:
        return None

    if "MSFT" not in symbols:
        quote = market_data.get_quote("MSFT")
        return StrategyCandidate(
            symbol="MSFT",
            company_name="Microsoft",
            action="buy",
            thesis="AI infrastructure exposure through cloud, enterprise software, and data center demand.",
            confidence="low",
            quantity=1,
            limit_price=quote.ask,
            reason="Paper-mode strategy candidate for market data and risk integration.",
        )

    if "NVDA" in symbols:
        quote = market_data.get_quote("NVDA")
        return StrategyCandidate(
            symbol="NVDA",
            company_name="NVIDIA",
            action="hold",
            thesis="AI infrastructure leader, but existing exposure should be concentration-checked before any add.",
            confidence="medium",
            quantity=0,
            limit_price=quote.ask,
            reason="Paper-mode hold candidate. No order proposed.",
        )

    return None


def candidate_to_order(candidate: StrategyCandidate) -> OrderRequest | None:
    if candidate.action == "buy":
        return OrderRequest(
            symbol=candidate.symbol,
            side=OrderSide.BUY,
            quantity=candidate.quantity,
            limit_price=candidate.limit_price,
            reason=candidate.reason,
        )

    return None


def candidate_to_dict(candidate: StrategyCandidate | None):
    if candidate is None:
        return None

    return {
        "symbol": candidate.symbol,
        "company_name": candidate.company_name,
        "action": candidate.action,
        "thesis": candidate.thesis,
        "confidence": candidate.confidence,
        "quantity": candidate.quantity,
        "limit_price": candidate.limit_price,
        "reason": candidate.reason,
        "exceptional_conviction": candidate.exceptional_conviction,
    }
