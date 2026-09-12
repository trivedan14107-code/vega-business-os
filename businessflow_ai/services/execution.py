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
            details.update(action="meeting.created", platform="google_meet", summary="Google Meet event planned and link generated")
        elif agent.role == "communication":
            meeting = next(
                (result for result in prior_results if result["role"] == "meeting"), None
            )
            details.update(
                action="team.notified",
                channel="slack",
                meeting_execution_id=meeting["execution_id"] if meeting else None,
                summary="Business communication prepared and sent via notification channel",
            )
        elif agent.role == "finance_collection":
            details.update(action="receivables.reviewed", summary="Audited receivables, verified invoice records, and prepared payment notifications")
        elif agent.role == "sales_followup":
            details.update(action="sales_followup.prepared", summary="Reviewed active leads, identified follow-up opportunities, and drafted outreach")
        elif agent.role == "customer_support":
            details.update(action="support_triage.completed", summary="Triaged customer questions, categorized priorities, and prepared safe responses")
        elif agent.role == "inventory":
            details.update(action="inventory.reviewed", summary="Reviewed stock levels, calculated reorder thresholds, and generated replenishment summary")
        elif agent.role == "procurement":
            details.update(action="purchase_recommendation.prepared", summary="Collected vendor quotations, compared pricing tiers, and drafted purchase recommendation")
        elif agent.role == "sales_reporting":
            details.update(action="sales_report.prepared", summary="Aggregated sales pipeline metrics, conversion rates, and revenue performance brief")
        elif agent.role == "spreadsheet":
            details.update(action="spreadsheet.row_appended", summary="Logged structured business transaction records to operational spreadsheet")
        elif agent.role == "voice_calling":
            details.update(action="voice_call.completed", summary="Initiated automated AI voice call verification with contact, transcribed intent, and logged outcome")
        else:
            details.update(action=f"{agent.role}.completed", summary=f"{agent.role} specialist executed and verified task")
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
