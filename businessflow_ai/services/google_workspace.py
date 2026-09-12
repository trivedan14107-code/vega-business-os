"""Real Google Calendar/Meet execution behind Vega's approval boundary."""

import hashlib
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import httpx
from langchain_groq import ChatGroq
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from businessflow_ai.models import AgentDefinition, OAuthProvider
from businessflow_ai.services.connections import ConnectionStore
from businessflow_ai.services.execution import ExecutionEngine, MockExecutionEngine

GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_MEET_URL_PATTERN = re.compile(
    r"^https://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}$"
)


class MeetingDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=2, max_length=200)
    start_time: datetime
    duration_minutes: int = Field(ge=5, le=480)
    attendee_emails: list[EmailStr] = Field(default_factory=list, max_length=100)


class MeetingDetailsExtractor(Protocol):
    def extract(self, owner_goal: str) -> MeetingDetails: ...


class GroqMeetingDetailsExtractor:
    """Convert a natural-language meeting request into validated event fields."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timezone: str,
        default_duration_minutes: int = 45,
    ) -> None:
        self.timezone = ZoneInfo(timezone)
        self.default_duration_minutes = default_duration_minutes
        client = ChatGroq(api_key=api_key, model=model, temperature=0)
        self._extractor = client.with_structured_output(MeetingDetails)

    def extract(self, owner_goal: str) -> MeetingDetails:
        now = datetime.now(self.timezone)
        prompt = (
            "Extract the meeting details from the owner's request. "
            f"Current local datetime is {now.isoformat()}; timezone is {self.timezone.key}. "
            f"Use {self.default_duration_minutes} minutes when duration is omitted. "
            "Resolve relative dates such as tomorrow. Include only explicitly provided email "
            "addresses as attendees. Never invent attendees. Request:\n"
            f"{owner_goal}"
        )
        result = self._extractor.invoke(prompt)
        details = (
            result if isinstance(result, MeetingDetails) else MeetingDetails.model_validate(result)
        )
        if details.start_time.tzinfo is None:
            details = details.model_copy(
                update={"start_time": details.start_time.replace(tzinfo=self.timezone)}
            )
        return details


class GoogleWorkspaceExecutionEngine:
    """Execute meetings in Google and delegate unfinished roles to the mock adapter."""

    def __init__(
        self,
        connection_store: ConnectionStore,
        client_id: str,
        client_secret: str,
        meeting_extractor: MeetingDetailsExtractor,
        timezone: str,
        http_client: httpx.Client | None = None,
        fallback: ExecutionEngine | None = None,
    ) -> None:
        self.connection_store = connection_store
        self.client_id = client_id
        self.client_secret = client_secret
        self.meeting_extractor = meeting_extractor
        self.timezone = ZoneInfo(timezone)
        self.http = http_client or httpx.Client(timeout=20)
        self.fallback = fallback or MockExecutionEngine()

    def _refresh_token(self, company_id: str, token: dict[str, Any]) -> dict[str, Any]:
        refresh_token = token.get("refresh_token")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise RuntimeError("Google access expired; reconnect Google Workspace")
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
            raise RuntimeError("Google access refresh failed; reconnect Google Workspace")
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
            raise RuntimeError("Google Workspace is connected without a usable access token")
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

    def _create_meeting(
        self, agent: AgentDefinition, owner_goal: str, task_id: str
    ) -> dict[str, Any]:
        details = self.meeting_extractor.extract(owner_goal)
        event_id = hashlib.sha256(f"vega:{task_id}".encode()).hexdigest()[:32]
        start = details.start_time.astimezone(self.timezone)
        end = start + timedelta(minutes=details.duration_minutes)
        event: dict[str, Any] = {
            "id": event_id,
            "summary": details.title,
            "start": {"dateTime": start.isoformat(), "timeZone": self.timezone.key},
            "end": {"dateTime": end.isoformat(), "timeZone": self.timezone.key},
            "conferenceData": {
                "createRequest": {
                    "requestId": task_id,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }
        if details.attendee_emails:
            event["attendees"] = [
                {"email": str(email)} for email in details.attendee_emails
            ]
        response = self._request(
            "POST",
            f"{GOOGLE_CALENDAR_API}/calendars/primary/events",
            agent.company_id,
            params={
                "conferenceDataVersion": "1",
                "sendUpdates": "all" if details.attendee_emails else "none",
            },
            json=event,
        )
        if response.status_code == 409:
            response = self._request(
                "GET",
                f"{GOOGLE_CALENDAR_API}/calendars/primary/events/{event_id}",
                agent.company_id,
            )
        if response.is_error:
            raise RuntimeError(f"Google Calendar rejected the event ({response.status_code})")
        created = response.json()
        return {
            "execution_id": event_id,
            "task_id": task_id,
            "company_id": agent.company_id,
            "agent_id": str(agent.agent_id),
            "role": agent.role,
            "adapter": "google_calendar",
            "action": "meeting.created",
            "success": True,
            "event_id": created.get("id", event_id),
            "event_url": created.get("htmlLink"),
            "meet_url": created.get("hangoutLink"),
            "title": created.get("summary", details.title),
            "start_time": created.get("start", {}).get("dateTime", start.isoformat()),
            "attendee_count": len(details.attendee_emails),
        }

    def execute(
        self,
        agent: AgentDefinition,
        owner_goal: str,
        prior_results: list[dict[str, Any]],
        task_id: str,
    ) -> dict[str, Any]:
        if agent.role == "meeting":
            return self._create_meeting(agent, owner_goal, task_id)
        return self.fallback.execute(agent, owner_goal, prior_results, task_id)

    def verify(self, result: dict[str, Any]) -> dict[str, Any]:
        if result.get("adapter") != "google_calendar":
            return self.fallback.verify(result)
        event_id = result.get("event_id")
        company_id = result.get("company_id")
        if not company_id:
            return {**self.fallback.verify(result), "verified": False}
        response = self._request(
            "GET",
            f"{GOOGLE_CALENDAR_API}/calendars/primary/events/{event_id}",
            company_id,
        )
        event = response.json() if response.is_success else {}
        verified = bool(
            response.is_success
            and event.get("id") == event_id
            and event.get("status") != "cancelled"
            and isinstance(event.get("hangoutLink"), str)
            and GOOGLE_MEET_URL_PATTERN.fullmatch(event["hangoutLink"])
        )
        return {
            "execution_id": result.get("execution_id"),
            "role": result.get("role"),
            "verified": verified,
            "adapter": "google_calendar",
            "event_id": event_id,
            "meet_url": event.get("hangoutLink"),
        }
