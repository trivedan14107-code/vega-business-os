"""Specialist execution boundary and safe mock adapter."""

from typing import Any, Protocol
from uuid import uuid4

from businessflow_ai.models import AgentDefinition


class ExecutionEngine(Protocol):
    def execute(
        self,
        agent: AgentDefinition,
        owner_goal: str,
        prior_results: list[dict[str, Any]],
        task_id: str,
    ) -> dict[str, Any]: ...

    def verify(self, result: dict[str, Any]) -> dict[str, Any]: ...


from businessflow_ai.services.pdf_generator import ExecutivePDFReportGenerator


class MockExecutionEngine:
    """Deterministic adapter for testing orchestration without external side effects."""

    def __init__(self, pdf_generator: ExecutivePDFReportGenerator | None = None) -> None:
        self.pdf_generator = pdf_generator or ExecutivePDFReportGenerator()

    def execute(
        self,
        agent: AgentDefinition,
        owner_goal: str,
        prior_results: list[dict[str, Any]],
        task_id: str,
    ) -> dict[str, Any]:
        details: dict[str, Any] = {
            "execution_id": str(uuid4()),
            "agent_id": str(agent.agent_id),
            "role": agent.role,
            "adapter": "mock",
            "success": True,
            "owner_goal": owner_goal,
            "task_id": task_id,
        }

        is_report_goal = any(
            w in owner_goal.lower()
            for w in (
                "summarise", "summarize", "summary", "pdf", "brief", "research",
                "audit", "report", "competitor", "compittators", "invoices", "analysis"
            )
        )

        if agent.role == "meeting":
            details.update(action="meeting.created", platform="google_meet", summary="Google Meet event planned and link generated")
        elif agent.role == "communication":
            meeting = next(
                (result for result in prior_results if result["role"] == "meeting"), None
            )
            comm_summary = "Business communication prepared and sent via notification channel"
            if is_report_goal:
                comm_summary = (
                    "Executive Synthesis Brief:\n"
                    f"• Goal Objective: {owner_goal}\n"
                    "• Specialist Workforce: Multi-agent coordination completed with verified outcomes.\n"
                    "• Key Deliverables: Audit checks passed, metrics synchronized, and team notified."
                )
                _, pdf_url = self.pdf_generator.generate_executive_brief_pdf(
                    task_id=task_id,
                    title="Executive Synthesis Brief",
                    source="Vega Multi-Agent Workforce",
                    summary_text=comm_summary,
                    action_items=[
                        "Review verified deliverables and stakeholder notes",
                        "Verify automated background schedule triggers",
                        "Proceed with operational follow-up items",
                    ],
                )
                details["pdf_url"] = pdf_url

            details.update(
                action="team.notified",
                channel="slack",
                meeting_execution_id=meeting["execution_id"] if meeting else None,
                summary=comm_summary,
            )
        elif agent.role == "finance_collection":
            fin_summary = "Audited receivables, verified invoice records, and prepared payment notifications"
            _, pdf_url = self.pdf_generator.generate_executive_brief_pdf(
                task_id=task_id,
                title="Financial Receivables & Invoice Audit Brief",
                source="Vega Finance Specialist",
                summary_text=(
                    f"Invoice & Receivables Audit Report for '{owner_goal}':\n"
                    "• Verified 12 active client accounts in ledger.\n"
                    "• Identified $14,250 in pending receivables across 3 overdue accounts.\n"
                    "• Automated payment reminders prepared with owner sign-off boundary."
                ),
                action_items=[
                    "Send automated payment reminders to 3 overdue accounts",
                    "Reconcile bank deposit batch with accounts receivable ledger",
                    "Review credit terms for key enterprise accounts",
                ],
                prefix="vega_finance_audit",
            )
            details.update(
                action="receivables.reviewed",
                summary=fin_summary,
                pdf_url=pdf_url,
            )
        elif agent.role == "sales_followup":
            details.update(action="sales_followup.prepared", summary="Reviewed active leads, identified follow-up opportunities, and drafted outreach")
        elif agent.role == "customer_support":
            details.update(action="support_triage.completed", summary="Triaged customer questions, categorized priorities, and prepared safe responses")
        elif agent.role == "inventory":
            inv_summary = "Reviewed stock levels, calculated reorder thresholds, and generated replenishment summary"
            _, pdf_url = self.pdf_generator.generate_executive_brief_pdf(
                task_id=task_id,
                title="Inventory & Stock Replenishment Brief",
                source="Vega Inventory Specialist",
                summary_text=(
                    f"Inventory Analysis for '{owner_goal}':\n"
                    "• Audited 48 SKUs in warehouse database.\n"
                    "• 4 items currently below minimum safety stock threshold.\n"
                    "• Purchase recommendations queued with trusted suppliers."
                ),
                prefix="vega_inventory_brief",
            )
            details.update(
                action="inventory.reviewed",
                summary=inv_summary,
                pdf_url=pdf_url,
            )
        elif agent.role == "procurement":
            details.update(action="purchase_recommendation.prepared", summary="Collected vendor quotations, compared pricing tiers, and drafted purchase recommendation")
        elif agent.role == "sales_reporting":
            sales_summary = "Aggregated sales pipeline metrics, conversion rates, and revenue performance brief"
            _, pdf_url = self.pdf_generator.generate_executive_brief_pdf(
                task_id=task_id,
                title="Executive Sales Pipeline & Performance Report",
                source="Vega Sales Reporting Specialist",
                summary_text=(
                    f"Sales Pipeline Brief for '{owner_goal}':\n"
                    "• Q3 Pipeline Value: $382,000 across 24 qualified opportunities.\n"
                    "• Win Rate: 34.2% (+4.1% MoM); Average Deal Size: $15,900.\n"
                    "• Enterprise Tier deals leading quarterly revenue growth."
                ),
                prefix="vega_sales_report",
            )
            details.update(
                action="sales_report.prepared",
                summary=sales_summary,
                pdf_url=pdf_url,
            )
        elif agent.role == "spreadsheet":
            details.update(action="spreadsheet.row_appended", summary="Logged structured business transaction records to operational spreadsheet")
        elif agent.role == "voice_calling":
            details.update(action="voice_call.completed", summary="Initiated automated AI voice call verification with contact, transcribed intent, and logged outcome")
        else:
            specialist_summary = f"{agent.role} specialist executed and verified task"
            if is_report_goal:
                _, pdf_url = self.pdf_generator.generate_executive_brief_pdf(
                    task_id=task_id,
                    title=f"Executive Brief - {agent.role.replace('_', ' ').title()}",
                    source=f"Vega {agent.role} Specialist",
                    summary_text=f"Outcome Brief for '{owner_goal}':\n• {specialist_summary}\n• Verified milestones and recorded immutable audit receipt.",
                )
                details["pdf_url"] = pdf_url
            details.update(action=f"{agent.role}.completed", summary=specialist_summary)
        return details

    def verify(self, result: dict[str, Any]) -> dict[str, Any]:
        required = {"execution_id", "agent_id", "role", "adapter", "action", "success"}
        missing = sorted(required - result.keys())
        verified = result.get("success") is True and not missing
        return {
            "execution_id": result.get("execution_id"),
            "role": result.get("role"),
            "verified": verified,
            "missing_fields": missing,
            "adapter": result.get("adapter"),
        }
