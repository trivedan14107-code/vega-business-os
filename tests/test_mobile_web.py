"""Mobile web and installable app shell checks."""

from fastapi.testclient import TestClient

from businessflow_ai.api import app


def test_mobile_app_manifest_is_available() -> None:
    client = TestClient(app)

    response = client.get("/static/manifest.webmanifest")

    assert response.status_code == 200
    manifest = response.json()
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/"
    assert manifest["icons"]


def test_service_worker_has_root_scope_and_does_not_cache_api_data() -> None:
    client = TestClient(app)

    response = client.get("/sw.js")

    assert response.status_code == 200
    assert response.headers["service-worker-allowed"] == "/"
    assert response.headers["cache-control"] == "no-cache"
    assert 'url.pathname.startsWith("/api/")' in response.text
