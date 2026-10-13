from billing.config import INVOICE_PREFIX
from billing.models.invoice import Invoice
from billing.repos.memory import MemoryRepo
from billing.services import tax
from billing.services.coupons import apply_coupons
from billing.services.usage import billable_units


class InvoiceService:
    def __init__(self, plans, customers, coupons, usage, invoices=None):
        self.plans = plans
        self.customers = customers
        self.coupons = coupons
        self.usage = usage
        self.invoices = invoices if invoices is not None else MemoryRepo("invoice")

    def build_renewal_invoice(self, sub, today, usage_period=None):
        plan = self.plans.get(sub.plan_id)
        customer = self.customers.get(sub.customer_id)
        start, end = sub.current_period_start, sub.current_period_end

        inv = Invoice(customer.id, sub.id, issue_date=today)
        inv.add_line("%s (%s to %s)" % (plan.name, start, end), 1,
                     plan.price_for_interval(), kind="subscription")

        if usage_period:
            units = self.usage.total_units(sub.id, usage_period[0], usage_period[1])
            extra = billable_units(plan, units)
            if extra > 0:
                inv.add_line("Usage overage (%d units)" % extra, plan.overage_rate, extra,
                             kind="usage")

        self._apply_discounts(inv, sub, start)
        tax.apply_tax(inv, customer.region)
        return self._finalize(inv)

    def invoice_for_plan_change(self, sub, proration, today):
        """Invoice the net of a proration. Returns None when the customer is owed money."""
        customer = self.customers.get(sub.customer_id)
        if proration["net"] <= 0:
            if proration["net"] < 0:
                customer.addCredit(-proration["net"])
            return None
        inv = Invoice(customer.id, sub.id, issue_date=today)
        inv.add_line("Unused time on previous plan", 1, -proration["credit"], kind="proration")
        inv.add_line("Remaining time on new plan", 1, proration["charge"], kind="proration")
        tax.apply_tax(inv, customer.region)
        return self._finalize(inv)

    def _apply_discounts(self, inv, sub, period_start):
        active = []
        for code in sub.coupon_codes:
            coupon = self.coupons.get(code)
            if self.coupons.is_active_for_period(coupon, sub.coupon_start, period_start):
                active.append(coupon)
        discount, applied = apply_coupons(inv.subtotal, self.coupons.select(active))
        inv.discount_total = discount
        inv.coupon_codes = [c.code for c in applied]

    def _finalize(self, inv):
        number = "%s-%d-%05d" % (INVOICE_PREFIX, inv.issue_date.year, len(self.invoices) + 1)
        inv.finalize(number)
        return self.invoices.add(inv)
