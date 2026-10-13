from decimal import Decimal


class Customer(object):
    """A paying customer.

    Old-style class from before we adopted dataclasses; some callers still
    use the camelCase helpers.
    """

    def __init__(self, id, name, email, region="US-CA", timezone="UTC", payment_token=None):
        self.id = id
        self.name = name
        self.email = email
        self.region = region
        self.timezone = timezone
        self.payment_token = payment_token
        self.credit_balance = Decimal("0")

    def addCredit(self, amount):
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("credit must be positive")
        self.credit_balance += amount
        return self.credit_balance

    def use_credit(self, amount):
        """Consume up to `amount` of the balance, returning what was used."""
        used = min(self.credit_balance, amount)
        self.credit_balance -= used
        return used

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "region": self.region,
            "timezone": self.timezone,
            "payment_token": self.payment_token,
            "credit_balance": str(self.credit_balance),
        }

    @classmethod
    def from_dict(cls, d):
        c = cls(d["id"], d["name"], d["email"], d.get("region", "US-CA"),
                d.get("timezone", "UTC"), d.get("payment_token"))
        c.credit_balance = Decimal(d.get("credit_balance", "0"))
        return c

    def __repr__(self):
        return "<Customer %s %s>" % (self.id, self.email)
