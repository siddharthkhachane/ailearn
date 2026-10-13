"""Demo entry point:  python -m billing.cli demo"""
import sys
from datetime import date, timedelta
from decimal import Decimal

from billing.app import BillingApp
from billing.models.plan import Plan


def demo():
    app = BillingApp()
    app.plans.add(Plan("starter", "Starter", Decimal("19.00"), included_units=1000,
                       overage_rate=Decimal("0.02")))
    cust = app.customers.create("Demo Co", "demo@example.com", payment_token="tok_demo")
    start = date(2024, 1, 15)
    sub = app.subscribe(cust.id, "starter", start=start)
    for month in range(1, 4):
        day = start + timedelta(days=31 * month)
        print(day, app.billing_run.run(day))
    print("subscription:", sub.status, sub.current_period_end)
    print("emails sent:", len(app.mailer.outbox))


def report():
    from billing.services import reporting
    app = BillingApp()
    app.plans.add(Plan("starter", "Starter", Decimal("19.00")))
    cust = app.customers.create("Demo Co", "demo@example.com", payment_token="tok_demo")
    app.subscribe(cust.id, "starter", start=date(2024, 1, 15))
    print("MRR:", reporting.mrr(app.subs.repo.all(), app.plans))
    print("plan mix:", reporting.plan_mix(app.subs.repo.all()))


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if argv[:1] == ["demo"]:
        demo()
        return 0
    if argv[:1] == ["report"]:
        report()
        return 0
    print("usage: python -m billing.cli [demo|report]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
