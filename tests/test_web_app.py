"""Security and owner-interface smoke tests."""

from fastapi.testclient import TestClient

from businessflow_ai.api import app


def test_owner_interface_and_security_headers() -> None:
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "Tell Vega the outcome" in response.text
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_dashboard_requires_authenticated_owner() -> None:
    client = TestClient(app)
    assert client.get("/api/dashboard").status_code == 401


def test_mutation_requires_csrf_token() -> None:
    client = TestClient(app)
    response = client.post("/api/goals", json={"goal": "Schedule a meeting"})
    assert response.status_code == 403


def test_session_uses_http_only_signed_cookie() -> None:
    client = TestClient(app)
    response = client.get("/api/session")

    assert response.status_code == 200
    assert response.json()["authenticated"] is False
    cookie = response.headers["set-cookie"]
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()
