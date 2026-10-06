from wardwatch_api.db import SessionLocal
from wardwatch_api.models import User
from wardwatch_api.reports import submit_report
from wardwatch_api.security import hash_password

ORIGIN = {"origin_lat": 17.3616, "origin_lng": 78.4747}


def test_duplicate_attaches_within_50m_same_type():
    db = SessionLocal()
    u1 = User(email="one@x.com", password_hash=hash_password("street123"))
    u2 = User(email="two@x.com", password_hash=hash_password("street123"))
    db.add_all([u1, u2])
    db.commit()
    a, action_a = submit_report(
        db,
        user=u1,
        lat=17.3616,
        lng=78.4747,
        typ="pothole",
        severity="blocks_road",
        body="Deep pothole on the road approaching Charminar hurting bikes.",
        media_id=None,
        confirmed=True,
        **ORIGIN,
    )
    assert action_a == "created"
    b, action_b = submit_report(
        db,
        user=u2,
        lat=17.3617,
        lng=78.4748,
        typ="pothole",
        severity="blocks_road",
        body="Deep pothole on the road approaching Charminar hurting bikes.",
        media_id=None,
        confirmed=True,
        **ORIGIN,
    )
    assert action_b == "attached"
    assert b.id == a.id
    assert b.confirmation_count == 2
    db.close()


def test_farther_than_50m_creates_new_pin():
    db = SessionLocal()
    u1 = User(email="one@x.com", password_hash=hash_password("street123"))
    db.add(u1)
    db.commit()
    a, _ = submit_report(
        db,
        user=u1,
        lat=17.3616,
        lng=78.4747,
        typ="garbage",
        severity="smell",
        body="Bags of trash piled beside the drain after market hours today.",
        media_id=None,
        confirmed=True,
        **ORIGIN,
    )
    b, action = submit_report(
        db,
        user=u1,
        lat=17.385,
        lng=78.486,
        typ="garbage",
        severity="smell",
        body="Bags of trash piled beside the drain after market hours today.",
        media_id=None,
        confirmed=True,
        **ORIGIN,
    )
    assert action == "created"
    assert b.id != a.id
    db.close()


def test_same_spot_different_type_creates_new_pin():
    db = SessionLocal()
    u1 = User(email="one@x.com", password_hash=hash_password("street123"))
    db.add(u1)
    db.commit()
    a, _ = submit_report(
        db,
        user=u1,
        lat=17.3616,
        lng=78.4747,
        typ="pothole",
        severity="blocks_road",
        body="Broken road surface and a hole that fills with monsoon water.",
        media_id=None,
        confirmed=True,
        **ORIGIN,
    )
    b, action = submit_report(
        db,
        user=u1,
        lat=17.3616,
        lng=78.4747,
        typ="dumping",
        severity="smell",
        body="Debris dumped beside the same junction entirely this week.",
        media_id=None,
        confirmed=True,
        **ORIGIN,
    )
    assert action == "created"
    assert b.id != a.id
    db.close()
