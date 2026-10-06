from __future__ import annotations

import time

_CACHE: dict[str, tuple[float, dict]] = {}
TTL = 20.0


def get(key: str) -> dict | None:
    hit = _CACHE.get(key)
    if not hit:
        return None
    exp, val = hit
    if time.time() > exp:
        _CACHE.pop(key, None)
        return None
    return val


def set(key: str, val: dict) -> None:
    _CACHE[key] = (time.time() + TTL, val)


def bust() -> None:
    _CACHE.clear()
