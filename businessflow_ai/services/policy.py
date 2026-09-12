"""Deterministic policy checks for agent creation and task execution."""

from typing import Any

from businessflow_ai.agents.templates import AGENT_TEMPLATES, AgentTemplate
from businessflow_ai.models import RiskLevel


class PolicyViolation(ValueError):
    """Raised when an agent or action exceeds approved authority."""


class PolicyEngine:
    def approve_agent_template(self, template: AgentTemplate) -> None:
        approved = AGENT_TEMPLATES.get(template.role)
        if approved != template:
            raise PolicyViolation(f"Agent template is not approved: {template.role}")

        overlap = set(template.allowed_tools) & set(template.forbidden_tools)
        if overlap:
            raise PolicyViolation(f"Tools cannot be both allowed and forbidden: {sorted(overlap)}")

    def requires_human_approval(self, roles: list[str]) -> bool:
        external_writers = {
            "communication",
            "finance_collection",
            "meeting",
            "procurement",
            "sales_followup",
            "spreadsheet",
        }
        return any(role in external_writers for role in roles)

    def classify_action_risk(self, action: str) -> RiskLevel:
        normalized = action.lower()
        if any(term in normalized for term in ("transfer", "delete all", "entire customer database")):
            return RiskLevel.CRITICAL
        if any(term in normalized for term in ("refund", "purchase order", "send", "create")):
            return RiskLevel.HIGH
        if any(term in normalized for term in ("read", "summarize", "report")):
            return RiskLevel.LOW
        return RiskLevel.MEDIUM

    def action_requires_human_approval(
        self, proposed_action: dict[str, Any], company_policy: dict[str, Any]
    ) -> bool:
        action = str(proposed_action.get("action", ""))
        amount = proposed_action.get("amount_inr")
        if action == "refund":
            threshold = company_policy.get("refund_approval_threshold_inr")
            return threshold is None or amount is None or amount > threshold
        if action == "place_purchase_order":
            threshold = company_policy.get("purchase_approval_threshold_inr")
            return threshold is None or amount is None or amount > threshold
        return self.classify_action_risk(action) in {RiskLevel.HIGH, RiskLevel.CRITICAL}
