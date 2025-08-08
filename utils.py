"""
Currency utilities for handling amounts in cents to avoid floating-point precision issues.
"""

from typing import Union
from decimal import Decimal, ROUND_HALF_UP


def dollars_to_cents(amount: Union[float, str, Decimal]) -> int:
    """
    Convert dollars to cents.

    Args:
        amount: Amount in dollars (can be float, string, or Decimal)

    Returns:
        Amount in cents as integer

    Examples:
        >>> dollars_to_cents(10.50)
        1050
        >>> dollars_to_cents("10.50")
        1050
        >>> dollars_to_cents(10.555)
        1056  # Rounds to nearest cent
    """
    if isinstance(amount, str):
        amount = Decimal(amount)
    elif isinstance(amount, float):
        amount = Decimal(str(amount))
    elif isinstance(amount, Decimal):
        pass
    else:
        raise ValueError(f"Invalid amount type: {type(amount)}")

    # Convert to cents and round to nearest cent
    cents = (amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def cents_to_dollars(amount_cents: int) -> Decimal:
    """
    Convert cents to dollars as Decimal for precise calculations.

    Args:
        amount_cents: Amount in cents

    Returns:
        Amount in dollars as Decimal

    Examples:
        >>> cents_to_dollars(1050)
        Decimal('10.50')
    """
    return Decimal(amount_cents) / 100


def cents_to_dollars_float(amount_cents: int) -> float:
    """
    Convert cents to dollars as float (use with caution for display only).

    Args:
        amount_cents: Amount in cents

    Returns:
        Amount in dollars as float

    Examples:
        >>> cents_to_dollars_float(1050)
        10.5
    """
    return float(cents_to_dollars(amount_cents))


def format_currency(amount_cents: int) -> str:
    """
    Format cents as currency string.

    Args:
        amount_cents: Amount in cents

    Returns:
        Formatted currency string

    Examples:
        >>> format_currency(1050)
        '$10.50'
        >>> format_currency(-1050)
        '-$10.50'
    """
    dollars = cents_to_dollars(amount_cents)
    if amount_cents < 0:
        return f"-${abs(dollars):.2f}"
    return f"${dollars:.2f}"


def validate_amount(amount: Union[float, str, Decimal, int]) -> bool:
    """
    Validate that an amount is reasonable for financial transactions.

    Args:
        amount: Amount to validate (can be dollars or cents)

    Returns:
        True if amount is valid

    Raises:
        ValueError: If amount is invalid
    """
    try:
        # If amount is already an int, assume it's in cents
        if isinstance(amount, int):
            cents = amount
        else:
            # Convert from dollars to cents
            cents = dollars_to_cents(amount)

        if cents < 0:
            raise ValueError("Amount cannot be negative")
        if cents > 999999999:  # $10 million limit
            raise ValueError("Amount exceeds maximum limit")
        return True
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid amount: {e}")


def parse_amount_string(amount_str: str) -> int:
    """
    Parse amount string (e.g., "$10.50", "10.50", "1050") to cents.

    Args:
        amount_str: String representation of amount

    Returns:
        Amount in cents

    Examples:
        >>> parse_amount_string("$10.50")
        1050
        >>> parse_amount_string("10.50")
        1050
        >>> parse_amount_string("1050")
        1050
    """
    # Remove currency symbols and whitespace
    cleaned = amount_str.strip().replace("$", "").replace(",", "")

    try:
        # Try to parse as float first
        return dollars_to_cents(float(cleaned))
    except ValueError:
        raise ValueError(f"Invalid amount format: {amount_str}")
