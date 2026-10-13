from dataclasses import dataclass, asdict
from decimal import Decimal

from billing.money import quantize


@dataclass
class Plan:
    id: str
    name: str
    monthly_price: Decimal
    interval: str = "month"          # "month" | "year"
    trial_days: int = 0
    included_units: int = 0
    overage_rate: Decimal = Decimal("0")
    annual_discount: float = 0.0     # fraction, e.g. 0.15 -- comes straight from the pricing JSON
    active: bool = True

    @property
    def months(self):
        return 12 if self.interval == "year" else 1

    def annual_price(self):
        return quantize(Decimal(float(self.monthly_price) * 12 * (1 - self.annual_discount)))

    def price_for_interval(self):
        if self.interval == "year":
            return self.annual_price()
        return self.monthly_price

    @classmethod
    def from_dict(cls, d):
        return cls(
            id=d["id"],
            name=d["name"],
            monthly_price=Decimal(str(d["monthly_price"])),
            interval=d.get("interval", "month"),
            trial_days=int(d.get("trial_days", 0)),
            included_units=int(d.get("included_units", 0)),
            overage_rate=Decimal(str(d.get("overage_rate", "0"))),
            annual_discount=float(d.get("annual_discount", 0.0)),
            active=d.get("active", True),
        )

    def to_dict(self):
        return asdict(self)
