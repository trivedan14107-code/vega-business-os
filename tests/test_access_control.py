"""Tests for user-granted application access."""

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from businessflow_ai.agents.main_agent import build_main_agent
from businessflow_ai.agents.planner import RuleBasedGoalPlanner
from businessflow_ai.models import TaskStatus
from businessflow_ai.services import AccessController, AgentRegistry


class FakeCapabilities:
    def __init__(self, capabilities: set[str]) -> None:
        self.capabilities = capabilities

    def available_capabilities(self, company_id: str) -> set[str]:
        return self.capabilities


def state(goal: str) -> dict:
    return {
        "company_id": "company-001",
        "owner_goal": goal,
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
    }


class AccessControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry = AgentRegistry(Path(self.temp_dir.name) / "registry.db")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def invoke(self, capabilities: set[str]) -> dict:
        graph = build_main_agent(
            RuleBasedGoalPlanner(),
            self.registry,
            access_controller=AccessController(FakeCapabilities(capabilities)),
        )
        return graph.invoke(
            state("Schedule a meeting and inform the team"),
            config={"configurable": {"thread_id": str(uuid4())}},
        )

    def test_stops_before_execution_when_user_has_not_connected_apps(self) -> None:
        result = self.invoke(set())

        self.assertEqual(result["task"].status, TaskStatus.WAITING_ACCESS)
        self.assertEqual(result["execution_results"], [])
        self.assertEqual(
            [request["role"] for request in result["access_requests"]],
            ["meeting", "communication"],
        )
        self.assertIn("/api/oauth/google/start", result["access_requests"][0]["connect_url"])

    def test_connected_capabilities_allow_normal_approval_flow(self) -> None:
        result = self.invoke(
            {"calendar.create", "google_meet.create", "slack.send"}
        )

        self.assertIn("__interrupt__", result)
        self.assertEqual(result["access_requests"], [])


if __name__ == "__main__":
    unittest.main()
