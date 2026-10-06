from __future__ import annotations

from datetime import datetime, timedelta, timezone

from wardwatch_api.geo import circle_label
from wardwatch_api.models import Ticket, TicketEvent


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def days_open(t: Ticket) -> int:
    start = _aware(t.created_at)
    if not start:
        return 0
    end = _aware(t.resolved_at) or datetime.now(timezone.utc)
    return max(0, (end - start).days)


def ticket_public(t: Ticket, *, include_events: bool = False) -> dict:
    media = [
        {"id": m.id, "url": f"/v1/media/{m.id}", "kind": m.kind}
        for m in (t.media or [])
    ]
    data = {
        "id": t.id,
        "public_id": t.public_id,
        "status": t.status,
        "type": t.type,
        "severity": t.severity,
        "lat": t.lat,
        "lng": t.lng,
        "neighborhood": t.neighborhood,
        "circle": t.circle,
        "circle_label": circle_label(t.circle or ""),
        "ward": t.ward,
        "title": t.title,
        "body": t.body,
        "confirmation_count": t.confirmation_count,
        "days_open": days_open(t),
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
        "resolve_note": t.resolve_note if t.status in ("resolved", "rejected") else None,
        "media": media,
    }
    if include_events:
        events = sorted(t.events or [], key=lambda e: e.created_at or datetime.min.replace(tzinfo=timezone.utc))
        data["timeline"] = [
            {"type": e.type, "at": e.created_at.isoformat() if e.created_at else None}
            for e in events
        ]
    return data


def geojson_feature(
    t: Ticket,
    *,
    distance_m: int | None = None,
    confirmations_week: int = 0,
) -> dict:
    thumb = None
    photos = [m for m in (t.media or []) if m.kind != "fix"]
    if photos:
        thumb = f"/v1/media/{photos[0].id}"
    elif t.media:
        thumb = f"/v1/media/{t.media[0].id}"
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [t.lng, t.lat]},
        "properties": {
            "public_id": t.public_id,
            "type": t.type,
            "severity": t.severity,
            "status": t.status,
            "title": t.title,
            "confirmation_count": t.confirmation_count,
            "confirmations_week": confirmations_week,
            "days_open": days_open(t),
            "neighborhood": t.neighborhood,
            "circle": t.circle,
            "circle_label": circle_label(t.circle or ""),
            "ward": t.ward,
            "distance_m": distance_m,
            "thumb": thumb,
        },
    }


def recently_fixed_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=14)


def add_event(ticket_id: str, typ: str, payload: dict | None = None) -> TicketEvent:
    import json

    return TicketEvent(
        ticket_id=ticket_id,
        type=typ,
        payload_json=json.dumps(payload or {}),
    )
