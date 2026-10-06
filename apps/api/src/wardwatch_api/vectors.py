from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
from pathlib import Path

import sqlite_vec

from wardwatch_api.embed import EMBED_DIM, embed_semantic

log = logging.getLogger(__name__)

# Cosine distance from sqlite-vec. 0 is identical. Tuned so a nearby pothole
# matches "hole in the road", while "who is the mayor" stays out.
MAX_DISTANCE = 0.36


def vec_db_path() -> Path:
    url = os.getenv("DATABASE_URL", "sqlite:///./wardwatch.db")
    raw = url.split(":///", 1)[-1] if url.startswith("sqlite:") else "wardwatch.db"
    base = Path(raw)
    if not base.is_absolute():
        base = Path.cwd() / base
    return base.with_suffix(".vec.db")


def connect() -> sqlite3.Connection:
    path = vec_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_tickets USING vec0(
            embedding float[{EMBED_DIM}] distance_metric=cosine,
            +public_id text,
            +text_hash text
        )
        """
    )
    return conn


def upsert_vector(public_id: str, vector: list[float], text_hash: str) -> None:
    if len(vector) != EMBED_DIM:
        return
    conn = connect()
    try:
        _replace(conn, public_id, vector, text_hash)
        conn.commit()
    finally:
        conn.close()


def ensure_indexed(items: list[tuple[str, str]]) -> None:
    """Embed ticket text that is missing or has changed. items are (public_id, blob)."""
    if os.getenv("WARDWATCH_SEED") == "0" or not items:
        return
    if not os.getenv("GEMINI_API_KEY", "").strip():
        return
    conn = connect()
    try:
        for public_id, blob in items:
            digest = hashlib.sha256(blob.encode()).hexdigest()
            row = conn.execute(
                "SELECT text_hash FROM vec_tickets WHERE public_id = ?",
                [public_id],
            ).fetchone()
            if row and row[0] == digest:
                continue
            vector = embed_semantic(blob, "RETRIEVAL_DOCUMENT")
            if not vector:
                continue
            _replace(conn, public_id, vector, digest)
        conn.commit()
    finally:
        conn.close()


def dense_rank(query_vec: list[float], allowed: set[str], k: int = 8) -> list[str]:
    if not query_vec or not allowed:
        return []
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT public_id, distance
            FROM vec_tickets
            WHERE embedding MATCH ? AND k = ?
            """,
            [sqlite_vec.serialize_float32(query_vec), 50],
        ).fetchall()
    finally:
        conn.close()
    hits = [
        (public_id, float(distance))
        for public_id, distance in rows
        if public_id in allowed and float(distance) <= MAX_DISTANCE
    ]
    hits.sort(key=lambda item: item[1])
    return [public_id for public_id, _distance in hits[:k]]


def _replace(conn: sqlite3.Connection, public_id: str, vector: list[float], text_hash: str) -> None:
    existing = conn.execute(
        "SELECT rowid FROM vec_tickets WHERE public_id = ?",
        [public_id],
    ).fetchall()
    for (rowid,) in existing:
        conn.execute("DELETE FROM vec_tickets WHERE rowid = ?", [rowid])
    conn.execute(
        "INSERT INTO vec_tickets(embedding, public_id, text_hash) VALUES (?, ?, ?)",
        [sqlite_vec.serialize_float32(vector), public_id, text_hash],
    )


def reindex_all() -> None:
    if os.getenv("WARDWATCH_SEED") == "0":
        return
    from wardwatch_api.db import SessionLocal
    from wardwatch_api.models import Ticket
    from wardwatch_api.rag import ticket_blob

    db = SessionLocal()
    try:
        items = [(ticket.public_id, ticket_blob(ticket)) for ticket in db.query(Ticket).all()]
    finally:
        db.close()
    try:
        ensure_indexed(items)
    except Exception:
        log.exception("ask reindex failed")
