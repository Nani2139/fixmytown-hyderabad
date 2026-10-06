from __future__ import annotations

import os
from pathlib import Path

MEDIA_DIR = Path(os.getenv("MEDIA_DIR", "media"))
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_BYTES = 8 * 1024 * 1024


def save_stripped_jpeg(data: bytes, media_id: str) -> Path:
    from io import BytesIO

    from PIL import Image

    img = Image.open(BytesIO(data))
    img = img.convert("RGB")
    longest = max(img.size)
    if longest > 1600:
        ratio = 1600 / longest
        img = img.resize((int(img.width * ratio), int(img.height * ratio)))
    path = MEDIA_DIR / f"{media_id}.jpg"
    img.save(path, format="JPEG", quality=82, optimize=True)
    return path


def path_for(media_id: str) -> Path:
    return MEDIA_DIR / f"{media_id}.jpg"
