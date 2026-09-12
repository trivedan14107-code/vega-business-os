import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi.testclient import TestClient

from businessflow_ai.api import app
from businessflow_ai.models import ScheduledTask
from businessflow_ai.services.registry import AgentRegistry
from businessflow_ai.services.scheduler import VegaSchedulerService


class SchedulerRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_scheduler.db"
        self.registry = AgentRegistry(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_and_list_schedules(self) -> None:
        future_time = datetime.now(UTC) + timedelta(hours=2)
        task = ScheduledTask(
            company_id="comp-123",
            goal="Send invoices to client and post to Slack",
            run_at=future_time,
            schedule_type="once",
            preapproved=True,
            approved_at=datetime.now(UTC),
        )
        saved = self.registry.create_schedule(task)
        self.assertEqual(saved.company_id, "comp-123")
        self.assertEqual(saved.goal, "Send invoices to client and post to Slack")
        self.assertEqual(saved.status, "pending")

        schedules = self.registry.list_schedules("comp-123")
        self.assertEqual(len(schedules), 1)
        self.assertEqual(schedules[0].schedule_id, saved.schedule_id)
        self.assertTrue(schedules[0].preapproved)

    def test_get_due_schedules(self) -> None:
        now = datetime.now(UTC)
        past_task = ScheduledTask(
            company_id="comp-123",
            goal="Past due goal",
            run_at=now - timedelta(minutes=5),
            status="pending",
        )
        future_task = ScheduledTask(
            company_id="comp-123",
            goal="Future goal",
            run_at=now + timedelta(hours=1),
            status="pending",
        )
        self.registry.create_schedule(past_task)
        self.registry.create_schedule(future_task)

        due = self.registry.get_due_schedules(as_of=now)
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0].goal, "Past due goal")

    def test_update_schedule_status(self) -> None:
        task = ScheduledTask(
            company_id="comp-123",
            goal="Recurring sync",
            run_at=datetime.now(UTC),
            status="pending",
        )
        saved = self.registry.create_schedule(task)
        result_id = uuid4()
        run_timestamp = datetime.now(UTC)

        self.registry.update_schedule_status(
            saved.schedule_id,
            status="completed",
            result_task_id=result_id,
            last_run_at=run_timestamp,
        )

        updated = self.registry.get_schedule(saved.schedule_id)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, "completed")
        self.assertEqual(updated.result_task_id, result_id)

    def test_delete_schedule(self) -> None:
        task = ScheduledTask(
            company_id="comp-123",
            goal="Task to delete",
            run_at=datetime.now(UTC),
            status="pending",
        )
        saved = self.registry.create_schedule(task)
        self.assertEqual(len(self.registry.list_schedules("comp-123")), 1)

        self.assertFalse(self.registry.delete_schedule(saved.schedule_id, "other-company"))
        deleted = self.registry.delete_schedule(saved.schedule_id, "comp-123")
        self.assertTrue(deleted)
        self.assertEqual(len(self.registry.list_schedules("comp-123")), 0)

    def test_claim_due_schedules_is_single_use(self) -> None:
        task = ScheduledTask(
            company_id="comp-123",
            goal="Run once only",
            run_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        self.registry.create_schedule(task)

        self.assertEqual(len(self.registry.claim_due_schedules()), 1)
        self.assertEqual(self.registry.claim_due_schedules(), [])


class VegaSchedulerServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_service.db"
        self.registry = AgentRegistry(self.db_path)
        self.executed_goals = []

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def mock_executor(self, company_id: str, goal: str) -> dict:
        self.executed_goals.append((company_id, goal))
        return {
            "status": "completed",
            "message": "Goal executed autonomously",
            "task": {"task_id": str(uuid4()), "status": "completed"},
        }

    def test_run_once_executes_due_tasks(self) -> None:
        scheduler = VegaSchedulerService(
            registry=self.registry,
            executor_callback=self.mock_executor,
            poll_interval_seconds=1.0,
        )

        past_task = ScheduledTask(
            company_id="comp-alpha",
            goal="Automate client follow-ups",
            run_at=datetime.now(UTC) - timedelta(minutes=10),
            status="pending",
        )
        self.registry.create_schedule(past_task)

        results = scheduler.run_once()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "completed")
        self.assertEqual(len(self.executed_goals), 1)
        self.assertEqual(self.executed_goals[0], ("comp-alpha", "Automate client follow-ups"))

        schedules = self.registry.list_schedules("comp-alpha")
        self.assertEqual(schedules[0].status, "completed")

    def test_run_once_handles_execution_error(self) -> None:
        def failing_executor(company_id: str, goal: str) -> dict:
            raise RuntimeError("API failure")

        scheduler = VegaSchedulerService(
            registry=self.registry,
            executor_callback=failing_executor,
            poll_interval_seconds=1.0,
        )

        past_task = ScheduledTask(
            company_id="comp-fail",
            goal="Failing task",
            run_at=datetime.now(UTC) - timedelta(minutes=5),
            status="pending",
        )
        self.registry.create_schedule(past_task)

        results = scheduler.run_once()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "failed")

        schedules = self.registry.list_schedules("comp-fail")
        self.assertEqual(schedules[0].status, "failed")

    def test_preapproved_task_resumes_real_approval_boundary(self) -> None:
        thread_id = "scheduled-thread"

        def waiting_executor(company_id: str, goal: str) -> dict:
            return {"status": "waiting_approval", "thread_id": thread_id}

        approvals: list[tuple[str, str, bool]] = []

        def approver(company_id: str, supplied_thread_id: str, approved: bool) -> dict:
            approvals.append((company_id, supplied_thread_id, approved))
            return {
                "status": "completed",
                "task": {"task_id": str(uuid4()), "status": "completed"},
            }

        scheduler = VegaSchedulerService(
            registry=self.registry,
            executor_callback=waiting_executor,
            approval_callback=approver,
        )
        self.registry.create_schedule(
            ScheduledTask(
                company_id="comp-approved",
                goal="Send approved update",
                run_at=datetime.now(UTC) - timedelta(minutes=1),
                preapproved=True,
                approved_at=datetime.now(UTC),
            )
        )

        result = scheduler.run_once()

        self.assertEqual(result[0]["status"], "completed")
        self.assertEqual(approvals, [("comp-approved", thread_id, True)])


def test_api_schedules_endpoints_require_auth() -> None:
    client = TestClient(app)
    res_list = client.get("/api/schedules")
    assert res_list.status_code == 401

    res_post = client.post("/api/schedules", json={"goal": "test", "run_at": "2026-09-12T10:00:00Z"})
    assert res_post.status_code in (401, 403)

