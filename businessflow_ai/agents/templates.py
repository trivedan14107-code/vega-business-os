"""Approved templates from which the Main Agent may create specialists."""

from dataclasses import dataclass

from businessflow_ai.models import RiskLevel


@dataclass(frozen=True)
class AgentTemplate:
    role: str
    responsibilities: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    forbidden_tools: tuple[str, ...]
    permissions: tuple[str, ...]
    business_rules: tuple[str, ...]
    risk_level: RiskLevel


AGENT_TEMPLATES: dict[str, AgentTemplate] = {
    "meeting": AgentTemplate(
        role="meeting",
        responsibilities=("Plan and manage company meetings",),
        allowed_tools=("calendar.read", "calendar.create", "google_meet.create"),
        forbidden_tools=("calendar.delete", "calendar.share_external"),
        permissions=("read_availability", "draft_meeting", "create_meeting_with_approval"),
        business_rules=("Use Google Meet first and Zoom only as fallback",),
        risk_level=RiskLevel.MEDIUM,
    ),
    "communication": AgentTemplate(
        role="communication",
        responsibilities=("Prepare and deliver approved company communications",),
        allowed_tools=("slack.send",),
        forbidden_tools=("contact.delete", "bulk_broadcast.unapproved"),
        permissions=("draft_message", "send_message_with_approval"),
        business_rules=("Use Slack first for internal communication",),
        risk_level=RiskLevel.HIGH,
    ),
    "finance_collection": AgentTemplate(
        role="finance_collection",
        responsibilities=("Monitor receivables and resolve overdue invoice exceptions",),
        allowed_tools=(
            "invoice.read",
            "payment_status.read",
            "reminder.draft",
            "gmail.send",
            "owner.notify",
        ),
        forbidden_tools=("money.transfer", "refund.issue", "invoice.amount.modify"),
        permissions=("read_receivables", "draft_payment_reminder"),
        business_rules=("Never modify money or accounting records",),
        risk_level=RiskLevel.MEDIUM,
    ),
    "sales_followup": AgentTemplate(
        role="sales_followup",
        responsibilities=("Monitor and prepare follow-ups for unanswered sales leads",),
        allowed_tools=("crm.read", "lead.score", "followup.draft", "owner.notify"),
        forbidden_tools=("deal.discount", "contract.sign"),
        permissions=("read_leads", "draft_sales_followup"),
        business_rules=("Never offer discounts or commit contract terms",),
        risk_level=RiskLevel.MEDIUM,
    ),
    "customer_support": AgentTemplate(
        role="customer_support",
        responsibilities=("Triage customer questions and prepare safe responses",),
        allowed_tools=("support_ticket.read", "knowledge.search", "response.draft"),
        forbidden_tools=("refund.issue", "account.delete"),
        permissions=("read_tickets", "draft_support_response"),
        business_rules=("Escalate refunds and account changes to the owner",),
        risk_level=RiskLevel.MEDIUM,
    ),
    "inventory": AgentTemplate(
        role="inventory",
        responsibilities=("Monitor inventory conditions and recommend replenishment",),
        allowed_tools=("inventory.read", "reorder.recommend", "owner.notify"),
        forbidden_tools=("purchase_order.submit", "supplier.payment"),
        permissions=("read_inventory", "recommend_reorder"),
        business_rules=("Never place an order without owner approval",),
        risk_level=RiskLevel.MEDIUM,
    ),
    "procurement": AgentTemplate(
        role="procurement",
        responsibilities=("Collect quotations and prepare purchase recommendations",),
        allowed_tools=(
            "vendor_directory.search",
            "gmail.send",
            "procurement.create_approval_request",
        ),
        forbidden_tools=("purchase_order.submit", "financial_transfer"),
        permissions=("request_authorized_quotes", "prepare_purchase_approval"),
        business_rules=("Never place an order or transfer money",),
        risk_level=RiskLevel.HIGH,
    ),
    "sales_reporting": AgentTemplate(
        role="sales_reporting",
        responsibilities=("Prepare recurring sales performance reports",),
        allowed_tools=("crm.read", "gmail.send", "owner.notify"),
        forbidden_tools=("crm.update", "deal.modify"),
        permissions=("read_sales_metrics", "prepare_sales_report"),
        business_rules=("Report source data and do not modify sales records",),
        risk_level=RiskLevel.LOW,
    ),
    "spreadsheet": AgentTemplate(
        role="spreadsheet",
        responsibilities=("Manage company spreadsheets, records, and data logs",),
        allowed_tools=("sheets.read", "sheets.append", "sheets.create_log"),
        forbidden_tools=("sheets.delete", "sheets.share_public"),
        permissions=("read_spreadsheet", "append_spreadsheet_row"),
        business_rules=("Record accurate business rows and never delete existing sheets without approval",),
        risk_level=RiskLevel.MEDIUM,
    ),
    "voice_calling": AgentTemplate(
        role="voice_calling",
        responsibilities=("Conduct natural AI voice calls with teammates or clients and execute warm handoffs",),
        allowed_tools=("voice.call", "voice.synthesize", "voice.transfer_to_owner", "voice.transcribe"),
        forbidden_tools=("voice.unauthorized_commit", "voice.record_without_notice"),
        permissions=("initiate_voice_call", "transfer_call_to_owner", "transcribe_call_summary"),
        business_rules=("Converse strictly on the owner's goal and initiate a warm transfer if complex blockers or human approval are requested",),
        risk_level=RiskLevel.HIGH,
    ),
}


def get_agent_template(role: str) -> AgentTemplate:
    normalized = role.strip().lower()
    if normalized not in AGENT_TEMPLATES:
        raise ValueError(f"Unsupported specialist role: {role}")
    return AGENT_TEMPLATES[normalized]

