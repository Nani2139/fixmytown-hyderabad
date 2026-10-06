from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class FirebaseAuthError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


def public_config() -> dict | None:
    fields = {
        "apiKey": os.getenv("FIREBASE_API_KEY", "").strip(),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", "").strip(),
        "projectId": os.getenv("FIREBASE_PROJECT_ID", "").strip(),
        "appId": os.getenv("FIREBASE_APP_ID", "").strip(),
    }
    if not all(fields.values()):
        return None
    return fields


def lookup_google_user(id_token: str) -> dict:
    key = os.getenv("FIREBASE_API_KEY", "").strip()
    if not key:
        raise FirebaseAuthError(503, "NOT_CONFIGURED", "Google sign-in is not configured yet.")
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={key}"
    req = urllib.request.Request(
        url,
        data=json.dumps({"idToken": id_token}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise FirebaseAuthError(401, "UNAUTHORIZED", "Google sign-in was rejected.") from exc
    except urllib.error.URLError as exc:
        raise FirebaseAuthError(503, "NOT_READY", "Could not reach Google sign-in.") from exc
    users = payload.get("users") or []
    if not users:
        raise FirebaseAuthError(401, "UNAUTHORIZED", "Google sign-in was rejected.")
    user = users[0]
    providers = {item.get("providerId") for item in user.get("providerUserInfo") or []}
    if "google.com" not in providers:
        raise FirebaseAuthError(401, "UNAUTHORIZED", "Use a Google account.")
    email = (user.get("email") or "").strip().lower()
    if not email:
        raise FirebaseAuthError(401, "UNAUTHORIZED", "That Google account has no email.")
    return {"email": email, "uid": user.get("localId") or ""}
