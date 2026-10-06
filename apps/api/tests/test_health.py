from fastapi.testclient import TestClient

from wardwatch_api.main import app

client = TestClient(app)


def test_health_ok():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["service"] == "api"
    assert "request_id" in body
    assert res.headers["X-Request-Id"] == body["request_id"]


def test_health_echoes_incoming_request_id():
    res = client.get("/health", headers={"X-Request-Id": "learn-123"})
    assert res.headers["X-Request-Id"] == "learn-123"
    assert res.json()["request_id"] == "learn-123"
