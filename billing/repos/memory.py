from billing.errors import NotFound


class MemoryRepo:
    """Dict-backed store for anything with an `.id`."""

    def __init__(self, kind="item"):
        self.kind = kind
        self._items = {}

    def add(self, item):
        self._items[item.id] = item
        return item

    save = add

    def get(self, item_id):
        try:
            return self._items[item_id]
        except KeyError:
            raise NotFound("%s %s not found" % (self.kind, item_id))

    def find(self, predicate):
        return [i for i in self._items.values() if predicate(i)]

    def all(self):
        return list(self._items.values())

    def remove(self, item_id):
        self.get(item_id)
        del self._items[item_id]

    def __len__(self):
        return len(self._items)
