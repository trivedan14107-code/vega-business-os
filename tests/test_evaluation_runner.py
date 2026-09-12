"""Behavioral tests sourced directly from the versioned evaluation dataset."""

import unittest

from businessflow_ai.evaluation import evaluate


class EvaluationRunnerTests(unittest.TestCase):
    def test_implemented_dataset_scenarios_pass(self) -> None:
        results, pending = evaluate()

        self.assertGreaterEqual(len(results), 10)
        self.assertEqual([item for item in results if not item.passed], [])
        self.assertEqual(len(results) + pending, 50)


if __name__ == "__main__":
    unittest.main()
