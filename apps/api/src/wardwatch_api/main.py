from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy import text

from wardwatch_api import models as _models  # noqa: F401 — register all tables
from wardwatch_api.city import load_cities, load_city
from wardwatch_api.db import Base, SessionLocal, engine, ensure_ticket_columns
from wardwatch_api.deps import AuthError
from wardwatch_api.errors import error_response
from wardwatch_api.routers.admin import router as admin_router
from wardwatch_api.routers.ask import router as ask_router
from wardwatch_api.routers.auth import router as auth_router
from wardwatch_api.routers.map import router as map_router
from wardwatch_api.routers.tickets import router as tickets_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_ticket_columns()
    from wardwatch_api.vectors import reindex_all

    reindex_all()
    yield


app = FastAPI(title="WardWatch API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(map_router)
app.include_router(tickets_router)
app.include_router(admin_router)
app.include_router(ask_router)


@app.exception_handler(AuthError)
async def auth_error_handler(_request: Request, exc: AuthError):
    return exc.response


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:
        logging.getLogger("wardwatch").exception("request failed")
        return error_response(
            500,
            "INTERNAL",
            "Unexpected error",
            request_id,
        )
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/health")
def health(request: Request) -> JSONResponse:
    request_id = request.state.request_id
    return JSONResponse(
        content={
            "status": "ok",
            "service": "api",
            "request_id": request_id,
        },
        headers={"X-Request-Id": request_id},
    )


@app.get("/ready")
def ready(request: Request) -> JSONResponse:
    request_id = request.state.request_id
    try:
        city = load_city()
        cities = load_cities()
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        return error_response(
            503,
            "NOT_READY",
            "City file or database is not ready",
            request_id,
        )
    return JSONResponse(
        content={
            "status": "ok",
            "service": "api",
            "city": city["name"],
            "cities": [c["name"] for c in cities],
            "request_id": request_id,
        },
        headers={"X-Request-Id": request_id},
    )
