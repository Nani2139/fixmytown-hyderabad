from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import urllib.error
import urllib.request

DIM = 128
EMBED_DIM = 768
EMBED_MODEL = "gemini-embedding-001"
TOKEN = re.compile(r"[a-z0-9]+")
log = logging.getLogger(__name__)


def embed_text(text: str) -> list[float]:
    """Cheap hashed-bag embedding. Swap for MiniLM later without changing callers."""
    vec = [0.0] * DIM
    for tok in TOKEN.findall(text.lower()):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % DIM] += 1.0
        vec[(h >> 8) % DIM] += 0.35
    return _l2(vec)


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def embed_semantic(text: str, task: str) -> list[float] | None:
    """Real embedding for Ask. task is RETRIEVAL_QUERY or RETRIEVAL_DOCUMENT."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    cleaned = " ".join(text.split())
    if not key or not cleaned:
        return None
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{EMBED_MODEL}:embedContent?key={key}"
    )
    body = {
        "content": {"parts": [{"text": cleaned[:8000]}]},
        "taskType": task,
        "outputDimensionality": EMBED_DIM,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "FixMyTown/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode())
        values = payload.get("embedding", {}).get("values") or []
        if len(values) != EMBED_DIM:
            log.warning("embedding dim %s", len(values))
            return None
        return [float(v) for v in values]
    except urllib.error.HTTPError as exc:
        log.warning("embedding http %s", exc.code)
        return None
    except Exception:
        log.exception("embedding failed")
        return None


def _l2(vec: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in vec))
    if n == 0:
        return vec
    return [x / n for x in vec]
