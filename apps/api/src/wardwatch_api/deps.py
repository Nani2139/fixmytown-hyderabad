from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from wardwatch_api.db import get_db
from wardwatch_api.errors import error_response
from wardwatch_api.models import User
from wardwatch_api.security import user_id_from_request


class AuthError(Exception):
    def __init__(self, response):
        self.response = response


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    request_id = request.state.request_id
    uid = user_id_from_request(request)
    if not uid:
        raise AuthError(
            error_response(401, "UNAUTHORIZED", "Sign in required", request_id)
        )
    user = db.get(User, uid)
    if not user:
        raise AuthError(
            error_response(401, "UNAUTHORIZED", "Sign in required", request_id)
        )
    return user


def admin_user(request: Request, user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise AuthError(
            error_response(
                403, "FORBIDDEN", "Admin only", request.state.request_id
            )
        )
    return user
