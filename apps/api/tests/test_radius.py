from wardwatch_api.db import SessionLocal
from wardwatch_api.models import User
from wardwatch_api.reports import DomainError, confirm_still, submit_report
from wardwatch_api.security import hash_password


def _user(db, email="one@x.com"):
    user = User(email=email, password_hash=hash_password("street123"))
    db.add(user)
    db.commit()
    return user


def test_pin_outside_hyderabad_is_rejected():
    db = SessionLocal()
    user = _user(db)
    try:
        submit_report(
            db,
            user=user,
            lat=12.9716,
            lng=77.5946,
            origin_lat=17.3616,
            origin_lng=78.4747,
            typ="pothole",
            severity="blocks_road",
            body="This pin is in another city and must be rejected outright.",
            media_id=None,
            confirmed=True,
        )
        assert False
    except DomainError as exc:
        assert exc.code == "OUT_OF_BOUNDS"
    db.close()


def test_pin_beyond_20km_is_rejected():
    db = SessionLocal()
    user = _user(db)
    try:
        submit_report(
            db,
            user=user,
            lat=17.56,
            lng=78.4747,
            origin_lat=17.3616,
            origin_lng=78.4747,
            typ="pothole",
            severity="blocks_road",
            body="This pin is inside the city but outside the 20 km circle.",
            media_id=None,
            confirmed=True,
        )
        assert False
    except DomainError as exc:
        assert exc.code == "OUT_OF_RADIUS"
    db.close()


def test_still_there_requires_being_near_the_pin():
    db = SessionLocal()
    author = _user(db, "author@x.com")
    neighbor = _user(db, "near@x.com")
    ticket, _ = submit_report(
        db,
        user=author,
        lat=17.3616,
        lng=78.4747,
        origin_lat=17.3616,
        origin_lng=78.4747,
        typ="open_manhole",
        severity="night_danger",
        body="Open manhole with no cover on the lane beside Charminar.",
        media_id=None,
        confirmed=True,
    )
    try:
        confirm_still(db, ticket, neighbor, 17.44, 78.39)
        assert False
    except DomainError as exc:
        assert exc.code == "TOO_FAR"
    updated = confirm_still(db, ticket, neighbor, 17.3616, 78.4747)
    assert updated.confirmation_count == 2
    db.close()
