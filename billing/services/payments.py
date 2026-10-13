from billing import clock
from billing.errors import PaymentError
from billing.models.payment import Payment
from billing.money import ZERO, to_cents
from billing.repos.memory import MemoryRepo
from billing.utils.misc import new_id


class PaymentService:
    def __init__(self, gateway, customers, payments=None):
        self.gateway = gateway
        self.customers = customers
        self.payments = payments if payments is not None else MemoryRepo("payment")

    def collect(self, invoice, now=None):
        """Charge whatever is still owed, using account credit first."""
        if invoice.status != "open":
            raise PaymentError("invoice %s is %s" % (invoice.id, invoice.status))
        now = now or clock.now()
        customer = self.customers.get(invoice.customer_id)

        used = customer.use_credit(invoice.amount_due)
        invoice.credit_applied += used
        due = invoice.amount_due

        if due == 0:
            invoice.mark_paid(ZERO, now)
            return self._record(invoice, ZERO, "succeeded", now)

        attempt = len(self.payments.find(lambda p: p.invoice_id == invoice.id)) + 1
        result = self.gateway.charge(customer.payment_token, to_cents(due), invoice.currency,
                                     "%s-%d" % (invoice.id, attempt))
        if result["ok"]:
            invoice.mark_paid(due, now)
            return self._record(invoice, due, "succeeded", now, ref=result["ref"])
        return self._record(invoice, due, "failed", now, error=result["error"])

    def _record(self, invoice, amount, status, when, ref=None, error=None):
        payment = Payment(new_id("pay"), invoice.id, invoice.customer_id, amount, status, when,
                          gateway_ref=ref, error=error)
        return self.payments.add(payment)

    def payments_for(self, invoice_id):
        return self.payments.find(lambda p: p.invoice_id == invoice_id)
