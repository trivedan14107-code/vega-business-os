"""Real Gmail execution behind Vega's approval boundary."""

import base64
import re
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx

from businessflow_ai.models import AgentDefinition, OAuthProvider
from businessflow_ai.services.connections import ConnectionStore
from businessflow_ai.services.execution import ExecutionEngine, MockExecutionEngine

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


class GmailError(RuntimeError):
    pass


class GmailService:
    """Manages composing and sending real emails via Gmail API."""

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
            raise GmailError("Google access expired; reconnect Google Workspace")
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
            raise GmailError("Google access refresh failed; reconnect Google Workspace")
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
            raise GmailError("Google Workspace is connected without a usable access token")
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

    def send_email(
        self, company_id: str, recipient: str, subject: str, body: str
    ) -> dict[str, Any]:
        """Send an RFC 2822 email via Gmail REST API."""
        msg = EmailMessage()
        msg.set_content(body)
        msg["To"] = recipient
        msg["Subject"] = subject

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        response = self._request(
            "POST",
            f"{GMAIL_API}/messages/send",
            company_id,
            json={"raw": raw},
        )
        if response.is_error:
            raise GmailError(f"Failed to send email via Gmail: {response.text}")
        return response.json()


class GmailExecutionEngine:
    """Specialist execution engine for business communications delivered via Gmail."""

    def __init__(
        self,
        gmail_service: GmailService,
        fallback: ExecutionEngine | None = None,
    ) -> None:
        self.gmail_service = gmail_service
        self.fallback = fallback or MockExecutionEngine()

    def execute(
        self,
        agent: AgentDefinition,
        owner_goal: str,
        prior_results: list[dict[str, Any]],
        task_id: str,
    ) -> dict[str, Any]:
        if agent.role not in ("finance_collection", "sales_followup"):
            return self.fallback.execute(agent, owner_goal, prior_results, task_id)

        company_id = agent.company_id
        emails = EMAIL_PATTERN.findall(owner_goal)
        if not emails:
            raise GmailError(
                "An explicit recipient email is required before Vega can send this message"
            )
        recipient = emails[0]

        if agent.role == "finance_collection":
            subject = "Payment Reminder: Outstanding Invoice"
            body = (
                f"Dear Client,\n\n"
                f"This is a friendly reminder regarding your outstanding invoice. "
                f"Please review the payment details at your earliest convenience.\n\n"
                f"Reference: {owner_goal}\n\n"
                f"Best regards,\nAccounts Team"
            )
        else:
            subject = "Following Up on Your Inquiry"
            body = (
                f"Hello,\n\n"
                f"I hope you are having a productive week. "
                f"I wanted to quickly follow up regarding our recent conversation.\n\n"
                f"Context: {owner_goal}\n\n"
                f"Best regards,\nSales Team"
            )

        result = self.gmail_service.send_email(
            company_id=company_id,
            recipient=recipient,
            subject=subject,
            body=body,
        )

        message_id = result.get("id", str(uuid4()))
        thread_id = result.get("threadId", message_id)

        return {
            "execution_id": str(uuid4()),
            "task_id": task_id,
            "company_id": agent.company_id,
            "agent_id": str(agent.agent_id),
            "role": agent.role,
            "adapter": "gmail",
            "action": "email.sent",
            "success": True,
            "message_id": message_id,
            "thread_id": thread_id,
            "recipient": recipient,
            "subject": subject,
            "status": "completed",
        }

    def verify(self, result: dict[str, Any]) -> dict[str, Any]:
        if result.get("adapter") != "gmail":
            return self.fallback.verify(result)
        verified = bool(result.get("success") and result.get("message_id"))
        return {
            "execution_id": result.get("execution_id"),
            "task_id": result.get("task_id"),
            "role": result.get("role"),
            "adapter": "gmail",
            "verified": verified,
            "receipt": {
                "message_id": result.get("message_id"),
                "recipient": result.get("recipient"),
                "subject": result.get("subject"),
            },
        }
