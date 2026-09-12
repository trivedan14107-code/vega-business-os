import unittest
from datetime import UTC, datetime

from businessflow_ai.services.goal_decomposer import (
    decompose_goal_into_milestones,
    parse_temporal_intent,
)


class GoalDecomposerTests(unittest.TestCase):
    def test_parse_tomorrow_at_time(self) -> None:
        base = datetime(2026, 9, 12, 10, 0, 0, tzinfo=UTC)
        goal = "Send payment reminder to client tomorrow at 9:00 AM"
        run_at, _, _, sched_type = parse_temporal_intent(goal, base_time=base)

        self.assertIsNotNone(run_at)

        self.assertEqual(run_at.day, 13)
        self.assertEqual(run_at.hour, 9)
        self.assertEqual(run_at.minute, 0)
        self.assertEqual(sched_type, "once")

    def test_parse_in_hours(self) -> None:
        base = datetime(2026, 9, 12, 10, 0, 0, tzinfo=UTC)
        goal = "Call Venu in 2 hours to check deliverables"
        run_at, _, _, _ = parse_temporal_intent(goal, base_time=base)

        self.assertIsNotNone(run_at)
        self.assertEqual(run_at.hour, 12)

    def test_parse_recurring_schedule(self) -> None:
        base = datetime(2026, 9, 12, 10, 0, 0, tzinfo=UTC)
        goal = "Send weekly financial summary every weekday at 10 AM"
        run_at, _, _, sched_type = parse_temporal_intent(goal, base_time=base)

        self.assertIsNotNone(run_at)
        self.assertEqual(sched_type, "recurring")

    def test_decompose_into_milestones(self) -> None:
        goal = "Audit unpaid invoices, email clients tomorrow at 9 AM, and notify Slack"
        milestones = decompose_goal_into_milestones(goal)
        self.assertGreaterEqual(len(milestones), 2)
        self.assertEqual(milestones[0]["execution_type"], "immediate")


if __name__ == "__main__":
    unittest.main()
