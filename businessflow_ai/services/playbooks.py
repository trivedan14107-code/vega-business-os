"""Curated 1-Click Business Playbooks for Vega Business OS."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BusinessPlaybook:
    playbook_id: str
    title: str
    category: str  # "finance", "operations", "sales", "executive", "support"
    icon: str
    description: str
    estimated_time_saved_minutes: int
    specialist_roles: tuple[str, ...]
    prompt_template: str
    parameters: list[dict[str, Any]] = field(default_factory=list)


PLAYBOOKS: list[BusinessPlaybook] = [
    BusinessPlaybook(
        playbook_id="receivables_recovery",
        title="Receivables Recovery & Invoice Chase",
        category="finance",
        icon="💰",
        description="Audit unpaid invoices, draft polite payment reminders to overdue clients, log tracking to Google Sheets, and alert the finance channel.",
        estimated_time_saved_minutes=45,
        specialist_roles=("finance_collection", "spreadsheet", "communication"),
        prompt_template="Audit all unpaid invoices older than 14 days, draft customized payment reminders via Gmail, update the payment recovery tracking sheet in Google Sheets, and post a receivables summary to Slack.",
    ),
    BusinessPlaybook(
        playbook_id="executive_sprint_kickoff",
        title="Executive Sprint Kickoff & Team Sync",
        category="executive",
        icon="📅",
        description="Coordinate sprint planning, schedule team review on Google Meet with conferencing link, invite lead designer Venu, and post agenda to Slack.",
        estimated_time_saved_minutes=30,
        specialist_roles=("meeting", "communication"),
        prompt_template="Schedule a 30-minute Sprint Kickoff meeting on Google Meet for tomorrow at 10:00 AM, invite Venu (Lead Designer), and broadcast the meeting link and agenda to the team on Slack.",
    ),
    BusinessPlaybook(
        playbook_id="weekly_financial_audit",
        title="Weekly Financial Summary & Sheet Log",
        category="finance",
        icon="📊",
        description="Compile weekly revenue figures, record detailed audit rows into Google Sheets, and email an executive brief to company leadership.",
        estimated_time_saved_minutes=60,
        specialist_roles=("spreadsheet", "finance_collection"),
        prompt_template="Compile this week's revenue and expense summary, append transaction records to the Executive Finance Log in Google Sheets, and prepare an executive email digest.",
    ),
    BusinessPlaybook(
        playbook_id="inventory_procurement_rfq",
        title="Supply Chain Triage & Supplier RFQ",
        category="operations",
        icon="📦",
        description="Inspect inventory levels against safety thresholds, generate vendor quotation requests, and request owner approval before purchase orders.",
        estimated_time_saved_minutes=50,
        specialist_roles=("inventory", "procurement"),
        prompt_template="Review current stock levels, identify items below reorder threshold, prepare supplier RFQ emails for pricing quotes, and request owner purchase approval.",
    ),
    BusinessPlaybook(
        playbook_id="support_triage_escalation",
        title="Customer Support Triage & Ticket Resolver",
        category="support",
        icon="🚀",
        description="Review incoming customer inquiries, draft verified resolution responses from knowledge base, and escalate refund requests to the owner.",
        estimated_time_saved_minutes=35,
        specialist_roles=("customer_support", "communication"),
        prompt_template="Triage all pending customer support inquiries, draft verified solution responses from knowledge base, and escalate any refund requests to the owner for approval.",
    ),
]


def list_playbooks() -> list[dict[str, Any]]:
    """Return serializable list of business playbooks."""
    return [
        {
            "playbook_id": p.playbook_id,
            "title": p.title,
            "category": p.category,
            "icon": p.icon,
            "description": p.description,
            "estimated_time_saved_minutes": p.estimated_time_saved_minutes,
            "specialist_roles": list(p.specialist_roles),
            "prompt_template": p.prompt_template,
        }
        for p in PLAYBOOKS
    ]


def get_playbook(playbook_id: str) -> BusinessPlaybook | None:
    """Find playbook by ID."""
    for p in PLAYBOOKS:
        if p.playbook_id == playbook_id:
            return p
    return None
