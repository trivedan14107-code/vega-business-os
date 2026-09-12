"""Command-line entry point for the Main Agent."""

import argparse
from pathlib import Path
from uuid import uuid4

from langgraph.types import Command

from businessflow_ai.agents.main_agent import build_main_agent
from businessflow_ai.agents.planner import GroqGoalPlanner, RuleBasedGoalPlanner
from businessflow_ai.config import get_settings
from businessflow_ai.services import (
    AccessController,
    AgentRegistry,
    ConnectionStore,
    GoogleWorkspaceExecutionEngine,
    GroqMeetingDetailsExtractor,
    SlackExecutionEngine,
    SlackService,
    TokenVault,
)


def database_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("Only sqlite:/// database URLs are supported in the MVP")
    return Path(database_url.removeprefix(prefix))


def run(owner_goal: str, company_id: str, offline: bool = False) -> str:
    settings = get_settings()
    registry = AgentRegistry(database_path(settings.database_url))

    if not offline and settings.groq_api_key is not None:
        planner = GroqGoalPlanner(
            api_key=settings.groq_api_key.get_secret_value(),
            model=settings.groq_reasoning_model,
        )
    else:
        planner = RuleBasedGoalPlanner()

    access_controller = None
    execution_engine = None
    if settings.token_encryption_key is not None:
        connection_store = ConnectionStore(
            database_path(settings.database_url),
            TokenVault(settings.token_encryption_key.get_secret_value()),
        )
        access_controller = AccessController(connection_store)
        if settings.slack_client_id and settings.slack_client_secret is not None:
            execution_engine = SlackExecutionEngine(
                SlackService(connection_store),
                default_channel_id=settings.slack_default_channel_id,
            )
        if (
            not offline
            and settings.groq_api_key is not None
            and settings.google_client_id
            and settings.google_client_secret is not None
        ):
            meeting_extractor = GroqMeetingDetailsExtractor(
                api_key=settings.groq_api_key.get_secret_value(),
                model=settings.groq_fast_model,
                timezone=settings.business_timezone,
                default_duration_minutes=settings.default_meeting_duration_minutes,
            )
            execution_engine = GoogleWorkspaceExecutionEngine(
                connection_store=connection_store,
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret.get_secret_value(),
                meeting_extractor=meeting_extractor,
                timezone=settings.business_timezone,
                fallback=execution_engine,
            )

    graph = build_main_agent(
        planner,
        registry,
        access_controller=access_controller,
        execution_engine=execution_engine,
    )
    config = {"configurable": {"thread_id": str(uuid4())}}
    result = graph.invoke(
        {
            "company_id": company_id,
            "owner_goal": owner_goal,
            "plan": None,
            "resolved_agents": [],
            "task": None,
            "access_requests": [],
            "approval_decision": None,
            "execution_results": [],
            "verification_results": [],
            "final_response": "",
            "audit_events": [],
            "errors": [],
        },
        config=config,
    )

    if result.get("__interrupt__"):
        roles = ", ".join(agent.role for agent in result["resolved_agents"])
        print(f"Approval required for: {roles}")
        answer = input("Approve specialist execution? [y/N]: ").strip().lower()
        approved = answer in {"y", "yes", "approve", "approved"}
        result = graph.invoke(Command(resume=approved), config=config)

    return result["final_response"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Vega, the Business Second Brain")
    parser.add_argument("goal", help="Business goal stated by the owner")
    parser.add_argument("--company", default="demo-company", help="Company identifier")
    parser.add_argument("--offline", action="store_true", help="Use the deterministic planner")
    args = parser.parse_args()
    print(run(args.goal, args.company, args.offline))


if __name__ == "__main__":
    main()
