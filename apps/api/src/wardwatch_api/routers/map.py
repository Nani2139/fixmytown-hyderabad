from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from wardwatch_api.db import get_db
from wardwatch_api.errors import error_response
from wardwatch_api.geo import RADIUS_M, city, haversine_m, in_bounds, place_for
from wardwatch_api.map_cache import get as cache_get
from wardwatch_api.map_cache import set as cache_set
from wardwatch_api.models import Confirmation, Ticket
from wardwatch_api.serialize import geojson_feature, recently_fixed_cutoff

router = APIRouter(tags=["map"])


@router.get("/v1/city")
def get_city(request: Request):
    return JSONResponse(
        {"city": city(), "request_id": request.state.request_id},
        headers={"X-Request-Id": request.state.request_id},
    )


def _week_counts(db: Session, ids: list[str]) -> dict[str, int]:
    if not ids:
        return {}
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    rows = (
        db.query(Confirmation.ticket_id, func.count(Confirmation.id))
        .filter(Confirmation.ticket_id.in_(ids), Confirmation.created_at >= week_ago)
        .group_by(Confirmation.ticket_id)
        .all()
    )
    return {ticket_id: int(n) for ticket_id, n in rows}


def _collect(
    db: Session,
    *,
    status: str,
    typ: str | None,
    south: float,
    north: float,
    west: float,
    east: float,
    origin_lat: float | None = None,
    origin_lng: float | None = None,
    radius_m: float | None = None,
) -> list[tuple[Ticket, int | None]]:
    q = db.query(Ticket).options(joinedload(Ticket.media)).filter(
        Ticket.lat >= south,
        Ticket.lat <= north,
        Ticket.lng >= west,
        Ticket.lng <= east,
    )
    if typ:
        q = q.filter(Ticket.type == typ)
    if status == "open":
        q = q.filter(Ticket.status == "open")
    elif status == "recently_fixed":
        q = q.filter(
            Ticket.status == "resolved",
            Ticket.resolved_at != None,  # noqa: E711
            Ticket.resolved_at >= recently_fixed_cutoff(),
        )
    else:
        q = q.filter(Ticket.status == status)
    rows: list[tuple[Ticket, int | None]] = []
    for ticket in q.limit(800).all():
        distance = None
        if origin_lat is not None and origin_lng is not None:
            distance = int(round(haversine_m(origin_lat, origin_lng, ticket.lat, ticket.lng)))
            if radius_m is not None and distance > radius_m:
                continue
        rows.append((ticket, distance))
    rows.sort(key=lambda item: (item[1] if item[1] is not None else 10**9, -item[0].confirmation_count))
    return rows[:500]


@router.get("/v1/map")
def get_map(
    request: Request,
    bbox: str | None = Query(default=None, description="w,s,e,n"),
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float = Query(20, ge=1, le=20),
    status: str = Query("open"),
    type: str | None = None,
    db: Session = Depends(get_db),
):
    request_id = request.state.request_id
    origin = lat is not None and lng is not None
    if origin:
        if not in_bounds(lat, lng):
            return error_response(400, "OUT_OF_BOUNDS", "Location must be inside Hyderabad", request_id)
        pad_lat = radius_km / 111
        pad_lng = radius_km / 105
        west, south, east, north = lng - pad_lng, lat - pad_lat, lng + pad_lng, lat + pad_lat
        radius_m = radius_km * 1000
        key = f"map:v2:{status}:{type or 'all'}:{round(lat, 3)}:{round(lng, 3)}:{radius_km}"
    elif bbox:
        try:
            west, south, east, north = [float(x) for x in bbox.split(",")]
        except ValueError:
            return error_response(400, "VALIDATION", "bbox must be w,s,e,n", request_id)
        radius_m = None
        key = f"map:v2:{status}:{type or 'all'}:{bbox}"
    else:
        return error_response(400, "VALIDATION", "lat and lng are required", request_id)

    cached = cache_get(key)
    if cached:
        return JSONResponse(cached, headers={"X-Request-Id": request_id, "X-Cache": "HIT"})

    rows = _collect(
        db,
        status=status,
        typ=type,
        south=south,
        north=north,
        west=west,
        east=east,
        origin_lat=lat if origin else None,
        origin_lng=lng if origin else None,
        radius_m=radius_m,
    )
    weeks = _week_counts(db, [t.id for t, _ in rows])
    body = {
        "type": "FeatureCollection",
        "features": [
            geojson_feature(t, distance_m=dist, confirmations_week=weeks.get(t.id, 0))
            for t, dist in rows
        ],
        "truncated": len(rows) == 500,
        "request_id": request_id,
    }
    cache_set(key, body)
    return JSONResponse(body, headers={"X-Request-Id": request_id, "X-Cache": "MISS"})


@router.get("/v1/brief")
def brief(
    request: Request,
    lat: float,
    lng: float,
    db: Session = Depends(get_db),
):
    request_id = request.state.request_id
    if not in_bounds(lat, lng):
        return error_response(400, "OUT_OF_BOUNDS", "Location must be inside Hyderabad", request_id)
    place = place_for(lat, lng)
    open_rows = _collect(
        db,
        status="open",
        typ=None,
        south=lat - 0.2,
        north=lat + 0.2,
        west=lng - 0.22,
        east=lng + 0.22,
        origin_lat=lat,
        origin_lng=lng,
        radius_m=RADIUS_M,
    )
    fixed_rows = _collect(
        db,
        status="recently_fixed",
        typ=None,
        south=lat - 0.2,
        north=lat + 0.2,
        west=lng - 0.22,
        east=lng + 0.22,
        origin_lat=lat,
        origin_lng=lng,
        radius_m=RADIUS_M,
    )
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    fixed_yesterday = 0
    for ticket, _dist in fixed_rows:
        resolved = ticket.resolved_at
        if resolved is None:
            continue
        if resolved.tzinfo is None:
            resolved = resolved.replace(tzinfo=timezone.utc)
        if resolved >= yesterday:
            fixed_yesterday += 1
    within_2 = [(t, d) for t, d in open_rows if d is not None and d <= 2000]
    headline = None
    pool = [(t, d) for t, d in open_rows if t.type == "waterlogging"] or open_rows
    if pool:
        ticket, dist = pool[0]
        headline = {
            "public_id": ticket.public_id,
            "type": ticket.type,
            "ward": ticket.ward,
            "circle": ticket.circle,
            "title": ticket.title,
            "meters": dist,
        }
    return {
        "ward": place["ward"],
        "circle": place["circle_label"],
        "open_2km": len(within_2),
        "open_20km": len(open_rows),
        "fixed_yesterday": fixed_yesterday,
        "fixed_recent": len(fixed_rows),
        "headline": headline,
        "request_id": request_id,
    }
