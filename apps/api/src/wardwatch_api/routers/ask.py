from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from wardwatch_api.db import get_db
from wardwatch_api.rag import ask_city

router = APIRouter(tags=["ask"])


class AskBody(BaseModel):
    q: str = Field(min_length=3, max_length=500)
    lat: float
    lng: float
    type: str | None = None


@router.post("/v1/ask")
def ask(body: AskBody, request: Request, db: Session = Depends(get_db)):
    result = ask_city(db, body.q, body.type, body.lat, body.lng)
    result["request_id"] = request.state.request_id
    return result
