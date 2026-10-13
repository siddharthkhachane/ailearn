from decimal import Decimal

import pytest

from billing.models.invoice import Invoice
from billing.services.tax import apply_tax, rate_for, tax_for_invoice

D = Decimal


def make_invoice(*amounts, taxable=True):
    inv = Invoice("cus_1")
    for a in amounts:
        inv.add_line("item", 1, D(a), taxable=taxable)
    return inv


@pytest.mark.parametrize("region,rate", [
    ("US-CA", "0.0725"),
    ("us-ca", "0.0725"),
    ("DE", "0.19"),
    ("US-OR", "0"),
    ("ZZ", "0"),
    (None, "0"),
])
def test_rate_for(region, rate):
    assert rate_for(region) == D(rate)


def test_tax_on_simple_invoice():
    assert tax_for_invoice(make_invoice("100.00"), "US-CA") == D("7.25")


def test_tax_sums_all_lines_then_rounds_once():
    assert tax_for_invoice(make_invoice("0.10", "0.10", "0.10"), "DE") == D("0.06")


def test_non_taxable_lines_excluded():
    inv = make_invoice("100.00")
    inv.add_line("gift", 1, D("50.00"), taxable=False)
    assert tax_for_invoice(inv, "DE") == D("19.00")


def test_negative_lines_reduce_taxable_base():
    inv = make_invoice("100.00")
    inv.add_line("credit", 1, D("-40.00"))
    assert tax_for_invoice(inv, "FR") == D("12.00")


def test_never_negative():
    inv = make_invoice("-10.00")
    assert tax_for_invoice(inv, "FR") == D("0.00")


def test_unknown_region_means_no_tax():
    assert tax_for_invoice(make_invoice("100.00"), "ZZ") == D("0.00")


def test_apply_tax_sets_total_on_invoice():
    inv = make_invoice("200.00")
    assert apply_tax(inv, "GB") == D("40.00")
    assert inv.tax_total == D("40.00")
    assert inv.total == D("240.00")


@pytest.mark.parametrize("region,amount,expected", [
    ("US-NY", "100.00", "8.88"),
    ("US-TX", "80.00", "5.00"),
    ("JP", "1000.00", "100.00"),
    ("GB", "9.99", "2.00"),
])
def test_tax_examples(region, amount, expected):
    assert tax_for_invoice(make_invoice(amount), region) == D(expected)
