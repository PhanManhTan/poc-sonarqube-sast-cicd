from __future__ import annotations
import re
from decimal import Decimal


_SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
_KNOWN_PRICES = {
    "AAPL": Decimal("228.50"),
    "MSFT": Decimal("421.75"),
    "SONAR": Decimal("100.00"),
}


def normalize_symbol(raw_symbol: str) -> str:
    symbol = raw_symbol.strip().upper()
    if not _SYMBOL_PATTERN.fullmatch(symbol):
        raise ValueError("symbol must contain 1-10 letters, digits, dots, or dashes")
    return symbol


def build_quote(raw_symbol: str) -> dict:
    symbol = normalize_symbol(raw_symbol)
    price = _KNOWN_PRICES.get(symbol)
    if price is None:
        # Deterministic sample data keeps the endpoint useful without external I/O.
        price = Decimal(sum(ord(character) for character in symbol)) / Decimal("10")

    return {
        "currency": "USD",
        "price": f"{price:.2f}",
        "symbol": symbol,
    }
