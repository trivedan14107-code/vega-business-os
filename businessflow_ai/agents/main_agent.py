"""LangGraph implementation of the Business Second Brain Main Agent."""

from datetime import UTC, datetime

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from businessflow_ai.agents.planner import GoalPlanner
from businessflow_ai.agents.templates import get_agent_template
from businessflow_ai.graph import MainAgentState
from businessflow_ai.models import AgentStatus, AuditEvent, TaskExecution, TaskStatus
from businessflow_ai.services import (
    AccessController,
    AgentRegistry,
    ExecutionEngine,
    MockExecutionEngine,
    PolicyEngine,
)


def build_main_agent(
    planner: GoalPlanner,
    registry: AgentRegistry,
    policy: PolicyEngine | None = None,
    execution_engine: ExecutionEngine | None = None,
    access_controller: AccessController | None = None,
):
    policy_engine = policy or PolicyEngine()
    executor = execution_engine or MockExecutionEngine()

    def understand_goal(state: MainAgentState) -> dict:
        plan = planner.plan(state["owner_goal"])
        return {
            "plan": plan,
            "audit_events": [{"event": "goal_understood", "intent": plan.intent}],
        }

    def resolve_specialists(state: MainAgentState) -> dict:
        if state["plan"] is None:
            raise ValueError("Goal plan is missing")

        resolved = []
        audit = []
        # Preserve hard dependencies even if a model returns roles in another order.
        # A meeting must exist before the communication agent can share its link.
        priority = {"meeting": 10, "communication": 20}
        requests = sorted(
            state["plan"].specialists,
            key=lambda item: priority.get(item.role, 15),
        )
        for request in requests:
            template = get_agent_template(request.role)
            policy_engine.approve_agent_template(template)
            existing = registry.find_agent(state["company_id"], template.role)
            agent = existing or registry.create_agent(
                state["company_id"], template, request.responsibility
            )
            resolved.append(agent)
            audit.append(
                {
                    "event": "agent_reused" if existing else "agent_created",
                    "agent_id": str(agent.agent_id),
                    "role": agent.role,
                }
            )
        return {"resolved_agents": resolved, "audit_events": audit}

    def create_execution(state: MainAgentState) -> dict:
        roles = [agent.role for agent in state["resolved_agents"]]
        requires_approval = policy_engine.requires_human_approval(roles)
        task = TaskExecution(
            company_id=state["company_id"],
            owner_goal=state["owner_goal"],
            assigned_agent_ids=[agent.agent_id for agent in state["resolved_agents"]],
            requires_approval=requires_approval,
            thread_id=state.get("thread_id"),
            status=TaskStatus.WAITING_APPROVAL if requires_approval else TaskStatus.PLANNED,
        )
        registry.save_task(task)
        registry.record_event(
            AuditEvent(
                company_id=state["company_id"],
                event_type="task_planned",
                details={"task_id": str(task.task_id), "roles": roles},
            )
        )
        return {
            "task": task,
            "audit_events": [{"event": "task_planned", "task_id": str(task.task_id)}],
        }

    def route_for_approval(state: MainAgentState) -> str:
        if state["task"] is None:
            raise ValueError("Task execution is missing")
        return "request_approval" if state["task"].requires_approval else "execute_specialists"

    def check_access(state: MainAgentState) -> dict:
        if state["task"] is None:
            raise ValueError("Task execution is missing")
        requests = (
            access_controller.requests_for(state["company_id"], state["resolved_agents"])
            if access_controller
            else []
        )
        if not requests:
            return {"access_requests": [], "audit_events": [{"event": "access_verified"}]}

        task = state["task"].model_copy(
            update={
                "status": TaskStatus.WAITING_ACCESS,
                "access_requests": requests,
                "updated_at": datetime.now(UTC),
            }
        )
        registry.save_task(task)
        return {
            "task": task,
            "access_requests": requests,
            "audit_events": [{"event": "access_required", "requests": requests}],
        }

    def route_after_access_check(state: MainAgentState) -> str:
        return "report_access_required" if state["access_requests"] else route_for_approval(state)

    def report_access_required(state: MainAgentState) -> dict:
        providers = ", ".join(
            sorted({str(request["provider"]) for request in state["access_requests"]})
        )
        return {
            "final_response": (
                f"Vega needs access to: {providers}. "
                "Please connect the app and then retry the request."
            ),
            "audit_events": [{"event": "access_request_reported"}],
        }

    def request_approval(state: MainAgentState) -> dict:
        if state["task"] is None:
            raise ValueError("Task execution is missing")
        decision = bool(
            interrupt(
                {
                    "task_id": str(state["task"].task_id),
                    "question": "Approve specialist execution?",
                    "roles": [agent.role for agent in state["resolved_agents"]],
                }
            )
        )
        status = TaskStatus.RUNNING if decision else TaskStatus.REJECTED
        task = state["task"].model_copy(
            update={"status": status, "updated_at": datetime.now(UTC)}
        )
        registry.save_task(task)
        return {
            "approval_decision": decision,
            "task": task,
            "audit_events": [{"event": "approval_recorded", "approved": decision}],
        }

    def route_after_approval(state: MainAgentState) -> str:
        return "execute_specialists" if state["approval_decision"] else "report_rejection"

    def execute_specialists(state: MainAgentState) -> dict:
        if state["task"] is None:
            raise ValueError("Task execution is missing")

        results = []
        for agent in state["resolved_agents"]:
            registry.set_agent_status(agent.agent_id, status=AgentStatus.ACTIVE)
            try:
                results.append(
                    executor.execute(
                        agent, state["owner_goal"], results, str(state["task"].task_id)
                    )
                )
            finally:
                registry.set_agent_status(agent.agent_id, status=AgentStatus.IDLE)

        task = state["task"].model_copy(
            update={
                "status": TaskStatus.RUNNING,
                "execution_results": results,
                "updated_at": datetime.now(UTC),
            }
        )
        registry.save_task(task)
        return {
            "task": task,
            "execution_results": results,
            "audit_events": [
                {"event": "specialist_executed", "role": result["role"]}
                for result in results
            ],
        }

    def verify_results(state: MainAgentState) -> dict:
        if state["task"] is None:
            raise ValueError("Task execution is missing")
        verification = [executor.verify(result) for result in state["execution_results"]]
        completed = bool(verification) and all(item["verified"] for item in verification)
        task = state["task"].model_copy(
            update={
                "status": TaskStatus.COMPLETED if completed else TaskStatus.FAILED,
                "verification_results": verification,
                "updated_at": datetime.now(UTC),
            }
        )
        registry.save_task(task)
        return {
            "task": task,
            "verification_results": verification,
            "audit_events": [{"event": "results_verified", "success": completed}],
        }

    def report_completion(state: MainAgentState) -> dict:
        roles = ", ".join(result["role"] for result in state["execution_results"])
        adapter = state["execution_results"][0]["adapter"]
        meet_url = next(
            (
                item.get("meet_url")
                for item in state["verification_results"] + state["execution_results"]
                if item.get("meet_url")
            ),
            None,
        )
        meeting_result = next(
            (
                result
                for result in state["execution_results"]
                if result.get("adapter") == "google_calendar"
            ),
            None,
        )
        meeting_note = ""
        if meeting_result:
            meeting_note = (
                f"\nMeeting: {meeting_result.get('title')}"
                f"\nStarts: {meeting_result.get('start_time')}"
                f"\nGoogle Meet: {meet_url}"
                f"\nCalendar event: {meeting_result.get('event_url')}"
            )
        return {
            "final_response": (
                f"Vega completed and verified the work with: {roles}. "
                f"Execution adapter: {adapter}.{meeting_note}"
            ),
            "audit_events": [{"event": "completion_reported"}],
        }

    def report_rejection(state: MainAgentState) -> dict:
        return {
            "final_response": "Vega stopped the task. No specialist action was performed.",
            "audit_events": [{"event": "rejection_reported"}],
        }

    builder = StateGraph(MainAgentState)
    builder.add_node("understand_goal", understand_goal)
    builder.add_node("resolve_specialists", resolve_specialists)
    builder.add_node("create_execution", create_execution)
    builder.add_node("check_access", check_access)
    builder.add_node("report_access_required", report_access_required)
    builder.add_node("request_approval", request_approval)
    builder.add_node("execute_specialists", execute_specialists)
    builder.add_node("verify_results", verify_results)
    builder.add_node("report_completion", report_completion)
    builder.add_node("report_rejection", report_rejection)

    builder.add_edge(START, "understand_goal")
    builder.add_edge("understand_goal", "resolve_specialists")
    builder.add_edge("resolve_specialists", "create_execution")
    builder.add_edge("create_execution", "check_access")
    builder.add_conditional_edges("check_access", route_after_access_check)
    builder.add_conditional_edges("request_approval", route_after_approval)
    builder.add_edge("execute_specialists", "verify_results")
    builder.add_edge("verify_results", "report_completion")
    builder.add_edge("report_completion", END)
    builder.add_edge("report_rejection", END)
    builder.add_edge("report_access_required", END)
    serializer = JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("businessflow_ai.models.platform", "AgentDefinition"),
            ("businessflow_ai.models.platform", "AgentPlan"),
            ("businessflow_ai.models.platform", "AgentStatus"),
            ("businessflow_ai.models.platform", "SpecialistRequest"),
            ("businessflow_ai.models.platform", "TaskExecution"),
            ("businessflow_ai.models.platform", "TaskStatus"),
        ]
    )
    return builder.compile(checkpointer=InMemorySaver(serde=serializer))
