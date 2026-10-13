# Backlog

Roughly ordered small to large. Acceptance criteria are as written by whoever filed the ticket,
so some are thinner than others.

---

### BILL-101 Validate plan fields
`PlanCatalog.add` only checks price and interval. Reject an empty/whitespace `name` and a negative
`trial_days` or `included_units` with a `ValidationError`. Add tests.

### BILL-102 Rename `addCredit` to `add_credit`
We have one camelCase method left on `Customer`. Rename it to `add_credit`, update callers, and keep
`addCredit` as a thin alias for now because some scripts outside this repo still use it.

### BILL-103 Tests for the email templates
`notify/templates.py` has no tests. Cover each template: subject, that the customer name and amount
show up, and the optional `next_retry` line in the payment-failed email.

### BILL-104 Tests for reporting
Nobody trusts the dashboard numbers. Add tests for `reporting.mrr`, `revenue_by_region` and
`ar_aging`. If you find something odd while doing it, note it in the PR rather than fixing it here.

---

### BILL-110 Notify customers on pause / resume / cancel
Customers only get email when something goes wrong with payment. Send an email when a subscription
is paused, resumed, or canceled (immediately or at period end). Needs new templates, a call from the
subscription service (or the app layer, your call), and tests with the fake email sender.

### BILL-111 First-invoice-only coupons
Marketing wants coupons that only discount the first invoice of a subscription. Add a flag on the
coupon, honor it when invoices are built, and make sure it works with the existing duration logic.

### BILL-112 Auto-resume for paused subscriptions
Let `pause` take an optional resume date. The nightly billing run should resume subscriptions whose
date has arrived (before it decides what is due). Paused subscriptions must never be invoiced.

### BILL-113 Use tiered pricing for overage
`usage.tiered_charge` exists but plans only support a flat overage rate. Allow a plan to define
tiers and use them when building the usage line on an invoice. Flat-rate plans must keep working.

### BILL-114 Persist invoices and payments to JSON
Plans can be saved and loaded, nothing else can. Add save/load for invoices and payments using
`JsonStore` so a demo run can be resumed. Decimals must round-trip exactly.

---

### BILL-120 Centralize money handling
Money is handled differently in about five places (Decimal helpers, ad hoc `Decimal(float(...))`,
integer cents, floats in reporting). Make `billing/money.py` the one way to do it, convert callers,
and keep float use out of anything that ends up on an invoice. Don't change behavior beyond that
without calling it out.

### BILL-121 Unify the duplicated rounding helpers
There are two rounding helpers that look the same but are not quite. Pick one, delete the other,
and make sure the behavior is pinned by tests before and after.

### BILL-122 Pull scattered constants into `config.py`
Tax rates, dunning offsets, the refund window, net terms and a few more are spread around. Move them
to config (or a JSON file loaded through config) without changing any values.

---

### BILL-130 Annual plans with mid-cycle upgrades
Support switching between monthly and annual plans, and upgrading an annual plan mid-year.
- Proration must work across different period lengths.
- The new period boundaries should be sensible (what happens to the renewal date?).
- The billing run must keep working for both kinds of subscription.
- Update `change_plan`, proration, invoicing, and the app facade; add an end-to-end test.
Currently `change_plan` refuses interval changes, see the TODO.

### BILL-131 Partial refunds with credit notes
Support refunding part of an invoice either back to the card or as account credit, and issue a credit
note document for every refund.
- New `CreditNote` model with its own numbering, linked to the invoice.
- Refund-to-credit increases the customer's balance instead of calling the gateway.
- Invoice should show how much has been credited vs refunded.
- Customer gets an email either way.
Design the data model first and put it in the PR description.

---

### BILL-140 Grace period for failed payments
Support says customers whose renewal fails should keep full access for 14 days. Finance says we
must stop service after the second failed charge to limit write-offs. Today the dunning schedule is
four retries over two weeks and the subscription goes `past_due` on the first failure. Make the
product behave the way "everyone agreed" in the last planning meeting.
