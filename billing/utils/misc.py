import itertools

_counter = itertools.count(1)


def new_id(prefix):
    return "%s_%05d" % (prefix, next(_counter))


def reset_ids():
    global _counter
    _counter = itertools.count(1)


def fmt_money(amount, symbol="$"):
    return "{}{:,.2f}".format(symbol, amount)


def chunk(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]
