from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from wardwatch_api.db import get_db
from wardwatch_api.deps import admin_user
from wardwatch_api.errors import error_response
from wardwatch_api.models import Ticket, User
from wardwatch_api.reports import DomainError, change_status
from wardwatch_api.serialize import ticket_public

router = APIRouter(prefix="/v1/admin", tags=["admin"])


class StatusBody(BaseModel):
    status: str
    note: str = Field(min_length=20, max_length=500)
    fix_media_id: str | None = None


@router.get("/tickets")
def list_tickets(
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(admin_user),
    status: str | None = "open",
    type: str | None = None,
):
    q = db.query(Ticket)
    if status:
        q = q.filter(Ticket.status == status)
    if type:
        q = q.filter(Ticket.type == type)
    rows = q.order_by(Ticket.created_at.asc()).all()
    return {
        "tickets": [ticket_public(t) for t in rows],
        "request_id": request.state.request_id,
    }


@router.patch("/tickets/{public_id}")
def patch_ticket(
    public_id: str,
    body: StatusBody,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    request_id = request.state.request_id
    ticket = db.query(Ticket).filter(Ticket.public_id == public_id).first()
    if not ticket:
        return error_response(404, "NOT_FOUND", "No ticket with that id", request_id)
    try:
        ticket = change_status(db, ticket, body.status, body.note, admin, body.fix_media_id)
    except DomainError as exc:
        return error_response(exc.status, exc.code, exc.message, request_id)
    return JSONResponse(
        {"ticket": ticket_public(ticket), "request_id": request_id},
        headers={"X-Request-Id": request_id},
    )
