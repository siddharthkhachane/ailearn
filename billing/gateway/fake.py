from billing.gateway.base import PaymentGateway


class FakeGateway(PaymentGateway):
    """In-memory gateway for tests and the demo CLI."""

    def __init__(self):
        self.charges = []
        self.refunds = []
        self.declined_tokens = set()
        self._fail_queue = []
        self._idempotent = {}

    def fail_next(self, n=1, reason="card_declined"):
        self._fail_queue.extend([reason] * n)

    def charge(self, token, amount_cents, currency="USD", idempotency_key=None):
        if idempotency_key and idempotency_key in self._idempotent:
            return self._idempotent[idempotency_key]
        if self._fail_queue:
            result = {"ok": False, "ref": None, "error": self._fail_queue.pop(0)}
        elif not token:
            result = {"ok": False, "ref": None, "error": "no_payment_method"}
        elif token in self.declined_tokens:
            result = {"ok": False, "ref": None, "error": "card_declined"}
        else:
            ref = "ch_%04d" % (len(self.charges) + 1)
            self.charges.append({"ref": ref, "token": token, "amount_cents": amount_cents,
                                 "currency": currency})
            result = {"ok": True, "ref": ref, "error": None}
        if idempotency_key:
            self._idempotent[idempotency_key] = result
        return result

    def refund(self, charge_ref, amount_cents):
        if not any(c["ref"] == charge_ref for c in self.charges):
            return {"ok": False, "ref": None, "error": "unknown_charge"}
        ref = "re_%04d" % (len(self.refunds) + 1)
        self.refunds.append({"ref": ref, "charge_ref": charge_ref, "amount_cents": amount_cents})
        return {"ok": True, "ref": ref, "error": None}
