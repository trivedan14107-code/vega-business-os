"""Slack channel selection and specialist execution."""

from typing import Any
from uuid import uuid4

import httpx

from businessflow_ai.models import AgentDefinition, OAuthProvider
from businessflow_ai.services.connections import ConnectionStore
from businessflow_ai.services.execution import ExecutionEngine, MockExecutionEngine

SLACK_API = "https://slack.com/api"


class SlackError(RuntimeError):
    pass


class SlackService:
    def __init__(
        self,
        connection_store: ConnectionStore,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.connection_store = connection_store
        self.http = http_client or httpx.Client(timeout=20)

    def _token(self, company_id: str) -> dict[str, Any]:
        token = self.connection_store.get_token(company_id, OAuthProvider.SLACK)
        if not token.get("access_token"):
            raise SlackError("Slack is connected without a usable bot token")
        return token

    def _request(self, company_id: str, method: str, **payload: Any) -> dict[str, Any]:
        token = self._token(company_id)
        response = self.http.post(
            f"{SLACK_API}/{method}",
            headers={"Authorization": f"Bearer {token['access_token']}"},
            json=payload,
        )
        body = response.json() if response.is_success else {}
        if response.is_error or body.get("ok") is not True:
            error = body.get("error", f"http_{response.status_code}")
            raise SlackError(f"Slack API request failed: {error}")
        return body

    def list_channels(self, company_id: str) -> list[dict[str, Any]]:
        body = self._request(
            company_id,
            "conversations.list",
            types="public_channel,private_channel",
            exclude_archived=True,
            limit=200,
        )
        return [
            {
                "id": channel["id"],
                "name": channel.get("name", channel["id"]),
                "is_private": bool(channel.get("is_private")),
                "is_member": bool(channel.get("is_member")),
            }
            for channel in body.get("channels", [])
        ]

    def select_channel(self, company_id: str, channel_id: str) -> dict[str, Any]:
        channels = self.list_channels(company_id)
        selected = next((item for item in channels if item["id"] == channel_id), None)
        if selected is None:
            raise SlackError("The selected Slack channel is unavailable")
        if not selected["is_member"]:
            raise SlackError("Invite Vega to this Slack channel before selecting it")
        token = self._token(company_id)
        token["default_channel_id"] = channel_id
        token["default_channel_name"] = selected["name"]
        self.connection_store.update_token(company_id, OAuthProvider.SLACK, token)
        return selected

    def post_message(self, company_id: str, channel_id: str, text: str) -> dict[str, Any]:
        return self._request(
            company_id,
            "chat.postMessage",
            channel=channel_id,
            text=text,
            unfurl_links=False,
            unfurl_media=False,
        )


class SlackExecutionEngine:
    def __init__(
        self,
        slack: SlackService,
        default_channel_id: str | None = None,
        fallback: ExecutionEngine | None = None,
    ) -> None:
        self.slack = slack
        self.default_channel_id = default_channel_id
        self.fallback = fallback or MockExecutionEngine()

    def execute(
        self,
        agent: AgentDefinition,
        owner_goal: str,
        prior_results: list[dict[str, Any]],
        task_id: str,
    ) -> dict[str, Any]:
        if agent.role != "communication":
            return self.fallback.execute(agent, owner_goal, prior_results, task_id)
        token = self.slack._token(agent.company_id)
        channel_id = token.get("default_channel_id") or self.default_channel_id
        if not isinstance(channel_id, str) or not channel_id:
            raise SlackError("Select a default Slack channel before sending messages")
        meeting = next(
            (item for item in prior_results if item.get("role") == "meeting"), None
        )
        if meeting:
            text = (
                f"Vega meeting invitation\n*{meeting.get('title', 'Team meeting')}*\n"
                f"Time: {meeting.get('start_time')}\nJoin: {meeting.get('meet_url')}"
            )
        else:
            text = owner_goal
        response = self.slack.post_message(agent.company_id, channel_id, text)
        return {
            "execution_id": str(uuid4()),
            "task_id": task_id,
            "company_id": agent.company_id,
            "agent_id": str(agent.agent_id),
            "role": agent.role,
            "adapter": "slack",
            "action": "team.notified",
            "success": True,
            "channel_id": response.get("channel", channel_id),
            "message_ts": response.get("ts"),
        }

    def verify(self, result: dict[str, Any]) -> dict[str, Any]:
        if result.get("adapter") != "slack":
            return self.fallback.verify(result)
        verified = bool(
            result.get("success")
            and result.get("channel_id")
            and result.get("message_ts")
        )
        return {
            "execution_id": result.get("execution_id"),
            "role": result.get("role"),
            "verified": verified,
            "adapter": "slack",
            "channel_id": result.get("channel_id"),
            "message_ts": result.get("message_ts"),
        }
