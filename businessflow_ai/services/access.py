"""Capability gate between specialist agents and connected applications."""

from dataclasses import dataclass
from typing import Protocol

from businessflow_ai.models import AgentDefinition, OAuthProvider


class CapabilitySource(Protocol):
    def available_capabilities(self, company_id: str) -> set[str]: ...


@dataclass(frozen=True)
class CapabilityOption:
    provider: OAuthProvider
    capabilities: frozenset[str]


ROLE_CAPABILITY_OPTIONS: dict[str, tuple[CapabilityOption, ...]] = {
    "meeting": (
        CapabilityOption(
            OAuthProvider.GOOGLE_WORKSPACE,
            frozenset({"calendar.create", "google_meet.create"}),
        ),
    ),
    "communication": (
        CapabilityOption(
            OAuthProvider.SLACK,
            frozenset({"slack.send"}),
        ),
    ),
    "spreadsheet": (
        CapabilityOption(
            OAuthProvider.GOOGLE_WORKSPACE,
            frozenset({"sheets.append"}),
        ),
    ),
    "finance_collection": (
        CapabilityOption(
            OAuthProvider.GOOGLE_WORKSPACE,
            frozenset({"gmail.send"}),
        ),
    ),
    "sales_followup": (
        CapabilityOption(
            OAuthProvider.GOOGLE_WORKSPACE,
            frozenset({"gmail.send"}),
        ),
    ),
}


class AccessController:
    """Determines whether a company granted the capabilities an agent needs."""

    def __init__(self, capability_source: CapabilitySource) -> None:
        self.capability_source = capability_source

    def requests_for(
        self, company_id: str, agents: list[AgentDefinition]
    ) -> list[dict[str, object]]:
        available = self.capability_source.available_capabilities(company_id)
        requests: list[dict[str, object]] = []

        for agent in agents:
            options = ROLE_CAPABILITY_OPTIONS.get(agent.role, ())
            if not options or any(option.capabilities <= available for option in options):
                continue

            preferred = options[0]
            connect_routes = {
                OAuthProvider.GOOGLE_WORKSPACE: "/api/oauth/google/start",
                OAuthProvider.SLACK: "/api/oauth/slack/start",
            }
            if (
                preferred.provider == OAuthProvider.SLACK
                and "slack.channels.read" in available
            ):
                connect_url = f"/api/companies/{company_id}/slack/channels"
            else:
                connect_url = connect_routes[preferred.provider] + "?company_id=" + company_id
            requests.append(
                {
                    "agent_id": str(agent.agent_id),
                    "role": agent.role,
                    "provider": preferred.provider.value,
                    "missing_capabilities": sorted(preferred.capabilities - available),
                    "connect_url": connect_url,
                }
            )
        return requests
