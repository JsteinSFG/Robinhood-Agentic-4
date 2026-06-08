from __future__ import annotations

from main import AccountState, OrderRequest, OrderSide, Position, RiskDecision


MAX_DAILY_LOSS_PCT = 5.0
MAX_POSITION_WEIGHT_PCT = 20.0
MAX_NEW_POSITION_WEIGHT_PCT = 5.0
DEFAULT_ADVERSE_MOVE_PCT = 10.0


def _position_by_symbol(positions: list[Position], symbol: str) -> Position | None:
    symbol = symbol.upper()
    for position in positions:
        if position.symbol.upper() == symbol:
            return position
    return None


def _order_value(order: OrderRequest) -> float:
    return float(order.quantity) * float(order.limit_price)


def _current_position_weight_pct(account: AccountState, position: Position | None) -> float:
    if position is None or account.portfolio_value <= 0:
        return 0.0

    return (float(position.market_value) / float(account.portfolio_value)) * 100.0


def _projected_position_weight_pct(
    account: AccountState,
    position: Position | None,
    order: OrderRequest,
) -> float:
    if account.portfolio_value <= 0:
        return 0.0

    current_value = float(position.market_value) if position else 0.0
    order_value = _order_value(order)

    if order.side == OrderSide.BUY:
        projected_value = current_value + order_value
    else:
        projected_value = max(0.0, current_value - order_value)

    return (projected_value / float(account.portfolio_value)) * 100.0


def _projected_daily_drawdown_pct(
    account: AccountState,
    order: OrderRequest,
    adverse_move_pct: float,
) -> float:
    if account.portfolio_value <= 0:
        return 100.0

    current_daily_loss_pct = max(0.0, -float(account.daily_pnl_pct))

    if order.side == OrderSide.SELL:
        return current_daily_loss_pct

    order_value = _order_value(order)
    adverse_order_loss = order_value * (float(adverse_move_pct) / 100.0)
    adverse_order_loss_pct = (adverse_order_loss / float(account.portfolio_value)) * 100.0

    return current_daily_loss_pct + adverse_order_loss_pct


def evaluate_order_risk(
    account: AccountState,
    positions: list[Position],
    order: OrderRequest,
    *,
    exceptional_conviction: bool = False,
    adverse_move_pct: float = DEFAULT_ADVERSE_MOVE_PCT,
    max_daily_loss_pct: float = MAX_DAILY_LOSS_PCT,
    max_position_weight_pct: float = MAX_POSITION_WEIGHT_PCT,
    max_new_position_weight_pct: float = MAX_NEW_POSITION_WEIGHT_PCT,
) -> RiskDecision:
    position = _position_by_symbol(positions, order.symbol)
    order_value = _order_value(order)

    current_weight_pct = _current_position_weight_pct(account, position)
    projected_weight_pct = _projected_position_weight_pct(account, position, order)
    projected_drawdown_pct = _projected_daily_drawdown_pct(
        account,
        order,
        adverse_move_pct,
    )

    if account.portfolio_value <= 0:
        return RiskDecision(
            approved=False,
            rejection_reason="Portfolio value is unavailable or invalid.",
            max_order_value=0.0,
            projected_position_weight_pct=projected_weight_pct,
            projected_daily_drawdown_pct=projected_drawdown_pct,
            exceptional_conviction_required=False,
            exceptional_conviction_passed=False,
        )

    if order.quantity <= 0:
        return RiskDecision(
            approved=False,
            rejection_reason="Order quantity must be greater than zero.",
            max_order_value=0.0,
            projected_position_weight_pct=projected_weight_pct,
            projected_daily_drawdown_pct=projected_drawdown_pct,
            exceptional_conviction_required=False,
            exceptional_conviction_passed=False,
        )

    if order.limit_price <= 0:
        return RiskDecision(
            approved=False,
            rejection_reason="Limit price must be greater than zero.",
            max_order_value=0.0,
            projected_position_weight_pct=projected_weight_pct,
            projected_daily_drawdown_pct=projected_drawdown_pct,
            exceptional_conviction_required=False,
            exceptional_conviction_passed=False,
        )

    if order.side == OrderSide.BUY and order_value > account.buying_power:
        return RiskDecision(
            approved=False,
            rejection_reason="Order value exceeds available buying power.",
            max_order_value=max(0.0, float(account.buying_power)),
            projected_position_weight_pct=projected_weight_pct,
            projected_daily_drawdown_pct=projected_drawdown_pct,
            exceptional_conviction_required=False,
            exceptional_conviction_passed=False,
        )

    if order.side == OrderSide.BUY and account.daily_pnl_pct <= -max_daily_loss_pct:
        return RiskDecision(
            approved=False,
            rejection_reason="Daily portfolio loss limit has already been reached.",
            max_order_value=0.0,
            projected_position_weight_pct=projected_weight_pct,
            projected_daily_drawdown_pct=projected_drawdown_pct,
            exceptional_conviction_required=False,
            exceptional_conviction_passed=False,
        )

    if order.side == OrderSide.BUY and projected_drawdown_pct >= max_daily_loss_pct:
        return RiskDecision(
            approved=False,
            rejection_reason="Projected daily drawdown would breach the 5% guardrail.",
            max_order_value=0.0,
            projected_position_weight_pct=projected_weight_pct,
            projected_daily_drawdown_pct=projected_drawdown_pct,
            exceptional_conviction_required=False,
            exceptional_conviction_passed=False,
        )

    if order.side == OrderSide.BUY and position is None and projected_weight_pct > max_new_position_weight_pct:
        return RiskDecision(
            approved=False,
            rejection_reason="New position would exceed max initial position size.",
            max_order_value=(account.portfolio_value * max_new_position_weight_pct) / 100.0,
            projected_position_weight_pct=projected_weight_pct,
            projected_daily_drawdown_pct=projected_drawdown_pct,
            exceptional_conviction_required=False,
            exceptional_conviction_passed=False,
        )

    exceptional_required = (
        order.side == OrderSide.BUY
        and position is not None
        and current_weight_pct >= max_position_weight_pct
    )

    if exceptional_required and not exceptional_conviction:
        return RiskDecision(
            approved=False,
            rejection_reason="Cannot add to a position already above 20% without exceptional conviction.",
            max_order_value=0.0,
            projected_position_weight_pct=projected_weight_pct,
            projected_daily_drawdown_pct=projected_drawdown_pct,
            exceptional_conviction_required=True,
            exceptional_conviction_passed=False,
        )

    return RiskDecision(
        approved=True,
        rejection_reason=None,
        max_order_value=order_value,
        projected_position_weight_pct=projected_weight_pct,
        projected_daily_drawdown_pct=projected_drawdown_pct,
        exceptional_conviction_required=exceptional_required,
        exceptional_conviction_passed=exceptional_required and exceptional_conviction,
    )

