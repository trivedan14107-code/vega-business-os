"""Specialist execution boundary and safe mock adapter."""

from typing import Any, Protocol
from uuid import uuid4

from businessflow_ai.models import AgentDefinition


class ExecutionEngine(Protocol):
    def execute(
        self,
        agent: AgentDefinition,
        owner_goal: str,
        prior_results: list[dict[str, Any]],
        task_id: str,
    ) -> dict[str, Any]: ...

    def verify(self, result: dict[str, Any]) -> dict[str, Any]: ...


class MockExecutionEngine:
    """Deterministic adapter for testing orchestration without external side effects."""

    def execute(
        self,
        agent: AgentDefinition,
        owner_goal: str,
        prior_results: list[dict[str, Any]],
        task_id: str,
    ) -> dict[str, Any]:
        details: dict[str, Any] = {
            "execution_id": str(uuid4()),
            "agent_id": str(agent.agent_id),
            "role": agent.role,
            "adapter": "mock",
            "success": True,
            "owner_goal": owner_goal,
            "task_id": task_id,
        }

        if agent.role == "meeting":
            details.update(action="meeting.created", platform="google_meet")
        elif agent.role == "communication":
            meeting = next(
                (result for result in prior_results if result["role"] == "meeting"), None
            )
            details.update(
                action="team.notified",
                channel="slack",
                meeting_execution_id=meeting["execution_id"] if meeting else None,
            )
        elif agent.role == "finance_collection":
            details.update(action="receivables.reviewed")
        elif agent.role == "sales_followup":
            details.update(action="sales_followup.prepared")
        elif agent.role == "customer_support":
            details.update(action="support_triage.completed")
        elif agent.role == "inventory":
            details.update(action="inventory.reviewed")
        elif agent.role == "procurement":
            details.update(action="purchase_recommendation.prepared")
        elif agent.role == "sales_reporting":
            details.update(action="sales_report.prepared")
        else:
            raise ValueError(f"No execution adapter for role: {agent.role}")
        return details

    def verify(self, result: dict[str, Any]) -> dict[str, Any]:
        required = {"execution_id", "agent_id", "role", "adapter", "action", "success"}
        missing = sorted(required - result.keys())
        verified = result.get("success") is True and not missing
        return {
            "execution_id": result.get("execution_id"),
            "role": result.get("role"),
            "verified": verified,
            "missing_fields": missing,
            "adapter": result.get("adapter"),
        }
