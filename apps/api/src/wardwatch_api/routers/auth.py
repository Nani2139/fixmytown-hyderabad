from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from wardwatch_api.db import get_db
from wardwatch_api.errors import error_response
from wardwatch_api.firebase_auth import FirebaseAuthError, lookup_google_user, public_config
from wardwatch_api.models import User
from wardwatch_api.security import (
    SESSION_COOKIE,
    hash_password,
    set_session_cookie,
    user_id_from_request,
    verify_password,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class SignupBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class SigninBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class GoogleBody(BaseModel):
    id_token: str = Field(min_length=20, max_length=8192)


def user_public(user: User) -> dict:
    return {"id": user.id, "email": user.email, "role": user.role}


@router.get("/config")
def auth_config(request: Request):
    request_id = request.state.request_id
    config = public_config()
    return JSONResponse(
        content={"google": config is not None, "firebase": config, "request_id": request_id},
        headers={"X-Request-Id": request_id},
    )


@router.post("/google")
def google_sign_in(request: Request, body: GoogleBody, db: Session = Depends(get_db)):
    request_id = request.state.request_id
    try:
        profile = lookup_google_user(body.id_token)
    except FirebaseAuthError as exc:
        return error_response(exc.status, exc.code, exc.message, request_id)
    email = profile["email"]
    admins = {item.strip().lower() for item in os.getenv("ADMIN_EMAILS", "").split(",") if item.strip()}
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role="admin" if email in admins else "citizen",
        )
        db.add(user)
    elif email in admins and user.role != "admin":
        user.role = "admin"
    db.commit()
    db.refresh(user)
    res = JSONResponse(
        content={"user": user_public(user), "request_id": request_id},
        headers={"X-Request-Id": request_id},
    )
    set_session_cookie(res, user.id)
    return res


@router.post("/signup")
def signup(request: Request, body: SignupBody, db: Session = Depends(get_db)):
    request_id = request.state.request_id
    existing = db.query(User).filter(User.email == body.email.lower()).first()
    if existing:
        return error_response(
            409, "EMAIL_TAKEN", "An account with that email exists", request_id
        )
    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        role="citizen",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    res = JSONResponse(
        status_code=201,
        content={"user": user_public(user), "request_id": request_id},
        headers={"X-Request-Id": request_id},
    )
    set_session_cookie(res, user.id)
    return res


@router.post("/signin")
def signin(request: Request, body: SigninBody, db: Session = Depends(get_db)):
    request_id = request.state.request_id
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        return error_response(401, "UNAUTHORIZED", "Sign in required", request_id)
    res = JSONResponse(
        content={"user": user_public(user), "request_id": request_id},
        headers={"X-Request-Id": request_id},
    )
    set_session_cookie(res, user.id)
    return res


@router.post("/signout")
def signout(request: Request):
    request_id = request.state.request_id
    res = JSONResponse(
        content={"ok": True, "request_id": request_id},
        headers={"X-Request-Id": request_id},
    )
    res.delete_cookie(SESSION_COOKIE, path="/")
    return res


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    request_id = request.state.request_id
    user_id = user_id_from_request(request)
    if not user_id:
        return error_response(401, "UNAUTHORIZED", "Sign in required", request_id)
    user = db.get(User, user_id)
    if not user:
        return error_response(401, "UNAUTHORIZED", "Sign in required", request_id)
    return JSONResponse(
        content={"user": user_public(user), "request_id": request_id},
        headers={"X-Request-Id": request_id},
    )
