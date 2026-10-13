"""Usage records (plain dicts) and overage pricing."""
from decimal import Decimal

from billing import clock
from billing.errors import ValidationError
from billing.money import ZERO, quantize


def make_usage_record(subscription_id, units, ts, metric="api_calls"):
    return {"subscription_id": subscription_id, "units": units, "ts": ts, "metric": metric}


class UsageService:
    def __init__(self):
        self._records = []

    def record(self, subscription_id, units, ts=None, metric="api_calls"):
        if not isinstance(units, int) or units <= 0:
            raise ValidationError("units must be a positive integer")
        rec = make_usage_record(subscription_id, units, ts or clock.now(), metric)
        self._records.append(rec)
        return rec

    def records_for_period(self, subscription_id, start, end):
        """Records whose day falls in [start, end)."""
        out = []
        for r in self._records:
            if r["subscription_id"] != subscription_id:
                continue
            day = r["ts"].date()
            if start <= day < end:
                out.append(r)
        return out

    def total_units(self, subscription_id, start, end):
        return sum(r["units"] for r in self.records_for_period(subscription_id, start, end))


def billable_units(plan, units):
    return max(units - plan.included_units, 0)


def usage_charge(plan, units):
    return quantize(Decimal(billable_units(plan, units)) * plan.overage_rate)


def tiered_charge(units, tiers):
    """Graduated pricing. tiers: [{"up_to": 100, "rate": "0.10"}, {"up_to": None, "rate": ...}]"""
    total = ZERO
    prev = 0
    for tier in tiers:
        cap = tier["up_to"]
        upper = units if cap is None else min(units, cap)
        if upper > prev:
            total += Decimal(upper - prev) * Decimal(str(tier["rate"]))
        if cap is None or units <= cap:
            break
        prev = cap
    return quantize(total)
