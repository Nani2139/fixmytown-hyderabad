from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wardwatch.db")

# SQLite needs this for FastAPI's multi-thread test client.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def ensure_ticket_columns() -> None:
    """Add columns on databases created before circle, ward, and severity."""
    insp = inspect(engine)
    if not insp.has_table("tickets"):
        return
    have = {c["name"] for c in insp.get_columns("tickets")}
    alters = {
        "circle": "ALTER TABLE tickets ADD COLUMN circle VARCHAR(64) DEFAULT ''",
        "ward": "ALTER TABLE tickets ADD COLUMN ward VARCHAR(80) DEFAULT ''",
        "severity": "ALTER TABLE tickets ADD COLUMN severity VARCHAR(32) DEFAULT 'smell'",
        "fix_media_id": "ALTER TABLE tickets ADD COLUMN fix_media_id VARCHAR(36)",
    }
    with engine.begin() as conn:
        for name, sql in alters.items():
            if name not in have:
                conn.execute(text(sql))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
