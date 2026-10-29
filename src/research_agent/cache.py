"""Bounded process-local TTL cache. No errors or secrets are cached."""

import hashlib
import json
import time
from collections import OrderedDict
from copy import deepcopy
from typing import Any


class TTLCache:
    def __init__(self, ttl: float = 3600, max_entries: int = 512) -> None:
        self.ttl = ttl
        self.max_entries = max_entries
        self.entries: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    @staticmethod
    def key(namespace: str, args: dict[str, Any]) -> str:
        return hashlib.sha256((namespace + json.dumps(args, sort_keys=True)).encode()).hexdigest()

    def get(self, key: str) -> Any | None:
        entry = self.entries.get(key)
        if entry is None:
            return None
        if entry[0] <= time.monotonic():
            del self.entries[key]
            return None
        self.entries.move_to_end(key)
        return deepcopy(entry[1])

    def put(self, key: str, data: Any) -> None:
        self.entries[key] = (time.monotonic() + self.ttl, deepcopy(data))
        self.entries.move_to_end(key)
        while len(self.entries) > self.max_entries:
            self.entries.popitem(last=False)
