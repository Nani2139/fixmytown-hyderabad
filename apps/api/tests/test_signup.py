from fastapi.testclient import TestClient

from wardwatch_api.main import app

client = TestClient(app)


def test_signup_creates_user_and_sets_cookie():
    res = client.post(
        "/v1/auth/signup",
        json={"email": "ada@example.com", "password": "street123"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["role"] == "citizen"
    assert "password" not in body["user"]
    assert "ww_session" in res.cookies


def test_signup_duplicate_email_conflict():
    payload = {"email": "ada@example.com", "password": "street123"}
    assert client.post("/v1/auth/signup", json=payload).status_code == 201
    res = client.post("/v1/auth/signup", json=payload)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "EMAIL_TAKEN"


def test_me_requires_cookie():
    res = client.get("/v1/auth/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_after_signup():
    client.post(
        "/v1/auth/signup",
        json={"email": "ada@example.com", "password": "street123"},
    )
    res = client.get("/v1/auth/me")
    assert res.status_code == 200
    assert res.json()["user"]["email"] == "ada@example.com"
