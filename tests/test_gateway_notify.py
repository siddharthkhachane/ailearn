import random
import time

from billing.gateway.fake import FakeGateway
from billing.notify.fake import FakeEmailSender


def test_charge_success_returns_ref():
    gw = FakeGateway()
    res = gw.charge("tok", 500)
    assert res["ok"] and res["ref"] == "ch_0001"


def test_charge_without_token_fails():
    res = FakeGateway().charge(None, 500)
    assert (res["ok"], res["error"]) == (False, "no_payment_method")


def test_declined_token():
    gw = FakeGateway()
    gw.declined_tokens.add("bad")
    assert gw.charge("bad", 100)["error"] == "card_declined"
    assert gw.charges == []


def test_fail_next_is_consumed_in_order():
    gw = FakeGateway()
    gw.fail_next(2, reason="timeout")
    assert gw.charge("tok", 1)["error"] == "timeout"
    assert gw.charge("tok", 1)["error"] == "timeout"
    assert gw.charge("tok", 1)["ok"]


def test_idempotency_key_replays_result():
    gw = FakeGateway()
    first = gw.charge("tok", 100, idempotency_key="k1")
    second = gw.charge("tok", 100, idempotency_key="k1")
    assert first == second
    assert len(gw.charges) == 1


def test_refund_known_and_unknown_charge():
    gw = FakeGateway()
    ref = gw.charge("tok", 1000)["ref"]
    assert gw.refund(ref, 400)["ok"]
    assert gw.refund("ch_missing", 400)["error"] == "unknown_charge"


def test_charges_recorded_in_order():
    # Seeded and sleeps a little so the order is "realistic" -- it is fully deterministic.
    random.seed(7)
    amounts = [random.randint(100, 5000) for _ in range(5)]
    gw = FakeGateway()
    started = time.time()
    for amount in amounts:
        time.sleep(0.01)
        gw.charge("tok", amount)
    elapsed = time.time() - started
    assert [c["amount_cents"] for c in gw.charges] == amounts
    assert elapsed >= 0.05 or len(gw.charges) == 5


def test_email_outbox():
    mail = FakeEmailSender()
    mail.send("a@b.c", "hi", "body")
    mail.send("x@y.z", "yo", "body")
    assert len(mail.outbox) == 2
    assert mail.sent_to("a@b.c")[0]["subject"] == "hi"
