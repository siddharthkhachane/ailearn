from datetime import timedelta
from decimal import Decimal, ROUND_HALF_EVEN

from billing import clock
from billing.config import DEFAULT_CURRENCY, NET_TERMS_DAYS
from billing.errors import BillingError
from billing.money import ZERO
from billing.utils.misc import new_id


def _round(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


class Invoice(object):
    """An invoice. Lines are plain dicts; tax and discount are totals on the invoice."""

    def __init__(self, customer_id, subscription_id=None, issue_date=None,
                 currency=DEFAULT_CURRENCY):
        self.id = new_id("inv")
        self.number = None
        self.customer_id = customer_id
        self.subscription_id = subscription_id
        self.currency = currency
        self.status = "draft"      # draft, open, paid, void, uncollectible, partially_refunded, refunded
        self._lines = []
        self.discount_total = ZERO
        self.tax_total = ZERO
        self.credit_applied = ZERO
        self.amount_paid = ZERO
        self.refunded_total = ZERO
        self.coupon_codes = []
        self.issue_date = issue_date or clock.today()
        self.due_date = self.issue_date + timedelta(days=NET_TERMS_DAYS)
        self.paid_at = None

    def add_line(self, description, quantity, unit_price, kind="charge", taxable=True):
        if self.status != "draft":
            raise BillingError("cannot edit a %s invoice" % self.status)
        amount = _round(Decimal(quantity) * Decimal(unit_price))
        line = {
            "description": description,
            "quantity": quantity,
            "unit_price": unit_price,
            "amount": amount,
            "kind": kind,
            "taxable": taxable,
        }
        self._lines.append(line)
        return line

    @property
    def lines(self):
        return [dict(l) for l in self._lines]

    @property
    def subtotal(self):
        return sum((l["amount"] for l in self._lines), ZERO)

    @property
    def total(self):
        return _round(self.subtotal - self.discount_total + self.tax_total)

    @property
    def amount_due(self):
        return max(self.total - self.credit_applied - self.amount_paid, ZERO)

    def finalize(self, number):
        if self.status != "draft":
            raise BillingError("invoice already finalized")
        self.number = number
        self.status = "open"
        if self.total <= 0:
            self.status = "paid"

    def mark_paid(self, amount, when=None):
        self.amount_paid += amount
        if self.amount_due == 0:
            self.status = "paid"
            self.paid_at = when or clock.now()

    def void(self):
        if self.status not in ("draft", "open"):
            raise BillingError("cannot void a %s invoice" % self.status)
        self.status = "void"

    def is_overdue(self, as_of):
        return self.status == "open" and as_of > self.due_date

    def to_dict(self):
        return {
            "id": self.id,
            "number": self.number,
            "customer_id": self.customer_id,
            "subscription_id": self.subscription_id,
            "status": self.status,
            "currency": self.currency,
            "issue_date": self.issue_date.isoformat(),
            "due_date": self.due_date.isoformat(),
            "lines": [
                {k: (str(v) if isinstance(v, Decimal) else v) for k, v in l.items()}
                for l in self._lines
            ],
            "subtotal": str(self.subtotal),
            "discount_total": str(self.discount_total),
            "tax_total": str(self.tax_total),
            "total": str(self.total),
            "amount_paid": str(self.amount_paid),
            "refunded_total": str(self.refunded_total),
        }
