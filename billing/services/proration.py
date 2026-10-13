"""Proration for mid-period plan changes."""
from decimal import Decimal

from billing.money import ZERO, quantize

_RATIO_PLACES = Decimal("0.01")


def remaining_ratio(period_start, period_end, change_date):
    """Fraction of the period still ahead of `change_date` (0..1)."""
    total_days = (period_end - period_start).days
    if total_days <= 0:
        return ZERO
    remaining = (period_end - change_date).days
    remaining = max(0, min(remaining, total_days))
    return (Decimal(remaining) / Decimal(total_days)).quantize(_RATIO_PLACES)


def prorate(old_price, new_price, ratio):
    credit = quantize(old_price * ratio)
    charge = quantize(new_price * ratio)
    return {"credit": credit, "charge": charge, "net": charge - credit, "ratio": ratio}
