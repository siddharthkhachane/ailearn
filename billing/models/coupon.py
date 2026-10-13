from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class Coupon:
    code: str
    kind: str                       # "percent" | "fixed"
    value: Decimal
    stackable: bool = False
    max_redemptions: Optional[int] = None
    times_redeemed: int = 0
    duration_months: Optional[int] = None   # None means forever
    min_subtotal: Decimal = Decimal("0")
    expires_on: Optional[date] = None

    @property
    def id(self):
        return self.code
