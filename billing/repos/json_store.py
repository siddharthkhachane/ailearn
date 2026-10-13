import json
import os
from datetime import date, datetime
from decimal import Decimal


class _Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        return super().default(o)


class JsonStore:
    """One JSON file per collection name, written atomically."""

    def __init__(self, directory):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def path(self, name):
        return os.path.join(self.directory, name + ".json")

    def exists(self, name):
        return os.path.exists(self.path(name))

    def read(self, name, default=None):
        if not self.exists(name):
            return default
        with open(self.path(name), "r", encoding="utf-8") as fh:
            return json.load(fh)

    def write(self, name, data):
        tmp = self.path(name) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, cls=_Encoder, indent=2, sort_keys=True)
        os.replace(tmp, self.path(name))
