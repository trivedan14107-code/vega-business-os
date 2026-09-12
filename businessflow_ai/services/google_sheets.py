"""Real Google Sheets execution behind Vega's approval boundary."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx

from businessflow_ai.models import AgentDefinition, OAuthProvider
from businessflow_ai.services.connections import ConnectionStore
from businessflow_ai.services.execution import ExecutionEngine, MockExecutionEngine

GOOGLE_SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleSheetsError(RuntimeError):
    pass


class GoogleSheetsService:
    """Manages reading, creating, and appending to Google Sheets."""

    def __init__(
        self,
        connection_store: ConnectionStore,
        client_id: str,
        client_secret: str,
        timezone: str = "Asia/Kolkata",
        http_client: httpx.Client | None = None,
    ) -> None:
        self.connection_store = connection_store
        self.client_id = client_id
        self.client_secret = client_secret
        self.timezone = ZoneInfo(timezone)
        self.http = http_client or httpx.Client(timeout=20)

    def _refresh_token(self, company_id: str, token: dict[str, Any]) -> dict[str, Any]:
        refresh_token = token.get("refresh_token")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise GoogleSheetsError("Google access expired; reconnect Google Workspace")
        response = self.http.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if response.is_error:
            raise GoogleSheetsError("Google access refresh failed; reconnect Google Workspace")
        refreshed = response.json()
        refreshed["refresh_token"] = refreshed.get("refresh_token", refresh_token)
        expires_in = refreshed.get("expires_in")
        if isinstance(expires_in, (int, float)):
            refreshed["expires_at"] = (
                datetime.now(UTC) + timedelta(seconds=float(expires_in))
            ).timestamp()
        self.connection_store.update_token(
            company_id, OAuthProvider.GOOGLE_WORKSPACE, refreshed
        )
        return refreshed

    def _access_token(self, company_id: str) -> str:
        token = self.connection_store.get_token(company_id, OAuthProvider.GOOGLE_WORKSPACE)
        expires_at = token.get("expires_at")
        if isinstance(expires_at, (int, float)) and expires_at <= (
            datetime.now(UTC).timestamp() + 60
        ):
            token = self._refresh_token(company_id, token)
        access_token = token.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise GoogleSheetsError("Google Workspace is connected without a usable access token")
        return access_token

    def _request(
        self, method: str, url: str, company_id: str, **kwargs: Any
    ) -> httpx.Response:
        access_token = self._access_token(company_id)
        headers = {**kwargs.pop("headers", {}), "Authorization": f"Bearer {access_token}"}
        response = self.http.request(method, url, headers=headers, **kwargs)
        if response.status_code == 401:
            current = self.connection_store.get_token(
                company_id, OAuthProvider.GOOGLE_WORKSPACE
            )
            refreshed = self._refresh_token(company_id, current)
            headers["Authorization"] = f"Bearer {refreshed['access_token']}"
            response = self.http.request(method, url, headers=headers, **kwargs)
        return response

    def create_spreadsheet(
        self, company_id: str, title: str = "Vega Business Operations Log"
    ) -> dict[str, Any]:
        """Create a new Google Spreadsheet with default operational headers."""
        payload = {
            "properties": {"title": title},
            "sheets": [
                {
                    "properties": {"title": "Log"},
                    "data": [
                        {
                            "startRow": 0,
                            "startColumn": 0,
                            "rowData": [
                                {
                                    "values": [
                                        {"userEnteredValue": {"stringValue": "Timestamp"}},
                                        {"userEnteredValue": {"stringValue": "Category"}},
                                        {"userEnteredValue": {"stringValue": "Item / Goal"}},
                                        {"userEnteredValue": {"stringValue": "Details / Receipts"}},
                                        {"userEnteredValue": {"stringValue": "Status"}},
                                    ]
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        response = self._request("POST", GOOGLE_SHEETS_API, company_id, json=payload)
        if response.is_error:
            raise GoogleSheetsError(f"Failed to create Google Spreadsheet: {response.text}")
        data = response.json()
        spreadsheet_id = data.get("spreadsheetId")
        token = self.connection_store.get_token(company_id, OAuthProvider.GOOGLE_WORKSPACE)
        token["default_spreadsheet_id"] = spreadsheet_id
        token["default_spreadsheet_url"] = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        self.connection_store.update_token(company_id, OAuthProvider.GOOGLE_WORKSPACE, token)
        return data

    def get_or_create_default_spreadsheet_id(self, company_id: str) -> str:
        token = self.connection_store.get_token(company_id, OAuthProvider.GOOGLE_WORKSPACE)
        spreadsheet_id = token.get("default_spreadsheet_id")
        if isinstance(spreadsheet_id, str) and spreadsheet_id:
            return spreadsheet_id
        created = self.create_spreadsheet(company_id)
        return str(created["spreadsheetId"])

    def append_row(
        self,
        company_id: str,
        spreadsheet_id: str,
        row_values: list[Any],
        sheet_name: str = "Log",
    ) -> dict[str, Any]:
        """Append a single row of values to the specified sheet."""
        url = (
            f"{GOOGLE_SHEETS_API}/{spreadsheet_id}/values/{sheet_name}!A1:append"
            "?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"
        )
        payload = {"values": [row_values]}
        response = self._request("POST", url, company_id, json=payload)
        if response.is_error:
            raise GoogleSheetsError(f"Failed to append row to Google Sheet: {response.text}")
        return response.json()


class GoogleSheetsExecutionEngine:
    """Specialist execution engine for spreadsheet operations and business logging."""

    def __init__(
        self,
        sheets_service: GoogleSheetsService,
        fallback: ExecutionEngine | None = None,
    ) -> None:
        self.sheets_service = sheets_service
        self.fallback = fallback or MockExecutionEngine()

    def execute(
        self,
        agent: AgentDefinition,
        owner_goal: str,
        prior_results: list[dict[str, Any]],
        task_id: str,
    ) -> dict[str, Any]:
        if agent.role != "spreadsheet":
            return self.fallback.execute(agent, owner_goal, prior_results, task_id)

        company_id = agent.company_id
        spreadsheet_id = self.sheets_service.get_or_create_default_spreadsheet_id(company_id)

        now_str = datetime.now(self.sheets_service.timezone).strftime("%Y-%m-%d %H:%M:%S")
        category = "Operations"
        summary = owner_goal

        # Extract context from prior specialist outputs
        details = "Completed"
        meeting = next((item for item in prior_results if item.get("role") == "meeting"), None)
        comm = next((item for item in prior_results if item.get("role") == "communication"), None)

        if meeting:
            meet_url = meeting.get("meet_url") or meeting.get("google_meet_url", "")
            title = meeting.get("title") or meeting.get("summary", "")
            category = "Meeting"
            details = f"Meet: {title} | Link: {meet_url}" if meet_url else f"Meet: {title}"
        elif comm:
            channel = comm.get("channel_id") or comm.get("channel", "")
            category = "Communication"
            details = f"Slack broadcast to {channel}"

        row_values = [
            now_str,
            category,
            summary,
            details,
            "SUCCESS",
        ]

        result = self.sheets_service.append_row(
            company_id=company_id,
            spreadsheet_id=spreadsheet_id,
            row_values=row_values,
        )

        updates = result.get("updates", {})
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

        return {
            "execution_id": str(uuid4()),
            "task_id": task_id,
            "company_id": agent.company_id,
            "agent_id": str(agent.agent_id),
            "role": agent.role,
            "adapter": "google_sheets",
            "action": "spreadsheet.row_appended",
            "success": True,
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_url": spreadsheet_url,
            "updated_range": updates.get("updatedRange", "Log!A:E"),
            "updated_rows": updates.get("updatedRows", 1),
            "values_appended": row_values,
            "status": "completed",
        }

    def verify(self, result: dict[str, Any]) -> dict[str, Any]:
        if result.get("adapter") != "google_sheets":
            return self.fallback.verify(result)
        verified = bool(
            result.get("success")
            and result.get("spreadsheet_id")
            and result.get("updated_rows", 0) >= 1
        )
        return {
            "execution_id": result.get("execution_id"),
            "task_id": result.get("task_id"),
            "role": result.get("role"),
            "adapter": "google_sheets",
            "verified": verified,
            "receipt": {
                "spreadsheet_id": result.get("spreadsheet_id"),
                "spreadsheet_url": result.get("spreadsheet_url"),
                "updated_range": result.get("updated_range"),
                "updated_rows": result.get("updated_rows"),
            },
        }
