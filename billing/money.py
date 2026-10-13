"""Money helpers. Amounts are Decimal, rounded half-up to cents."""
from decimal import Decimal, ROUND_HALF_UP

ZERO = Decimal("0")
CENT = Decimal("0.01")


def as_decimal(value):
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def quantize(amount):
    return as_decimal(amount).quantize(CENT, rounding=ROUND_HALF_UP)


def to_cents(amount):
    return int(quantize(amount) * 100)


def from_cents(cents):
    return quantize(Decimal(cents) / 100)
