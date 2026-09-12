"""Direct, deterministic evaluation against the versioned scenario dataset."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from businessflow_ai.agents.planner import RuleBasedGoalPlanner
from businessflow_ai.agents.templates import AGENT_TEMPLATES
from businessflow_ai.services import PolicyEngine

DEFAULT_DATASET = Path(__file__).parents[1] / "data" / "business_second_brain_dataset_v1.1.json"


@dataclass(frozen=True)
class EvaluationResult:
    scenario_id: str
    family: str
    passed: bool
    detail: str


def load_dataset(path: Path = DEFAULT_DATASET) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _business_intent(row: dict[str, Any]) -> tuple[bool, str]:
    expected_role = {"finance": "finance_collection", "sales": "sales_followup"}[
        row["expected"]["domain"]
    ]
    roles = {item.role for item in RuleBasedGoalPlanner().plan(row["owner_request"]).specialists}
    return expected_role in roles, f"expected role {expected_role}; planned {sorted(roles)}"


def _capability_identification(row: dict[str, Any]) -> tuple[bool, str]:
    capability_roles = {
        "meeting": "meeting",
        "team_communication": "communication",
        "vendor_sourcing": "procurement",
        "vendor_comparison": "procurement",
        "purchase_approval_preparation": "procurement",
    }
    expected = {
        capability_roles[item] for item in row["expected"]["required_capabilities"]
    }
    actual = {item.role for item in RuleBasedGoalPlanner().plan(row["owner_request"]).specialists}
    return actual == expected, f"expected {sorted(expected)}; planned {sorted(actual)}"


def _agent_specification(row: dict[str, Any]) -> tuple[bool, str]:
    expected = row["expected"]
    role = expected["role"]
    template = AGENT_TEMPLATES.get(role)
    if template is None:
        return False, f"missing approved template for {role}"
    missing_tools = sorted(set(expected["allowed_tools"]) - set(template.allowed_tools))
    return not missing_tools, f"role {role}; missing tools {missing_tools}"


def _risk_classification(row: dict[str, Any]) -> tuple[bool, str]:
    expected = row["expected"]["risk_level"]
    actual = PolicyEngine().classify_action_risk(row["action"]).name
    return actual == expected, f"expected {expected}; classified {actual}"


def _approval(row: dict[str, Any]) -> tuple[bool, str]:
    actual = PolicyEngine().action_requires_human_approval(
        row["proposed_action"], row["policy"]
    )
    expected = row["expected"]["approval_required"]
    return actual == expected, f"expected approval={expected}; actual={actual}"


EVALUATORS: dict[str, Callable[[dict[str, Any]], tuple[bool, str]]] = {
    "business_intent": _business_intent,
    "capability_identification": _capability_identification,
    "agent_specification": _agent_specification,
    "risk_classification": _risk_classification,
    "approval": _approval,
}


def evaluate(path: Path = DEFAULT_DATASET) -> tuple[list[EvaluationResult], int]:
    dataset = load_dataset(path)
    results: list[EvaluationResult] = []
    pending = 0
    for family, scenarios in dataset["families"].items():
        evaluator = EVALUATORS.get(family)
        if evaluator is None:
            pending += len(scenarios)
            continue
        for row in scenarios:
            try:
                passed, detail = evaluator(row)
            except (KeyError, TypeError, ValueError) as exc:
                passed, detail = False, str(exc)
            results.append(EvaluationResult(row["scenario_id"], family, passed, detail))
    return results, pending


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate BusinessFlow against its dataset")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()
    results, pending = evaluate(args.dataset)
    passed = sum(item.passed for item in results)
    print(f"Dataset: {args.dataset}")
    print(f"Behavioral checks: {passed}/{len(results)} passed")
    print(f"Scenarios awaiting evaluators: {pending}")
    for result in results:
        if not result.passed:
            print(f"FAIL {result.scenario_id} ({result.family}): {result.detail}")
    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
