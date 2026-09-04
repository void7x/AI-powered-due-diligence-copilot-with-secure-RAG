"""Minimal in-process TTL cache with a clean seam for Redis later."""
from __future__ import annotations

import threading
import time
from typing import Any, Callable


class TTLCache:
    def __init__(self, max_size: int = 512, ttl_seconds: float = 300.0) -> None:
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            hit = self._store.get(key)
            if not hit:
                return None
            expires, value = hit
            if expires < time.monotonic():
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._store) >= self.max_size:
                for k in list(self._store)[: max(1, len(self._store) // 4)]:
                    self._store.pop(k, None)
            self._store[key] = (time.monotonic() + self.ttl, value)

    def get_or_set(self, key: str, factory: Callable[[], Any]) -> Any:
        value = self.get(key)
        if value is None:
            value = factory()
            self.set(key, value)
        return value
