"""Slack OAuth, channel selection, and execution tests."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

from businessflow_ai.models import AgentDefinition, OAuthProvider
from businessflow_ai.services import ConnectionStore, TokenVault
from businessflow_ai.services.slack import SlackExecutionEngine, SlackService
from businessflow_ai.services.slack_oauth import SlackOAuthClient


class SlackIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = ConnectionStore(
            Path(self.temp_dir.name) / "slack.db",
            TokenVault(TokenVault.generate_key()),
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_oauth_connects_workspace_and_encrypts_bot_token(self) -> None:
        def oauth_handler(request: httpx.Request) -> httpx.Response:
            self.assertTrue(request.headers["Authorization"].startswith("Basic "))
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "access_token": "test-private-token",
                    "token_type": "bot",
                    "scope": "chat:write,channels:read,groups:read",
                    "bot_user_id": "B123",
                    "app_id": "A123",
                    "team": {"id": "T123", "name": "Vega Test"},
                },
            )

        async def connect() -> None:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(oauth_handler)
            ) as http:
                oauth = SlackOAuthClient(
                    client_id="client-id",
                    client_secret="client-secret",
                    redirect_uri="https://vega.example/api/oauth/slack/callback",
                    connection_store=self.store,
                    http_client=http,
                )
                url = oauth.authorization_url("company-001")
                query = parse_qs(urlparse(url).query)
                self.assertIn("chat:write", query["scope"][0])
                await oauth.complete("temporary-code", query["state"][0])

        asyncio.run(connect())
        token = self.store.get_token("company-001", OAuthProvider.SLACK)
        self.assertEqual(token["team"]["id"], "T123")
        database_text = Path(self.store.database_path).read_bytes().decode(errors="ignore")
        self.assertNotIn("test-private-token", database_text)

    def test_selects_channel_then_posts_and_verifies_meeting_message(self) -> None:
        self.store.save_connection(
            company_id="company-001",
            provider=OAuthProvider.SLACK,
            token={"access_token": "test-private-token", "team": {"id": "T123"}},
            scopes=["chat:write", "channels:read"],
            account_email=None,
        )
        sent_payloads = []

        def slack_handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers["Authorization"], "Bearer test-private-token")
            payload = __import__("json").loads(request.content)
            if request.url.path.endswith("conversations.list"):
                return httpx.Response(
                    200,
                    json={
                        "ok": True,
                        "channels": [
                            {
                                "id": "C123",
                                "name": "general",
                                "is_private": False,
                                "is_member": True,
                            }
                        ],
                    },
                )
            sent_payloads.append(payload)
            return httpx.Response(200, json={"ok": True, "channel": "C123", "ts": "1.2"})

        with httpx.Client(transport=httpx.MockTransport(slack_handler)) as http:
            slack = SlackService(self.store, http)
            slack.select_channel("company-001", "C123")
            engine = SlackExecutionEngine(slack)
            agent = AgentDefinition(
                company_id="company-001",
                role="communication",
                responsibilities=["Notify the team"],
            )
            result = engine.execute(
                agent,
                "Schedule and inform the team",
                [
                    {
                        "role": "meeting",
                        "title": "Leadership sync",
                        "start_time": "2026-09-13T10:00:00+05:30",
                        "meet_url": "https://meet.google.com/abc-defg-hij",
                    }
                ],
                "task-001",
            )

        self.assertTrue(engine.verify(result)["verified"])
        self.assertIn("https://meet.google.com/abc-defg-hij", sent_payloads[0]["text"])
        self.assertNotIn("test-private-token", str(result))
        self.assertIn(
            "slack.send", self.store.available_capabilities("company-001")
        )


if __name__ == "__main__":
    unittest.main()
