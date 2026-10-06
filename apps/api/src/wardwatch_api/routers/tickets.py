from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from wardwatch_api.db import SessionLocal, get_db
from wardwatch_api.deps import current_user
from wardwatch_api.errors import error_response
from wardwatch_api.geo import haversine_m
from wardwatch_api.media import ALLOWED_TYPES, MAX_BYTES, path_for, save_stripped_jpeg
from wardwatch_api.models import IdempotencyKey, Ticket, TicketMedia, User, VisionJob
from wardwatch_api.reports import DomainError, confirm_still, submit_report
from wardwatch_api.serialize import ticket_public
from wardwatch_api.vision import process_vision_job

router = APIRouter(tags=["tickets"])


class ReportBody(BaseModel):
    lat: float
    lng: float
    origin_lat: float
    origin_lng: float
    type: str
    severity: str
    body: str = Field(min_length=20, max_length=2000)
    media_id: str | None = None
    category_confirmed: bool = False


class ConfirmBody(BaseModel):
    lat: float
    lng: float


def _run_vision(job_id: str) -> None:
    db = SessionLocal()
    try:
        process_vision_job(db, job_id)
    finally:
        db.close()


@router.post("/v1/uploads")
async def upload(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    request_id = request.state.request_id
    if file.content_type not in ALLOWED_TYPES:
        return error_response(400, "VALIDATION", "Only jpeg, png, or webp", request_id)
    data = await file.read()
    if len(data) > MAX_BYTES:
        return error_response(400, "VALIDATION", "Image too large (8 MB)", request_id)
    media = TicketMedia(r2_key="pending", kind="stripped_jpeg")
    db.add(media)
    db.flush()
    save_stripped_jpeg(data, media.id)
    media.r2_key = str(path_for(media.id))
    job = VisionJob(media_id=media.id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(media)
    db.refresh(job)
    background.add_task(_run_vision, job.id)
    return JSONResponse(
        {
            "media_id": media.id,
            "job_id": job.id,
            "request_id": request_id,
        },
        headers={"X-Request-Id": request_id},
    )


@router.get("/v1/vision/{job_id}")
def vision_status(job_id: str, request: Request, db: Session = Depends(get_db)):
    request_id = request.state.request_id
    job = db.get(VisionJob, job_id)
    if not job:
        return error_response(404, "NOT_FOUND", "No vision job", request_id)
    return {
        "id": job.id,
        "status": job.status,
        "suggested_type": job.suggested_type,
        "confidence": job.confidence,
        "model_name": job.model_name,
        "unrelated": job.error == "unrelated",
        "request_id": request_id,
    }


@router.get("/v1/media/{media_id}")
def get_media(media_id: str, request: Request, db: Session = Depends(get_db)):
    media = db.get(TicketMedia, media_id)
    path = path_for(media_id)
    if not media or not path.exists():
        return error_response(404, "NOT_FOUND", "No image", request.state.request_id)
    return FileResponse(path, media_type="image/jpeg")


@router.post("/v1/reports")
def create_report(
    request: Request,
    body: ReportBody,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    request_id = request.state.request_id
    if idempotency_key:
        existing = db.get(IdempotencyKey, idempotency_key)
        if existing and existing.user_id == user.id:
            return JSONResponse(
                json.loads(existing.response_json),
                headers={"X-Request-Id": request_id, "X-Idempotent-Replay": "1"},
            )
    try:
        ticket, action = submit_report(
            db,
            user=user,
            lat=body.lat,
            lng=body.lng,
            origin_lat=body.origin_lat,
            origin_lng=body.origin_lng,
            typ=body.type,
            severity=body.severity,
            body=body.body,
            media_id=body.media_id,
            confirmed=body.category_confirmed,
        )
    except DomainError as exc:
        return error_response(exc.status, exc.code, exc.message, request_id)
    payload = {
        "action": action,
        "ticket": ticket_public(ticket),
        "request_id": request_id,
    }
    if idempotency_key:
        db.add(
            IdempotencyKey(
                key=idempotency_key,
                user_id=user.id,
                response_json=json.dumps(payload),
            )
        )
        db.commit()
    return JSONResponse(payload, headers={"X-Request-Id": request_id})


@router.post("/v1/tickets/{public_id}/confirm")
def confirm_ticket(
    public_id: str,
    body: ConfirmBody,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    request_id = request.state.request_id
    ticket = db.query(Ticket).filter(Ticket.public_id == public_id).first()
    if not ticket:
        return error_response(404, "NOT_FOUND", "No ticket with that id", request_id)
    try:
        ticket = confirm_still(db, ticket, user, body.lat, body.lng)
    except DomainError as exc:
        return error_response(exc.status, exc.code, exc.message, request_id)
    return {"ticket": ticket_public(ticket, include_events=True), "request_id": request_id}


@router.get("/v1/tickets/{public_id}")
def get_ticket(public_id: str, request: Request, db: Session = Depends(get_db)):
    request_id = request.state.request_id
    t = db.query(Ticket).filter(Ticket.public_id == public_id).first()
    if not t:
        return error_response(404, "NOT_FOUND", "No ticket with that id", request_id)
    nearby = []
    for other in (
        db.query(Ticket)
        .filter(Ticket.id != t.id, Ticket.status == "open")
        .limit(50)
        .all()
    ):
        d = haversine_m(t.lat, t.lng, other.lat, other.lng)
        if d <= 150:
            nearby.append({**ticket_public(other), "meters": round(d)})
    data = ticket_public(t, include_events=True)
    data["nearby"] = nearby
    data["request_id"] = request_id
    return data


@router.get("/v1/me/tickets")
def my_tickets(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    rows = (
        db.query(Ticket)
        .filter(Ticket.author_id == user.id)
        .order_by(Ticket.created_at.desc())
        .all()
    )
    return {
        "tickets": [ticket_public(t) for t in rows],
        "request_id": request.state.request_id,
    }
