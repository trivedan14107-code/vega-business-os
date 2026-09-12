"""Goal planners used by the Main Agent."""

from typing import Protocol

from langchain_groq import ChatGroq

from businessflow_ai.models import AgentPlan, SpecialistRequest


class GoalPlanner(Protocol):
    def plan(self, owner_goal: str) -> AgentPlan: ...


class RuleBasedGoalPlanner:
    """Deterministic planner for tests and offline demonstrations."""

    def plan(self, owner_goal: str) -> AgentPlan:
        goal = owner_goal.strip()
        lowered = goal.lower()
        specialists: list[SpecialistRequest] = []

        if any(word in lowered for word in ("meeting", "calendar", "schedule")):
            specialists.append(
                SpecialistRequest(role="meeting", responsibility="Plan and create the requested meeting")
            )
        if any(
            word in lowered
            for word in ("inform", "notify", "message", "email", "slack", "tell")
        ):
            specialists.append(
                SpecialistRequest(
                    role="communication",
                    responsibility="Prepare the requested business communication",
                )
            )
        if any(word in lowered for word in ("invoice", "overdue", "payment", "receivable")):
            specialists.append(
                SpecialistRequest(
                    role="finance_collection",
                    responsibility="Monitor and resolve the receivables goal",
                )
            )
        if any(
            word in lowered
            for word in ("lead", "prospect", "sales follow", "demo", "opportunity", "goes quiet")
        ):
            specialists.append(
                SpecialistRequest(
                    role="sales_followup",
                    responsibility="Monitor and prepare follow-ups for sales leads",
                )
            )
        if any(word in lowered for word in ("support", "ticket", "customer question")):
            specialists.append(
                SpecialistRequest(
                    role="customer_support",
                    responsibility="Triage the customer support goal",
                )
            )
        if any(word in lowered for word in ("inventory", "stock", "reorder")):
            specialists.append(
                SpecialistRequest(
                    role="inventory",
                    responsibility="Monitor inventory and recommend action",
                )
            )
        if any(word in lowered for word in ("quotation", "quote", "procure", "supplier", "vendor")):
            specialists.append(
                SpecialistRequest(
                    role="procurement",
                    responsibility="Collect quotations and prepare a purchase recommendation",
                )
            )
        if any(word in lowered for word in ("sales report", "sales performance")):
            specialists.append(
                SpecialistRequest(
                    role="sales_reporting",
                    responsibility="Prepare the requested sales performance report",
                )
            )
        if any(
            word in lowered
            for word in (
                "sheet",
                "sheets",
                "spreadsheet",
                "excel",
                "table",
                "log",
                "record",
            )
        ):
            specialists.append(
                SpecialistRequest(
                    role="spreadsheet",
                    responsibility="Record and manage the business spreadsheet log",
                )
            )
        unique = {request.role: request for request in specialists}
        if not unique:
            raise ValueError("The goal does not match an approved specialist capability")

        return AgentPlan(
            intent="business_goal",
            summary=goal,
            specialists=list(unique.values()),
        )


class GroqGoalPlanner:
    """Groq-backed structured planner restricted to approved specialist roles."""

    SYSTEM_PROMPT = """You are the planning system for Vega, the primary AI business operator.
You plan work for a non-technical business owner.
Return only a structured plan. Select the smallest useful set of specialist roles.
Allowed roles: meeting, communication, spreadsheet, finance_collection, sales_followup,
customer_support, inventory, procurement, sales_reporting. Never invent a role,
tool, permission, or completed action.
The plan only identifies responsibility; deterministic code controls permissions and execution.
"""

    def __init__(self, api_key: str, model: str) -> None:
        model_client = ChatGroq(api_key=api_key, model=model, temperature=0)
        self._planner = model_client.with_structured_output(AgentPlan)

    def plan(self, owner_goal: str) -> AgentPlan:
        result = self._planner.invoke(
            [("system", self.SYSTEM_PROMPT), ("human", owner_goal)]
        )
        return result if isinstance(result, AgentPlan) else AgentPlan.model_validate(result)
