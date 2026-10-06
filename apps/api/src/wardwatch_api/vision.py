from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request

from sqlalchemy.orm import Session

from wardwatch_api.media import path_for
from wardwatch_api.models import VisionJob

LABELS = (
    "waterlogging",
    "open_manhole",
    "garbage",
    "streetlight",
    "pothole",
    "dug_road",
    "dumping",
    "stagnant_water",
)
ALIASES = {"litter": "garbage", "graffiti": "dumping", "other": "stagnant_water"}


def process_vision_job(db: Session, job_id: str) -> VisionJob | None:
    job = db.get(VisionJob, job_id)
    if not job:
        return None
    job.status = "running"
    db.commit()
    path = path_for(job.media_id)
    try:
        suggested, confidence, model, unrelated = classify_image(path)
        job.suggested_type = suggested
        job.confidence = confidence
        job.model_name = model
        job.status = "succeeded"
        job.error = "unrelated" if unrelated else None
    except Exception as exc:  # noqa: BLE001 — job must always finish
        job.status = "failed"
        job.error = "unavailable"
        job.suggested_type = None
        job.confidence = 0.0
        job.model_name = "none"
    db.commit()
    db.refresh(job)
    return job


# Earlier models are tried first. gemini-3.8-flash often returns 503 under load.
MODELS = (
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
)


def classify_image(path) -> tuple[str | None, float, str, bool]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key and path.exists():
        return _gemini(path, key)
    return None, 0.0, "unavailable", False


def interpret_classification(parsed: dict) -> tuple[str | None, float, bool]:
    """Return type, confidence, and whether the photo is not a street problem."""
    relevant = parsed.get("relevant", True)
    if isinstance(relevant, str):
        relevant = relevant.strip().lower() not in ("false", "no", "0")
    try:
        conf = float(parsed.get("confidence") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))
    raw = str(parsed.get("type") or "").strip().lower()
    if relevant is False or raw in ("", "null", "none", "unrelated", "not_street", "other"):
        return None, conf, True
    typ = ALIASES.get(raw, raw)
    if typ not in LABELS:
        return None, conf, True
    return typ, conf, False


def _gemini(path, key: str) -> tuple[str | None, float, str, bool]:
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    prompt = (
        "Decide if this photo shows a real street problem. "
        "Street problems are only: waterlogging, open_manhole, garbage on a road or footpath, "
        "streetlight, pothole, dug_road, dumping, stagnant_water. "
        "A hole in the road, including one filled with water, is a pothole. "
        "Food, fruit, a banana, a person, a pet, an indoor object, a meme, or a screenshot is not a street problem. "
        "Do not force those into a street category. "
        "Reply JSON only, no markdown: "
        '{"relevant":true,"type":"waterlogging|open_manhole|garbage|streetlight|pothole|dug_road|dumping|stagnant_water|null","confidence":0.0}'
    )
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    payload_bytes = json.dumps(body).encode()
    last_status = 0
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        req = urllib.request.Request(
            url,
            data=payload_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            last_status = exc.code
            exc.read()
            if exc.code in (404, 429, 500, 503):
                continue
            raise RuntimeError(f"vision http {exc.code}") from None
        except urllib.error.URLError:
            last_status = 503
            continue
        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(_json_text(text))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            continue
        typ, conf, unrelated = interpret_classification(parsed)
        return typ, conf, model, unrelated
    raise RuntimeError(f"vision http {last_status or 503}")


def _json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return cleaned.strip()
