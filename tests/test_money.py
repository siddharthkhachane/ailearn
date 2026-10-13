from decimal import Decimal

import pytest

from billing.money import as_decimal, from_cents, quantize, to_cents
from billing.utils.misc import chunk, fmt_money

D = Decimal


@pytest.mark.parametrize("raw,expected", [
    ("2.675", "2.68"),
    ("2.674", "2.67"),
    ("0.005", "0.01"),
    ("10", "10.00"),
    ("-2.675", "-2.68"),
])
def test_quantize_rounds_half_up(raw, expected):
    assert quantize(D(raw)) == D(expected)


def test_as_decimal_goes_through_str_for_floats():
    assert as_decimal(0.1) == D("0.1")


def test_as_decimal_passes_decimal_through():
    d = D("1.234")
    assert as_decimal(d) is d


def test_to_cents():
    assert to_cents(D("19.99")) == 1999
    assert to_cents(D("0.005")) == 1


def test_to_cents_whole_dollars():
    assert to_cents(D("5")) == 500


def test_from_cents_roundtrip():
    assert from_cents(1999) == D("19.99")
    assert from_cents(to_cents(D("123.45"))) == D("123.45")


def test_fmt_money():
    assert fmt_money(D("1234.5")) == "$1,234.50"


def test_chunk():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
