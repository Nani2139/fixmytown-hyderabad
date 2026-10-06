"""Hyderabad is the only supported city."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CITIES_PATH = (
    Path(__file__).resolve().parents[4] / "packages" / "geo" / "cities.json"
)


def load_cities() -> list[dict[str, Any]]:
    with CITIES_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def load_city() -> dict[str, Any]:
    return load_cities()[0]


def city_for(lat: float, lng: float) -> dict[str, Any] | None:
    city = load_city()
    sw, ne = city["bounds"]["sw"], city["bounds"]["ne"]
    if sw["lat"] <= lat <= ne["lat"] and sw["lng"] <= lng <= ne["lng"]:
        return city
    return None
