from fastapi.testclient import TestClient

from wardwatch_api.main import app

client = TestClient(app)


def test_signin_ok():
    client.post(
        "/v1/auth/signup",
        json={"email": "ada@example.com", "password": "street123"},
    )
    client.post("/v1/auth/signout")
    res = client.post(
        "/v1/auth/signin",
        json={"email": "ada@example.com", "password": "street123"},
    )
    assert res.status_code == 200
    assert res.json()["user"]["email"] == "ada@example.com"
    assert "ww_session" in res.cookies
    me = client.get("/v1/auth/me")
    assert me.status_code == 200


def test_signin_wrong_password():
    client.post(
        "/v1/auth/signup",
        json={"email": "ada@example.com", "password": "street123"},
    )
    client.post("/v1/auth/signout")
    res = client.post(
        "/v1/auth/signin",
        json={"email": "ada@example.com", "password": "wrongpass"},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"
