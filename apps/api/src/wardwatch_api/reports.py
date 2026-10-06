from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from wardwatch_api.embed import cosine, embed_text
from wardwatch_api.geo import (
    RADIUS_M,
    SEVERITIES,
    STILL_THERE_M,
    TYPES,
    can_transition,
    haversine_m,
    in_bounds,
    place_for,
    type_label,
    within_radius,
)
from wardwatch_api.map_cache import bust
from wardwatch_api.models import Confirmation, Ticket, TicketMedia, User
from wardwatch_api.serialize import add_event

DUP_METERS = 50.0
DUP_COSINE = 0.82


class DomainError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


def next_public_id(db: Session) -> str:
    n = db.query(func.count(Ticket.id)).scalar() or 0
    return f"WW-24-{n + 1:04d}"


def find_duplicate(
    db: Session, *, typ: str, lat: float, lng: float, body: str
) -> Ticket | None:
    vec = embed_text(f"{typ} | {body}")
    opens = db.query(Ticket).filter(Ticket.status == "open", Ticket.type == typ).all()
    best: Ticket | None = None
    best_score = DUP_COSINE
    for t in opens:
        if haversine_m(lat, lng, t.lat, t.lng) > DUP_METERS:
            continue
        score = cosine(vec, embed_text(f"{t.type} | {t.body}"))
        if score >= best_score:
            best = t
            best_score = score
    return best


def submit_report(
    db: Session,
    *,
    user: User,
    lat: float,
    lng: float,
    origin_lat: float,
    origin_lng: float,
    typ: str,
    severity: str,
    body: str,
    media_id: str | None,
    confirmed: bool,
) -> tuple[Ticket, str]:
    if not confirmed:
        raise DomainError(400, "VALIDATION", "Confirm a category before submitting")
    if typ not in TYPES:
        raise DomainError(400, "VALIDATION", "Invalid type")
    if severity not in SEVERITIES:
        raise DomainError(400, "VALIDATION", "Pick how serious this is")
    if len(body.strip()) < 20:
        raise DomainError(400, "VALIDATION", "Write at least 20 characters")
    if not in_bounds(origin_lat, origin_lng):
        raise DomainError(400, "OUT_OF_BOUNDS", "Your location must be inside Hyderabad")
    if not in_bounds(lat, lng):
        raise DomainError(400, "OUT_OF_BOUNDS", "Pin must be inside Hyderabad")
    if not within_radius(lat, lng, origin_lat, origin_lng, RADIUS_M):
        raise DomainError(
            400,
            "OUT_OF_RADIUS",
            "Pin must be within 20 km of your live location",
        )

    media = db.get(TicketMedia, media_id) if media_id else None
    dup = find_duplicate(db, typ=typ, lat=lat, lng=lng, body=body)
    if dup:
        dup.confirmation_count += 1
        if media:
            media.ticket_id = dup.id
        db.add(
            Confirmation(
                ticket_id=dup.id,
                author_id=user.id,
                media_id=media.id if media else None,
                note=body,
            )
        )
        db.add(add_event(dup.id, "duplicate_attached", {"by": user.id}))
        _refresh_embedding(dup)
        db.commit()
        db.refresh(dup)
        _index_ticket(dup)
        bust()
        return dup, "attached"

    place = place_for(lat, lng)
    ticket = Ticket(
        public_id=next_public_id(db),
        author_id=user.id,
        status="open",
        type=typ,
        severity=severity,
        lat=lat,
        lng=lng,
        neighborhood=place["neighborhood"],
        circle=place["circle"],
        ward=place["ward"],
        title=f"{type_label(typ)} · {place['ward']}",
        body=body.strip(),
        confirmation_count=1,
    )
    ticket.set_embedding(
        embed_text(
            f"{typ} | {place['ward']} | {place['circle_label']} | {severity} | open | {body}"
        )
    )
    db.add(ticket)
    db.flush()
    if media:
        media.ticket_id = ticket.id
    db.add(add_event(ticket.id, "created", {}))
    db.commit()
    db.refresh(ticket)
    _index_ticket(ticket)
    bust()
    return ticket, "created"


def confirm_still(
    db: Session, ticket: Ticket, user: User, lat: float, lng: float
) -> Ticket:
    if ticket.status not in ("open", "in_review"):
        raise DomainError(400, "VALIDATION", "This issue is already closed")
    if not in_bounds(lat, lng):
        raise DomainError(400, "OUT_OF_BOUNDS", "Your location must be inside Hyderabad")
    if haversine_m(lat, lng, ticket.lat, ticket.lng) > STILL_THERE_M:
        raise DomainError(
            400,
            "TOO_FAR",
            "Stand within 400 m of the pin to confirm it is still there",
        )
    already = (
        db.query(Confirmation)
        .filter(Confirmation.ticket_id == ticket.id, Confirmation.author_id == user.id)
        .first()
    )
    if already:
        raise DomainError(400, "ALREADY", "You already confirmed this issue")
    ticket.confirmation_count += 1
    db.add(Confirmation(ticket_id=ticket.id, author_id=user.id, note="still there"))
    db.add(add_event(ticket.id, "still_there", {"by": user.id}))
    _refresh_embedding(ticket)
    db.commit()
    db.refresh(ticket)
    _index_ticket(ticket)
    bust()
    return ticket


def _index_ticket(ticket: Ticket) -> None:
    if os.getenv("WARDWATCH_SEED") == "0":
        return
    try:
        from wardwatch_api.rag import ticket_blob
        from wardwatch_api.vectors import ensure_indexed

        ensure_indexed([(ticket.public_id, ticket_blob(ticket))])
    except Exception:
        logging.getLogger(__name__).exception("ticket index failed")


def _refresh_embedding(ticket: Ticket) -> None:
    note = ticket.resolve_note or ""
    ticket.set_embedding(
        embed_text(
            f"{ticket.type} | {ticket.ward} | {ticket.circle} | {ticket.severity} | {ticket.status} | {ticket.body} | {note} | confirmations: {ticket.confirmation_count}"
        )
    )


def change_status(
    db: Session,
    ticket: Ticket,
    new_status: str,
    note: str,
    actor: User,
    fix_media_id: str | None = None,
) -> Ticket:
    if actor.role != "admin":
        raise DomainError(403, "FORBIDDEN", "Admin only")
    if not can_transition(ticket.status, new_status):
        raise DomainError(400, "VALIDATION", f"Cannot go from {ticket.status} to {new_status}")
    if len(note.strip()) < 20:
        raise DomainError(400, "VALIDATION", "A note of at least 20 characters is required")
    if new_status == "resolved":
        if not fix_media_id:
            raise DomainError(400, "VALIDATION", "A photo of the fix is required")
        media = db.get(TicketMedia, fix_media_id)
        if not media:
            raise DomainError(400, "VALIDATION", "Fix photo was not uploaded")
        media.ticket_id = ticket.id
        media.kind = "fix"
        ticket.fix_media_id = media.id
    prev = ticket.status
    ticket.status = new_status
    ticket.resolve_note = note.strip()
    if new_status in ("resolved", "rejected"):
        ticket.resolved_at = datetime.now(timezone.utc)
    _refresh_embedding(ticket)
    db.add(add_event(ticket.id, "status_changed", {"from": prev, "to": new_status}))
    db.commit()
    db.refresh(ticket)
    _index_ticket(ticket)
    bust()
    return ticket
