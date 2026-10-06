from __future__ import annotations

import math
from typing import Any

from wardwatch_api.city import city_for, load_city

TYPES = (
    "waterlogging",
    "open_manhole",
    "garbage",
    "streetlight",
    "pothole",
    "dug_road",
    "dumping",
    "stagnant_water",
)
TYPE_LABELS = {
    "waterlogging": "Waterlogging",
    "open_manhole": "Open manhole",
    "garbage": "Garbage black spot",
    "streetlight": "Streetlight out",
    "pothole": "Pothole",
    "dug_road": "Road left dug",
    "dumping": "Illegal dumping",
    "stagnant_water": "Stagnant water",
}
SEVERITIES = ("blocks_road", "night_danger", "smell")
STATUSES = ("open", "in_review", "resolved", "rejected")
ALLOWED = {
    "open": {"in_review", "resolved", "rejected"},
    "in_review": {"resolved", "rejected"},
    "resolved": set(),
    "rejected": set(),
}
RADIUS_M = 20_000.0
STILL_THERE_M = 400.0


def city() -> dict[str, Any]:
    return load_city()


def type_label(typ: str) -> str:
    return TYPE_LABELS.get(typ, typ.replace("_", " ").capitalize())


def circle_label(circle_id: str) -> str:
    for row in load_city().get("circles") or []:
        if row.get("id") == circle_id:
            return str(row.get("label") or circle_id)
    return circle_id.replace("_", " ").title()


def in_bounds(lat: float, lng: float) -> bool:
    return city_for(lat, lng) is not None


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def within_radius(
    lat: float,
    lng: float,
    origin_lat: float,
    origin_lng: float,
    meters: float = RADIUS_M,
) -> bool:
    return haversine_m(lat, lng, origin_lat, origin_lng) <= meters


def _nearest(lat: float, lng: float, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    best = None
    best_m = float("inf")
    for area in rows:
        if "lat" not in area or "lng" not in area:
            continue
        dist = haversine_m(lat, lng, float(area["lat"]), float(area["lng"]))
        if dist < best_m:
            best = area
            best_m = dist
    return best


def place_for(lat: float, lng: float) -> dict[str, str]:
    found = city_for(lat, lng) or load_city()
    ward = _nearest(lat, lng, found.get("neighborhoods") or [])
    circle = _nearest(lat, lng, found.get("circles") or [])
    ward_label = (ward or {}).get("label") or "Hyderabad"
    circle_label = (circle or {}).get("label") or "Hyderabad"
    return {
        "neighborhood": (ward or {}).get("id") or "unknown",
        "ward": ward_label,
        "circle": (circle or {}).get("id") or "unknown",
        "circle_label": circle_label,
    }


def neighborhood_for(lat: float, lng: float) -> str:
    return place_for(lat, lng)["neighborhood"]


def can_transition(src: str, dest: str) -> bool:
    return dest in ALLOWED.get(src, set())
