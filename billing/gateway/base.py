from abc import ABC, abstractmethod


class PaymentGateway(ABC):
    """Interface to the card processor. Amounts are integer cents.

    Both calls return a dict: {"ok": bool, "ref": str | None, "error": str | None}
    """

    @abstractmethod
    def charge(self, token, amount_cents, currency="USD", idempotency_key=None):
        raise NotImplementedError

    @abstractmethod
    def refund(self, charge_ref, amount_cents):
        raise NotImplementedError
