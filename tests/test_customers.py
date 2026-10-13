from decimal import Decimal

import pytest

from billing.errors import NotFound, ValidationError
from billing.models.customer import Customer
from billing.services.customers import CustomerService

D = Decimal


@pytest.fixture
def svc():
    return CustomerService()


def test_create_normalises_fields(svc):
    c = svc.create("  Ada Lovelace ", " ADA@Example.com ")
    assert c.name == "Ada Lovelace"
    assert c.email == "ada@example.com"
    assert c.region == "US-CA"
    assert c.id.startswith("cus_")


@pytest.mark.parametrize("name,email", [("", "a@b.c"), ("   ", "a@b.c"), ("Bob", "nope")])
def test_create_validates(svc, name, email):
    with pytest.raises(ValidationError):
        svc.create(name, email)


def test_duplicate_email_rejected_case_insensitively(svc):
    svc.create("A", "a@b.c")
    with pytest.raises(ValidationError):
        svc.create("B", "A@B.C")


def test_get_unknown(svc):
    with pytest.raises(NotFound):
        svc.get("cus_99999")


def test_find_by_email(svc):
    c = svc.create("A", "a@b.c")
    assert svc.find_by_email("A@b.c") is c
    assert svc.find_by_email("zzz@b.c") is None


def test_set_region(svc):
    c = svc.create("A", "a@b.c")
    svc.set_region(c.id, "DE")
    assert svc.get(c.id).region == "DE"


def test_list_page(svc):
    for i in range(5):
        svc.create("C%d" % i, "c%d@x.io" % i)
    assert len(svc.list_page(1, 2)) == 2
    assert len(svc.list_page(3, 2)) == 1
    assert svc.list_page(4, 2) == []
    assert [c.name for c in svc.list_page(1, 2)] == ["C0", "C1"]


def test_credit_helpers():
    c = Customer("c1", "A", "a@b.c")
    assert c.addCredit(5) == D("5")
    assert c.use_credit(D("3")) == D("3")
    assert c.use_credit(D("10")) == D("2")
    assert c.credit_balance == D("0")


def test_add_credit_rejects_non_positive():
    with pytest.raises(ValueError):
        Customer("c1", "A", "a@b.c").addCredit(0)


def test_service_add_credit(svc):
    c = svc.create("A", "a@b.c")
    svc.add_credit(c.id, D("12.50"))
    assert c.credit_balance == D("12.50")


def test_customer_dict_roundtrip():
    c = Customer("c1", "A", "a@b.c", region="DE", payment_token="tok")
    c.addCredit(D("2.50"))
    clone = Customer.from_dict(c.to_dict())
    assert (clone.id, clone.region, clone.payment_token) == ("c1", "DE", "tok")
    assert clone.credit_balance == D("2.50")
    assert "c1" in repr(clone)


@pytest.mark.parametrize("email", ["a@b.c", "first.last@sub.example.org", "x+tag@y.io"])
def test_accepts_reasonable_emails(svc, email):
    assert svc.create("Name", email).email == email


def test_customer_ids_are_sequential(svc):
    ids = [svc.create("N%d" % i, "n%d@x.io" % i).id for i in range(3)]
    assert ids == ["cus_00001", "cus_00002", "cus_00003"]


def test_list_page_default_page_size(svc):
    for i in range(25):
        svc.create("N%d" % i, "n%d@x.io" % i)
    assert len(svc.list_page()) == 20
    assert len(svc.list_page(2)) == 5
