"""Retry / dunning for failed renewal payments."""
from datetime import timedelta

from billing import clock
from billing.models.subscription import ACTIVE, CANCELED, PAST_DUE, TRIALING
from billing.notify import templates

# days after the first failure on which we retry the charge
RETRY_OFFSETS = [1, 3, 7, 14]


class DunningService:
    def __init__(self, payments, invoices, subs, customers, notifier):
        self.payments = payments
        self.invoices = invoices
        self.subs = subs
        self.customers = customers
        self.notifier = notifier
        self.cases = {}

    def record_failure(self, invoice, today):
        customer = self.customers.get(invoice.customer_id)
        sub = self.subs.get(invoice.subscription_id) if invoice.subscription_id else None

        case = self.cases.get(invoice.id)
        if case is None:
            case = {"invoice_id": invoice.id, "first_failure": today, "attempts": 0,
                    "next_retry": None, "state": "open"}
            self.cases[invoice.id] = case
        case["attempts"] += 1

        if case["attempts"] > len(RETRY_OFFSETS):
            self._give_up(case, invoice, sub, customer)
            return case

        idx = min(case["attempts"], len(RETRY_OFFSETS) - 1)
        case["next_retry"] = case["first_failure"] + timedelta(days=RETRY_OFFSETS[idx])
        if sub is not None and sub.status in (ACTIVE, TRIALING):
            sub.transition(PAST_DUE)
        subject, body = templates.payment_failed(customer, invoice, case["next_retry"])
        self.notifier.send(customer.email, subject, body)
        return case

    def due_cases(self, today):
        return [c for c in self.cases.values()
                if c["state"] == "open" and c["next_retry"] <= today]

    def retry(self, case, today):
        invoice = self.invoices.get(case["invoice_id"])
        payment = self.payments.collect(invoice, now=clock.now())
        if payment.status == "succeeded":
            case["state"] = "recovered"
            if invoice.subscription_id:
                sub = self.subs.get(invoice.subscription_id)
                if sub.status == PAST_DUE:
                    sub.transition(ACTIVE)
            return True
        self.record_failure(invoice, today)
        return False

    def _give_up(self, case, invoice, sub, customer):
        case["state"] = "exhausted"
        case["next_retry"] = None
        invoice.status = "uncollectible"
        if sub is not None and sub.status != CANCELED:
            sub.transition(CANCELED)
        subject, body = templates.subscription_canceled(customer)
        self.notifier.send(customer.email, subject, body)
