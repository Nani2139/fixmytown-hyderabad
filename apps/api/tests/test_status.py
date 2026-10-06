from wardwatch_api.db import SessionLocal
from wardwatch_api.geo import can_transition
from wardwatch_api.models import TicketMedia, User
from wardwatch_api.reports import DomainError, change_status, submit_report
from wardwatch_api.security import hash_password


def test_status_machine():
    assert can_transition("open", "resolved")
    assert can_transition("open", "in_review")
    assert can_transition("in_review", "rejected")
    assert not can_transition("resolved", "open")
    assert not can_transition("rejected", "open")


def test_change_status_requires_note_and_admin():
    db = SessionLocal()
    admin = User(email="a@x.com", password_hash=hash_password("street123"), role="admin")
    citizen = User(email="c@x.com", password_hash=hash_password("street123"), role="citizen")
    db.add_all([admin, citizen])
    db.commit()
    ticket, _ = submit_report(
        db,
        user=citizen,
        lat=17.3616,
        lng=78.4747,
        origin_lat=17.3616,
        origin_lng=78.4747,
        typ="pothole",
        severity="blocks_road",
        body="Deep hole on the Charminar approach blocking the left lane daily.",
        media_id=None,
        confirmed=True,
    )
    media = TicketMedia(r2_key="fix", kind="fix")
    db.add(media)
    db.commit()
    try:
        change_status(db, ticket, "resolved", "too short", admin)
        assert False
    except DomainError as exc:
        assert exc.code == "VALIDATION"
    try:
        change_status(
            db,
            ticket,
            "resolved",
            "Filled the stretch after a crew visit this week.",
            citizen,
        )
        assert False
    except DomainError as exc:
        assert exc.code == "FORBIDDEN"
    try:
        change_status(
            db,
            ticket,
            "resolved",
            "Filled the stretch after a crew visit this week.",
            admin,
        )
        assert False
    except DomainError as exc:
        assert exc.code == "VALIDATION"
    updated = change_status(
        db,
        ticket,
        "resolved",
        "Filled the stretch after a crew visit this week.",
        admin,
        media.id,
    )
    assert updated.status == "resolved"
    db.close()
