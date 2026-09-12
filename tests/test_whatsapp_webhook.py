"""WhatsApp webhook verification tests."""

from fastapi.testclient import TestClient

from businessflow_ai.api import app
from businessflow_ai.config import get_settings


def test_whatsapp_webhook_verification(monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "vega-test-token")
    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get(
        "/api/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "vega-test-token",
            "hub.challenge": "123456",
        },
    )

    assert response.status_code == 200
    assert response.text == "123456"
    get_settings.cache_clear()


def test_whatsapp_webhook_rejects_wrong_token(monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "vega-test-token")
    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get(
        "/api/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "123456",
        },
    )

    assert response.status_code == 403
    get_settings.cache_clear()
