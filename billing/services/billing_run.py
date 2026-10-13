from billing import clock
from billing.models.subscription import TRIALING
from billing.notify import templates


class BillingRun:
    """Nightly job: renew due subscriptions, invoice, collect, then retry dunning cases."""

    def __init__(self, subs, invoicing, payments, dunning, customers, notifier):
        self.subs = subs
        self.invoicing = invoicing
        self.payments = payments
        self.dunning = dunning
        self.customers = customers
        self.notifier = notifier

    def run(self, today=None):
        today = today or clock.today()
        summary = {"invoiced": 0, "paid": 0, "failed": 0, "canceled": 0, "retried": 0,
                   "recovered": 0}
        for sub in self.subs.due_for_renewal(today):
            self._process(sub, today, summary)
        for case in self.dunning.due_cases(today):
            summary["retried"] += 1
            if self.dunning.retry(case, today):
                summary["recovered"] += 1
        return summary

    def _process(self, sub, today, summary):
        if sub.cancel_at_period_end:
            sub.cancel()
            summary["canceled"] += 1
            return

        was_trial = sub.status == TRIALING
        usage_period = None if was_trial else (sub.current_period_start, sub.current_period_end)
        if was_trial:
            self.subs.activate_after_trial(sub)
        else:
            self.subs.renew(sub)

        invoice = self.invoicing.build_renewal_invoice(sub, today, usage_period)
        summary["invoiced"] += 1
        customer = self.customers.get(sub.customer_id)
        subject, body = templates.invoice_ready(customer, invoice)
        self.notifier.send(customer.email, subject, body)

        if invoice.status == "paid":
            summary["paid"] += 1
            return
        payment = self.payments.collect(invoice)
        if payment.status == "succeeded":
            summary["paid"] += 1
        else:
            summary["failed"] += 1
            self.dunning.record_failure(invoice, today)
