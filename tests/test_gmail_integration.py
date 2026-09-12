"""Gmail execution engine tests with verified receipts."""

import tempfile
import unittest
from pathlib import Path

import httpx

from businessflow_ai.models import AgentDefinition, OAuthProvider
from businessflow_ai.services import ConnectionStore, TokenVault
from businessflow_ai.services.gmail import GmailError, GmailExecutionEngine, GmailService


class GmailExecutionTests(unittest.TestCase):
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
            scopes=[
                "https://www.googleapis.com/auth/calendar.events",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/gmail.send",
            ],
            account_email="owner@example.com",
        )
        self.requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if request.method == "POST" and request.url.path.endswith("/messages/send"):
                return httpx.Response(
                    200,
                    json={
                        "id": "gmail-msg-12345",
                        "threadId": "thread-12345",
                        "labelIds": ["SENT"],
                    },
                )
            return httpx.Response(404, json={"error": "not found"})

        self.http = httpx.Client(transport=httpx.MockTransport(handler))
        self.service = GmailService(
            self.store,
            client_id="client-id",
            client_secret="client-secret",
            timezone="Asia/Kolkata",
            http_client=self.http,
        )
        self.engine = GmailExecutionEngine(self.service)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_finance_collection_sends_payment_reminder_and_verifies_receipt(self) -> None:
        agent = AgentDefinition(
            company_id="company-001",
            role="finance_collection",
            responsibilities=["Monitor receivables and send payment reminders"],
            allowed_tools=["invoice.read", "gmail.send"],
            forbidden_tools=["money.transfer"],
            permissions=["read_receivables", "draft_payment_reminder"],
        )
        result = self.engine.execute(
            agent=agent,
            owner_goal="Send overdue invoice reminder to billing@acme.com for INV-2026",
            prior_results=[],
            task_id="task-gmail-001",
        )

        self.assertEqual(result["role"], "finance_collection")
        self.assertEqual(result["adapter"], "gmail")
        self.assertEqual(result["message_id"], "gmail-msg-12345")
        self.assertEqual(result["recipient"], "billing@acme.com")
        self.assertEqual(result["status"], "completed")

        verification = self.engine.verify(result)
        self.assertTrue(verification["verified"])
        self.assertEqual(verification["receipt"]["message_id"], "gmail-msg-12345")
        self.assertEqual(verification["receipt"]["recipient"], "billing@acme.com")

    def test_missing_recipient_never_sends_to_a_placeholder(self) -> None:
        agent = AgentDefinition(
            company_id="company-001",
            role="finance_collection",
            responsibilities=["Send payment reminders"],
            allowed_tools=["gmail.send"],
            forbidden_tools=["money.transfer"],
            permissions=["draft_payment_reminder"],
        )

        with self.assertRaises(GmailError):
            self.engine.execute(
                agent=agent,
                owner_goal="Send the overdue invoice reminder",
                prior_results=[],
                task_id="task-no-recipient",
            )
        self.assertEqual(self.requests, [])
