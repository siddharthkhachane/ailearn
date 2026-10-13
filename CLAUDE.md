# Billing service

Internal subscription-billing library: plans, subscriptions, usage charges, proration, coupons,
tax, invoices, refunds, dunning. Standard library only (plus pytest). In-memory storage, with a
JSON file store for plans. No network; the payment gateway and email sender are fakes behind ABCs.

## Run

```bash
pip install -r requirements-dev.txt
pytest                      # whole suite, well under a second
python -m billing.cli demo  # tiny end-to-end run with the fakes
```

## Layout

```
billing/
  app.py          composition root (BillingApp) wiring everything with in-memory repos
  config.py       some constants (not all -- tax rates, retry offsets, refund window live in their services)
  money.py        Decimal helpers (quantize, to_cents, from_cents)
  clock.py        now()/today() with freeze() for tests
  models/         plan, customer, subscription, invoice, coupon, payment/refund
  services/       business logic: plans, customers, subscriptions, proration, usage, coupons,
                  tax, invoicing, payments, refunds, dunning, billing_run, reporting
  gateway/        PaymentGateway ABC + FakeGateway (integer cents)
  notify/         EmailSender ABC, FakeEmailSender, text templates
  repos/          MemoryRepo, JsonStore
  utils/          dates (add_months etc.), misc (ids, formatting)
tests/            pytest; conftest.py has the `app`, `customer`, `jan15` fixtures
STORIES.md        backlog
```

## Conventions

- Money is `Decimal`, rounded half-up to cents via `billing.money.quantize`. Integer cents only at
  the gateway boundary (`to_cents` / `from_cents`). A few older spots deviate; check before assuming.
- Use `billing.clock` rather than calling `datetime.now()` directly; tests freeze it or pass dates in.
- Model styles are mixed (dataclasses, plain classes, dict records). Match the file you are editing.
- Domain errors derive from `billing.errors.BillingError`.
- IDs come from `utils.misc.new_id`; `conftest.py` resets the counter before every test.
- `services/legacy_export.py` is unused; leave it unless a story says otherwise.
