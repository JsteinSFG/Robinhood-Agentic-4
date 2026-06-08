from main import AccountState, OrderRequest, OrderSide, Position
from risk import evaluate_order_risk


def account(
    portfolio_value=10000,
    cash=2000,
    daily_pnl=0,
    daily_pnl_pct=0,
    buying_power=2000,
):
    return AccountState(
        portfolio_value=portfolio_value,
        cash=cash,
        daily_pnl=daily_pnl,
        daily_pnl_pct=daily_pnl_pct,
        buying_power=buying_power,
    )


def position(
    symbol="NVDA",
    quantity=10,
    market_value=2000,
    average_cost=150,
    current_price=200,
):
    return Position(
        symbol=symbol,
        quantity=quantity,
        market_value=market_value,
        average_cost=average_cost,
        current_price=current_price,
    )


def buy_order(symbol="NVDA", quantity=1, limit_price=100):
    return OrderRequest(
        symbol=symbol,
        side=OrderSide.BUY,
        quantity=quantity,
        limit_price=limit_price,
    )


def sell_order(symbol="NVDA", quantity=1, limit_price=100):
    return OrderRequest(
        symbol=symbol,
        side=OrderSide.SELL,
        quantity=quantity,
        limit_price=limit_price,
    )


def test_blocks_buys_at_or_above_five_percent_daily_loss():
    decision = evaluate_order_risk(
        account(daily_pnl=-500, daily_pnl_pct=-5),
        [],
        buy_order(quantity=1, limit_price=100),
    )

    assert decision.approved is False
    assert "Daily portfolio loss limit" in decision.rejection_reason


def test_blocks_projected_drawdown_over_five_percent():
    decision = evaluate_order_risk(
        account(portfolio_value=10000, buying_power=6000),
        [],
        buy_order(symbol="MSFT", quantity=51, limit_price=100),
        adverse_move_pct=10,
        max_new_position_weight_pct=100,
    )

    assert decision.approved is False
    assert "Projected daily drawdown" in decision.rejection_reason


def test_blocks_adds_above_twenty_percent_without_exceptional_conviction():
    decision = evaluate_order_risk(
        account(portfolio_value=10000, buying_power=2000),
        [position(symbol="NVDA", market_value=2500)],
        buy_order(symbol="NVDA", quantity=1, limit_price=100),
    )

    assert decision.approved is False
    assert decision.exceptional_conviction_required is True
    assert "above 20%" in decision.rejection_reason


def test_allows_adds_above_twenty_percent_with_exceptional_conviction():
    decision = evaluate_order_risk(
        account(portfolio_value=10000, buying_power=2000),
        [position(symbol="NVDA", market_value=2500)],
        buy_order(symbol="NVDA", quantity=1, limit_price=100),
        exceptional_conviction=True,
    )

    assert decision.approved is True
    assert decision.exceptional_conviction_required is True
    assert decision.exceptional_conviction_passed is True


def test_blocks_buys_above_buying_power():
    decision = evaluate_order_risk(
        account(buying_power=100),
        [],
        buy_order(symbol="MSFT", quantity=2, limit_price=100),
    )

    assert decision.approved is False
    assert "buying power" in decision.rejection_reason


def test_allows_sells_as_risk_reducing():
    decision = evaluate_order_risk(
        account(daily_pnl=-500, daily_pnl_pct=-5, buying_power=0),
        [position(symbol="NVDA", market_value=2000)],
        sell_order(symbol="NVDA", quantity=1, limit_price=100),
    )

    assert decision.approved is True


def test_blocks_new_positions_above_max_initial_size():
    decision = evaluate_order_risk(
        account(portfolio_value=10000, buying_power=2000),
        [],
        buy_order(symbol="MSFT", quantity=6, limit_price=100),
        max_new_position_weight_pct=5,
    )

    assert decision.approved is False
    assert "max initial position size" in decision.rejection_reason
