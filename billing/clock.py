"""Tiny clock indirection so tests can freeze time."""
from datetime import datetime, timezone

_frozen = None


def now():
    if _frozen is not None:
        return _frozen
    return datetime.now(timezone.utc)


def today():
    return now().date()


def freeze(dt):
    global _frozen
    _frozen = dt


def unfreeze():
    global _frozen
    _frozen = None
