from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional


def _coerce_decimal(value: Optional[float | int | str]) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def format_usd(value: Optional[float | int | str], decimals: int = 2, default: str = "—") -> str:
    """
    Format a numeric value as a USD currency string.

    Args:
        value: Numeric value to format.
        decimals: Number of decimal places to show.
        default: String to return when value is None or invalid.
    """
    quantize_str = f"1.{'0' * decimals}"
    amount = _coerce_decimal(value)
    if amount is None:
        return default

    try:
        rounded = amount.quantize(Decimal(quantize_str))
    except (InvalidOperation, ValueError):
        return default

    sign = "-" if rounded < 0 else ""
    absolute = abs(rounded)
    return f"{sign}${absolute:,.{decimals}f}"

