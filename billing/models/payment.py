from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from billing.money import from_cents


@dataclass
class Payment:
    id: str
    invoice_id: str
    customer_id: str
    amount: Decimal
    status: str                      # "succeeded" | "failed"
    created_at: datetime
    gateway_ref: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Refund:
    id: str
    invoice_id: str
    payment_id: str
    amount_cents: int                # integer cents, mirrors the gateway API
    reason: str
    created_at: datetime
    gateway_ref: Optional[str] = None

    @property
    def amount(self):
        return from_cents(self.amount_cents)
