"""Google Calendar/Meet adapter tests with no external side effects."""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import httpx

from businessflow_ai.models import AgentDefinition, OAuthProvider
from businessflow_ai.services import ConnectionStore, TokenVault
from businessflow_ai.services.google_workspace import (
    GoogleWorkspaceExecutionEngine,
    MeetingDetails,
)


class FixedMeetingExtractor:
    def extract(self, owner_goal: str) -> MeetingDetails:
        return MeetingDetails(
            title="Weekly leadership sync",
            start_time=datetime.fromisoformat("2026-09-12T10:00:00+05:30"),
            duration_minutes=45,
            attendee_emails=["teammate@example.com"],
        )


class GoogleWorkspaceExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = ConnectionStore(
            Path(self.temp_dir.name) / "connections.db",
            TokenVault(TokenVault.generate_key()),
        )
        self.store.save_connection(
            company_id="company-001",
            provider=OAuthProvider.GOOGLE_WORKSPACE,
            token={"access_token": "private-token", "refresh_token": "refresh-token"},
            scopes=["https://www.googleapis.com/auth/calendar.events"],
            account_email="owner@example.com",
        )
        self.requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if request.method == "POST" and "/events" in request.url.path:
                event = json.loads(request.content)
                return httpx.Response(
                    200,
                    json={
                        **event,
                        "status": "confirmed",
                        "htmlLink": "https://calendar.google.test/event",
                        "hangoutLink": "https://meet.google.com/abc-defg-hij",
                    },
                )
            event_id = request.url.path.rsplit("/", 1)[-1]
            return httpx.Response(
                200,
                json={
                    "id": event_id,
                    "status": "confirmed",
                    "hangoutLink": "https://meet.google.com/abc-defg-hij",
                },
            )

        self.http = httpx.Client(transport=httpx.MockTransport(handler))
        self.engine = GoogleWorkspaceExecutionEngine(
            connection_store=self.store,
            client_id="client-id",
            client_secret="client-secret",
            meeting_extractor=FixedMeetingExtractor(),
            timezone="Asia/Kolkata",
            http_client=self.http,
        )

    def tearDown(self) -> None:
        self.http.close()
        self.temp_dir.cleanup()

    def test_creates_meet_event_and_verifies_by_reading_it_back(self) -> None:
        agent = AgentDefinition(
            company_id="company-001",
            role="meeting",
            responsibilities=["Create meetings"],
        )
        result = self.engine.execute(
            agent,
            "Arrange the weekly sync tomorrow at 10",
            [],
            "task-001",
        )
        verification = self.engine.verify(result)

        self.assertEqual(result["adapter"], "google_calendar")
        self.assertEqual(result["meet_url"], "https://meet.google.com/abc-defg-hij")
        self.assertTrue(verification["verified"])
        create_request = self.requests[0]
        body = json.loads(create_request.content)
        self.assertEqual(create_request.url.params["conferenceDataVersion"], "1")
        self.assertEqual(create_request.url.params["sendUpdates"], "all")
        self.assertEqual(body["conferenceData"]["createRequest"]["requestId"], "task-001")
        self.assertEqual(body["attendees"], [{"email": "teammate@example.com"}])
        self.assertNotIn("private-token", json.dumps(result))

    def test_same_task_uses_same_google_event_id(self) -> None:
        agent = AgentDefinition(
            company_id="company-001",
            role="meeting",
            responsibilities=["Create meetings"],
        )
        first = self.engine.execute(agent, "Meeting tomorrow at 10", [], "task-002")
        second = self.engine.execute(agent, "Meeting tomorrow at 10", [], "task-002")

        self.assertEqual(first["event_id"], second["event_id"])


if __name__ == "__main__":
    unittest.main()
