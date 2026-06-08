from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    bid: float
    ask: float
    as_of: str
    source: str = "paper"


class PaperMarketDataProvider:
    def __init__(self) -> None:
        self.quotes = {
            "MSFT": 100.00,
            "NVDA": 200.00,
            "AAPL": 190.00,
            "AMD": 160.00,
            "GOOGL": 175.00,
        }

    def get_quote(self, symbol: str) -> Quote:
        symbol = symbol.upper()
        price = float(self.quotes.get(symbol, 100.00))

        return Quote(
            symbol=symbol,
            price=price,
            bid=round(price * 0.999, 2),
            ask=round(price * 1.001, 2),
            as_of=datetime.now(timezone.utc).isoformat(),
        )


def build_market_data_provider():
    return PaperMarketDataProvider()
