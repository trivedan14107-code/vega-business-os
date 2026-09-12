"""Shared state for the Main Agent orchestration graph."""

from typing import Annotated, TypedDict

from businessflow_ai.models import AgentDefinition, AgentPlan, TaskExecution


def append_items(left: list[dict], right: list[dict]) -> list[dict]:
    return [*left, *right]


class MainAgentState(TypedDict):
    company_id: str
    owner_goal: str
    thread_id: str | None
    plan: AgentPlan | None
    resolved_agents: list[AgentDefinition]
    task: TaskExecution | None
    access_requests: list[dict]
    approval_decision: bool | None
    execution_results: list[dict]
    verification_results: list[dict]
    final_response: str
    audit_events: Annotated[list[dict], append_items]
    errors: Annotated[list[dict], append_items]
