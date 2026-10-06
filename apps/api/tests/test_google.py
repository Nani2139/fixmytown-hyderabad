from wardwatch_api.firebase_auth import public_config
from wardwatch_api.main import app
from fastapi.testclient import TestClient


def test_google_config_is_off_without_firebase(monkeypatch):
    for name in ("FIREBASE_API_KEY", "FIREBASE_AUTH_DOMAIN", "FIREBASE_PROJECT_ID", "FIREBASE_APP_ID"):
        monkeypatch.delenv(name, raising=False)
    client = TestClient(app)
    res = client.get("/v1/auth/config")
    assert res.status_code == 200
    assert res.json()["google"] is False
    assert public_config() is None


def test_google_sign_in_rejects_when_unconfigured(monkeypatch):
    monkeypatch.delenv("FIREBASE_API_KEY", raising=False)
    client = TestClient(app)
    res = client.post("/v1/auth/google", json={"id_token": "x" * 40})
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "NOT_CONFIGURED"
