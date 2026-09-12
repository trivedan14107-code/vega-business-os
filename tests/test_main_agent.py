"""Main Agent orchestration and persistence tests."""

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from langgraph.types import Command

from businessflow_ai.agents.main_agent import build_main_agent
from businessflow_ai.agents.planner import RuleBasedGoalPlanner
from businessflow_ai.models import AgentPlan, AgentStatus, SpecialistRequest, TaskStatus
from businessflow_ai.services import AgentRegistry


def initial_state(goal: str) -> dict:
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


class MainAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "registry.db"
        self.registry = AgentRegistry(self.database)
        self.graph = build_main_agent(RuleBasedGoalPlanner(), self.registry)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def invoke(self, goal: str) -> dict:
        return self.graph.invoke(
            initial_state(goal),
            config={"configurable": {"thread_id": str(uuid4())}},
        )

    def test_creates_required_specialists(self) -> None:
        result = self.invoke("Schedule a team meeting tomorrow and inform everyone")

        self.assertEqual(
            [agent.role for agent in result["resolved_agents"]],
            ["meeting", "communication"],
        )
        self.assertTrue(result["task"].requires_approval)
        self.assertEqual(len(self.registry.list_agents("company-001")), 2)

    def test_reuses_persistent_agents(self) -> None:
        first = self.invoke("Schedule a meeting and inform the team")
        second = self.invoke("Schedule another meeting and notify the team")

        self.assertEqual(
            [agent.agent_id for agent in first["resolved_agents"]],
            [agent.agent_id for agent in second["resolved_agents"]],
        )
        reuse_events = [
            event for event in second["audit_events"] if event["event"] == "agent_reused"
        ]
        self.assertEqual(len(reuse_events), 2)

    def test_meeting_runs_before_communication_even_if_model_reverses_them(self) -> None:
        class ReversedPlanner:
            def plan(self, owner_goal: str) -> AgentPlan:
                return AgentPlan(
                    intent="meeting_notification",
                    summary=owner_goal,
                    specialists=[
                        SpecialistRequest(role="communication", responsibility="Notify team"),
                        SpecialistRequest(role="meeting", responsibility="Create meeting"),
                    ],
                )

        graph = build_main_agent(ReversedPlanner(), self.registry)
        result = graph.invoke(
            initial_state("Schedule and notify"),
            config={"configurable": {"thread_id": str(uuid4())}},
        )
        self.assertEqual(
            [agent.role for agent in result["resolved_agents"]],
            ["meeting", "communication"],
        )

    def test_registry_survives_reopening(self) -> None:
        self.invoke("Monitor overdue invoices")
        reopened = AgentRegistry(self.database)

        agents = reopened.list_agents("company-001")
        self.assertEqual([agent.role for agent in agents], ["finance_collection"])

    def test_unknown_goal_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "approved specialist capability"):
            self.invoke("Paint the office walls blue")

    def test_approved_task_executes_and_verifies_subagents(self) -> None:
        config = {"configurable": {"thread_id": str(uuid4())}}
        paused = self.graph.invoke(
            initial_state("Schedule a meeting and inform the team"), config=config
        )
        self.assertIn("__interrupt__", paused)

        completed = self.graph.invoke(Command(resume=True), config=config)

        self.assertEqual(completed["task"].status, TaskStatus.COMPLETED)
        self.assertEqual(
            [result["role"] for result in completed["execution_results"]],
            ["meeting", "communication"],
        )
        self.assertTrue(all(item["verified"] for item in completed["verification_results"]))
        self.assertTrue(
            all(
                agent.status == AgentStatus.IDLE
                for agent in self.registry.list_agents("company-001")
            )
        )

    def test_rejected_task_performs_no_action(self) -> None:
        config = {"configurable": {"thread_id": str(uuid4())}}
        self.graph.invoke(initial_state("Schedule a meeting"), config=config)

        rejected = self.graph.invoke(Command(resume=False), config=config)

        self.assertEqual(rejected["task"].status, TaskStatus.REJECTED)
        self.assertEqual(rejected["execution_results"], [])
        self.assertIn("No specialist action", rejected["final_response"])

    def test_finance_email_task_requires_approval(self) -> None:
        planned = self.invoke("Send overdue invoice reminders")

        self.assertIn("__interrupt__", planned)
        self.assertEqual(planned["task"].status, TaskStatus.WAITING_APPROVAL)
        self.assertEqual(planned["execution_results"], [])

    def test_procurement_goal_creates_approved_specialist(self) -> None:
        result = self.invoke("Get supplier quotations and prepare the best option")

        self.assertEqual([agent.role for agent in result["resolved_agents"]], ["procurement"])
        self.assertTrue(result["task"].requires_approval)

    def test_sales_reporting_goal_executes_reporting_specialist(self) -> None:
        result = self.invoke("Prepare the weekly sales performance report")

        self.assertEqual(result["task"].status, TaskStatus.COMPLETED)
        self.assertEqual(result["execution_results"][0]["role"], "sales_reporting")


if __name__ == "__main__":
    unittest.main()
