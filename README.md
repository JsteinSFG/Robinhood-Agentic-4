import unittest

from rh_agent.config import Settings
from rh_agent.models import AccountState, OrderSide, Position, Quote, TradeIdea
from rh_agent.risk import RiskManager


class RiskManagerTests(unittest.TestCase):
    def test_blocks_daily_loss_limit(self):
        risk = RiskManager(Settings())
        decision = risk.evaluate(
            TradeIdea("MSFT", OrderSide.BUY, 100, "test"),
            Quote("MSFT", 100, 99.9, 100.1, 1_000_000_000),
            AccountState(1000, 1000, -50, -5, 1000),
            [],
            0,
        )
        self.assertFalse(decision.approved)

    def test_blocks_add_above_twenty_percent_without_exceptional_conviction(self):
        risk = RiskManager(Settings())
        decision = risk.evaluate(
            TradeIdea("MSFT", OrderSide.BUY, 50, "test"),
            Quote("MSFT", 100, 99.9, 100.1, 1_000_000_000),
            AccountState(1000, 750, 0, 0, 750),
            [Position("MSFT", 2.5, 250, 100, 100)],
            0,
        )
        self.assertFalse(decision.approved)
        self.assertTrue(decision.exceptional_conviction_required)

    def test_allows_small_liquid_buy(self):
        risk = RiskManager(Settings())
        decision = risk.evaluate(
            TradeIdea("MSFT", OrderSide.BUY, 50, "test"),
            Quote("MSFT", 100, 99.9, 100.1, 1_000_000_000),
            AccountState(1000, 1000, 0, 0, 1000),
            [],
            0,
        )
        self.assertTrue(decision.approved)
        self.assertEqual(decision.max_order_value, 50)


if __name__ == "__main__":
    unittest.main()

