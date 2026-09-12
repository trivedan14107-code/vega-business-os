"""Google Sheets adapter tests with verified receipts."""

import tempfile
import unittest
from pathlib import Path

import httpx

from businessflow_ai.models import AgentDefinition, OAuthProvider
from businessflow_ai.services import ConnectionStore, TokenVault
from businessflow_ai.services.google_sheets import (
    GoogleSheetsExecutionEngine,
    GoogleSheetsService,
)


class GoogleSheetsExecutionTests(unittest.TestCase):
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
            ],
            account_email="owner@example.com",
        )
        self.requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if request.method == "POST" and request.url.path.endswith("/spreadsheets"):
                return httpx.Response(
                    200,
                    json={
                        "spreadsheetId": "test-sheet-id-123",
                        "properties": {"title": "Vega Business Operations Log"},
                    },
                )
            if request.method == "POST" and ":append" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "spreadsheetId": "test-sheet-id-123",
                        "tableRange": "Log!A1:E1",
                        "updates": {
                            "spreadsheetId": "test-sheet-id-123",
                            "updatedRange": "Log!A2:E2",
                            "updatedRows": 1,
                            "updatedColumns": 5,
                            "updatedCells": 5,
                        },
                    },
                )
            return httpx.Response(404, json={"error": "not found"})

        self.http = httpx.Client(transport=httpx.MockTransport(handler))
        self.service = GoogleSheetsService(
            self.store,
            client_id="client-id",
            client_secret="client-secret",
            timezone="Asia/Kolkata",
            http_client=self.http,
        )
        self.engine = GoogleSheetsExecutionEngine(self.service)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_creates_sheet_appends_row_and_returns_receipt(self) -> None:
        agent = AgentDefinition(
            company_id="company-001",
            role="spreadsheet",
            responsibilities=["Manage company spreadsheets and logs"],
            allowed_tools=["sheets.read", "sheets.append", "sheets.create_log"],
            forbidden_tools=["sheets.delete"],
            permissions=["read_spreadsheet", "append_spreadsheet_row"],
        )
        result = self.engine.execute(
            agent=agent,
            owner_goal="Log meeting details in spreadsheet",
            prior_results=[
                {
                    "role": "meeting",
                    "title": "Leadership Sync",
                    "meet_url": "https://meet.google.com/abc-defg-hij",
                }
            ],
            task_id="task-001",
        )

        self.assertEqual(result["role"], "spreadsheet")
        self.assertEqual(result["spreadsheet_id"], "test-sheet-id-123")
        self.assertIn("test-sheet-id-123", result["spreadsheet_url"])
        self.assertEqual(result["updated_rows"], 1)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["values_appended"][1], "Meeting")
        self.assertIn("https://meet.google.com/abc-defg-hij", result["values_appended"][3])

        verification = self.engine.verify(result)
        self.assertTrue(verification["verified"])
        self.assertEqual(verification["receipt"]["spreadsheet_id"], "test-sheet-id-123")
