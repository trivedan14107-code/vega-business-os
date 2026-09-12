import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi.testclient import TestClient

from businessflow_ai.api import app
from businessflow_ai.models import TaskExecution, TaskStatus
from businessflow_ai.services.playbooks import get_playbook, list_playbooks
from businessflow_ai.services.registry import AgentRegistry


class PlaybooksAndMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_playbooks.db"
        self.registry = AgentRegistry(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_list_and_get_playbooks(self) -> None:
        playbooks = list_playbooks()
        self.assertGreaterEqual(len(playbooks), 5)

        ids = [p["playbook_id"] for p in playbooks]
        self.assertIn("receivables_recovery", ids)
        self.assertIn("executive_sprint_kickoff", ids)

        pb = get_playbook("receivables_recovery")
        self.assertIsNotNone(pb)
        self.assertEqual(pb.category, "finance")
        self.assertIn("finance_collection", pb.specialist_roles)

        unknown = get_playbook("non_existent_playbook")
        self.assertIsNone(unknown)

    def test_get_business_metrics(self) -> None:
        metrics = self.registry.get_business_metrics("comp-biz-1")
        self.assertIn("hours_saved", metrics)
        self.assertIn("tasks_completed", metrics)
        self.assertIn("active_agents", metrics)
        self.assertIn("scheduled_automations", metrics)

        task = TaskExecution(
            task_id=uuid4(),
            company_id="comp-biz-1",
            owner_goal="Test completed task",
            status=TaskStatus.COMPLETED,
        )
        self.registry.save_task(task)

        updated_metrics = self.registry.get_business_metrics("comp-biz-1")
        self.assertEqual(updated_metrics["tasks_completed"], 1)
        self.assertGreater(updated_metrics["hours_saved"], 0.0)

    def test_export_business_records(self) -> None:
        records = self.registry.export_business_records("comp-biz-1")
        self.assertEqual(records["company_id"], "comp-biz-1")
        self.assertIn("exported_at", records)
        self.assertIn("metrics", records)
        self.assertIn("tasks", records)
        self.assertIn("schedules", records)
        self.assertIn("contacts", records)
        self.assertIn("audit_events", records)


def test_api_playbooks_endpoint() -> None:
    client = TestClient(app)
    res = client.get("/api/playbooks")
    assert res.status_code == 401


def test_api_workforce_endpoint() -> None:
    client = TestClient(app)
    res = client.get("/api/workforce")
    assert res.status_code == 401


def test_api_authenticated_metrics_and_export() -> None:
    client = TestClient(app)
    res_metrics = client.get("/api/metrics")
    assert res_metrics.status_code == 401

    res_export = client.get("/api/export")
    assert res_export.status_code == 401
