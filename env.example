from __future__ import annotations

from rh_agent.models import Candidate, Quote


class DemoMarketDataProvider:
    """Deterministic starter data so paper mode works before paid data is connected."""

    quotes = {
        "MSFT": Quote("MSFT", 486.0, 485.8, 486.2, 6_000_000_000),
        "NVDA": Quote("NVDA", 144.0, 143.9, 144.1, 18_000_000_000),
        "AAPL": Quote("AAPL", 202.0, 201.9, 202.1, 7_500_000_000),
        "GEV": Quote("GEV", 550.0, 549.0, 551.0, 900_000_000),
        "VST": Quote("VST", 190.0, 189.8, 190.2, 1_200_000_000),
        "XOM": Quote("XOM", 112.0, 111.95, 112.05, 2_400_000_000),
    }

    candidates = [
        Candidate(
            "MSFT",
            "Microsoft",
            "High-quality AI platform compounder with strong balance sheet.",
            0.78,
            0.86,
            0.72,
            0.95,
        ),
        Candidate(
            "NVDA",
            "NVIDIA",
            "AI accelerator leader, but valuation and concentration risk need tight sizing.",
            0.82,
            0.74,
            0.8,
            0.98,
        ),
        Candidate(
            "VST",
            "Vistra",
            "Power demand beneficiary tied to U.S. data-center buildout.",
            0.76,
            0.68,
            0.74,
            0.83,
        ),
        Candidate(
            "GEV",
            "GE Vernova",
            "Grid and power infrastructure exposure with strong industrial demand.",
            0.72,
            0.7,
            0.73,
            0.72,
        ),
        Candidate(
            "XOM",
            "Exxon Mobil",
            "Large-cap U.S. energy exposure with strong liquidity and cash generation.",
            0.62,
            0.72,
            0.55,
            0.9,
        ),
    ]

    def get_quote(self, symbol: str) -> Quote:
        try:
            return self.quotes[symbol.upper()]
        except KeyError as exc:
            raise ValueError(f"No demo quote for {symbol}") from exc

    def screen_us_stocks(self) -> list[Candidate]:
        return sorted(self.candidates, key=lambda c: c.total_score, reverse=True)

