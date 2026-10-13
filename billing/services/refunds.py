from billing import clock
from billing.errors import RefundError
from billing.models.payment import Refund
from billing.money import quantize, to_cents
from billing.notify import templates
from billing.repos.memory import MemoryRepo
from billing.utils.misc import new_id

REFUND_WINDOW_DAYS = 90


class RefundService:
    def __init__(self, gateway, invoices, payments, customers, notifier, refunds=None):
        self.gateway = gateway
        self.invoices = invoices
        self.payments = payments
        self.customers = customers
        self.notifier = notifier
        self.refunds = refunds if refunds is not None else MemoryRepo("refund")

    def refund(self, invoice_id, amount=None, reason="", now=None):
        inv = self.invoices.get(invoice_id)
        if inv.status not in ("paid", "partially_refunded"):
            raise RefundError("invoice %s is %s, nothing to refund" % (inv.id, inv.status))

        paid = [p for p in self.payments.payments_for(inv.id)
                if p.status == "succeeded" and p.gateway_ref]
        if not paid:
            raise RefundError("no card payment found for invoice %s" % inv.id)
        payment = paid[-1]

        now = now or clock.now()
        if (now - payment.created_at).days > REFUND_WINDOW_DAYS:
            raise RefundError("refund window has passed")

        refundable = inv.total - inv.refunded_total
        if amount is None:
            amount = refundable
        amount = quantize(amount)
        if amount <= 0 or amount > refundable:
            raise RefundError("invalid refund amount %s (max %s)" % (amount, refundable))

        result = self.gateway.refund(payment.gateway_ref, to_cents(amount))
        if not result["ok"]:
            raise RefundError("gateway refused refund: %s" % result["error"])

        refund = Refund(new_id("ref"), inv.id, payment.id, to_cents(amount), reason, now,
                        gateway_ref=result["ref"])
        self.refunds.add(refund)
        inv.refunded_total += amount
        inv.status = "refunded" if inv.refunded_total >= inv.total else "partially_refunded"

        customer = self.customers.get(inv.customer_id)
        subject, body = templates.refund_issued(customer, inv, amount)
        self.notifier.send(customer.email, subject, body)
        return refund
