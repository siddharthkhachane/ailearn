import json
from datetime import date
from decimal import Decimal

from billing.repos.json_store import JsonStore
from billing.repos.memory import MemoryRepo
from billing.errors import NotFound

import pytest


def test_write_then_read(tmp_path):
    store = JsonStore(str(tmp_path / "nested"))
    store.write("things", [{"a": 1}])
    assert store.read("things") == [{"a": 1}]


def test_read_default_when_missing(tmp_path):
    store = JsonStore(str(tmp_path))
    assert store.read("nope", default={"x": 1}) == {"x": 1}
    assert not store.exists("nope")


def test_encoder_handles_decimal_and_dates(tmp_path):
    store = JsonStore(str(tmp_path))
    store.write("m", {"amount": Decimal("1.10"), "when": date(2024, 1, 2)})
    with open(store.path("m")) as fh:
        raw = json.load(fh)
    assert raw == {"amount": "1.10", "when": "2024-01-02"}


def test_overwrite_leaves_no_tmp_file(tmp_path):
    store = JsonStore(str(tmp_path))
    store.write("x", 1)
    store.write("x", 2)
    assert store.read("x") == 2
    assert [p.name for p in tmp_path.iterdir()] == ["x.json"]


class _Thing:
    def __init__(self, id):
        self.id = id


def test_memory_repo_basics():
    repo = MemoryRepo("thing")
    repo.add(_Thing("a"))
    repo.add(_Thing("b"))
    assert len(repo) == 2
    assert repo.get("a").id == "a"
    assert [t.id for t in repo.find(lambda t: t.id > "a")] == ["b"]
    repo.remove("a")
    with pytest.raises(NotFound):
        repo.get("a")
    with pytest.raises(NotFound):
        repo.remove("a")
