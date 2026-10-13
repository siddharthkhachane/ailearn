"""Composition root: wires the services together with in-memory storage."""
from billing import clock
from billing.gateway.fake import FakeGateway
from billing.notify.fake import FakeEmailSender
from billing.repos.memory import MemoryRepo
from billing.services.billing_run import BillingRun
from billing.services.coupons import CouponService
from billing.services.customers import CustomerService
from billing.services.dunning import DunningService
from billing.services.invoicing import InvoiceService
from billing.services.payments import PaymentService
from billing.services.plans import PlanCatalog
from billing.services.refunds import RefundService
from billing.services.subscriptions import SubscriptionService
from billing.services.usage import UsageService


class BillingApp:
    def __init__(self, gateway=None, mailer=None):
        self.gateway = gateway or FakeGateway()
        self.mailer = mailer or FakeEmailSender()

        self.plans = PlanCatalog()
        self.customers = CustomerService()
        self.coupons = CouponService()
        self.usage = UsageService()
        self.subs = SubscriptionService(self.plans, self.customers)

        self.invoice_repo = MemoryRepo("invoice")
        self.invoicing = InvoiceService(self.plans, self.customers, self.coupons, self.usage,
                                        self.invoice_repo)
        self.payments = PaymentService(self.gateway, self.customers)
        self.dunning = DunningService(self.payments, self.invoice_repo, self.subs,
                                      self.customers, self.mailer)
        self.refunds = RefundService(self.gateway, self.invoice_repo, self.payments,
                                     self.customers, self.mailer)
        self.billing_run = BillingRun(self.subs, self.invoicing, self.payments, self.dunning,
                                      self.customers, self.mailer)

    def subscribe(self, customer_id, plan_id, start=None, coupon_codes=None):
        plan = self.plans.get(plan_id)
        start = start or clock.today()
        for code in coupon_codes or []:
            self.coupons.redeem(code, plan.price_for_interval(), start)
        return self.subs.create(customer_id, plan_id, start, coupon_codes)

    def change_plan(self, sub_id, new_plan_id, change_date=None):
        result = self.subs.change_plan(sub_id, new_plan_id, change_date)
        sub = self.subs.get(sub_id)
        invoice = self.invoicing.invoice_for_plan_change(
            sub, result, change_date or clock.today())
        if invoice is not None:
            self.payments.collect(invoice)
        return result, invoice
