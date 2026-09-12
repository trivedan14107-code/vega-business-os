"""Integrity and platform-compatibility checks for the evaluation dataset."""

import json
import re
import unittest
from collections import Counter
from pathlib import Path

from businessflow_ai.agents.templates import AGENT_TEMPLATES
from businessflow_ai.models import AgentStatus, OutcomeState, RiskLevel

DATASET_PATH = Path("data/business_second_brain_dataset_v1.1.json")


class EvaluationDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        cls.rows = [
            row
            for scenarios in cls.dataset["families"].values()
            for row in scenarios
        ]

    def test_declared_counts_match_contents(self) -> None:
        stats = self.dataset["dataset_statistics"]
        self.assertEqual(stats["families"], len(self.dataset["families"]))
        self.assertEqual(stats["examples"], len(self.rows))
        self.assertEqual(stats["split_counts"], dict(Counter(r["split"] for r in self.rows)))
        self.assertEqual(
            stats["difficulty_counts"],
            dict(Counter(r["difficulty"] for r in self.rows)),
        )

    def test_scenario_ids_are_unique_and_well_formed(self) -> None:
        ids = [row["scenario_id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(re.fullmatch(r"[A-Z]{3,4}-\d{3}", item) for item in ids))

    def test_every_scenario_has_one_normalized_expected_object(self) -> None:
        self.assertTrue(all(isinstance(row.get("expected"), dict) for row in self.rows))
        self.assertTrue(all("expected_scorecard" not in row for row in self.rows))
        self.assertTrue(all("expected_message" not in row for row in self.rows))

    def test_label_conventions_are_supported_by_platform(self) -> None:
        labels = self.dataset["label_conventions"]
        self.assertEqual(set(labels["risk_levels"]), {item.name for item in RiskLevel})
        self.assertEqual(set(labels["agent_states"]), {item.name for item in AgentStatus})
        self.assertEqual(set(labels["outcome_states"]), {item.name for item in OutcomeState})

    def test_canonical_roles_have_approved_templates(self) -> None:
        roles = set(self.dataset["compatibility"]["canonical_roles"])
        self.assertTrue(roles.issubset(set(AGENT_TEMPLATES)))


if __name__ == "__main__":
    unittest.main()
