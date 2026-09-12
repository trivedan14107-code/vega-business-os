"""Persistent-agent and temporary-execution domain models."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class AgentStatus(StrEnum):
    CREATED = "created"
    IDLE = "idle"
    ACTIVE = "active"
    WAITING = "waiting"
    BLOCKED = "blocked"
    DISABLED = "disabled"


class TaskStatus(StrEnum):
    PLANNED = "planned"
    WAITING_ACCESS = "waiting_access"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OutcomeState(StrEnum):
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    WAITING = "waiting"
    BLOCKED = "blocked"
    REQUIRES_HUMAN = "requires_human"


class PlatformModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SpecialistRequest(PlatformModel):
    role: str = Field(min_length=2, max_length=80)
    responsibility: str = Field(min_length=3, max_length=300)


class AgentPlan(PlatformModel):
    intent: str = Field(min_length=2, max_length=120)
    summary: str = Field(min_length=3, max_length=500)
    specialists: list[SpecialistRequest] = Field(min_length=1, max_length=6)


class AgentDefinition(PlatformModel):
    agent_id: UUID = Field(default_factory=uuid4)
    company_id: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=2, max_length=80)
    responsibilities: list[str] = Field(min_length=1)
    allowed_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    business_rules: list[str] = Field(default_factory=list)
    memory: dict[str, Any] = Field(default_factory=dict)
    status: AgentStatus = AgentStatus.CREATED
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TaskExecution(PlatformModel):
    task_id: UUID = Field(default_factory=uuid4)
    company_id: str = Field(min_length=1, max_length=80)
    owner_goal: str = Field(min_length=1, max_length=2000)
    assigned_agent_ids: list[UUID] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PLANNED
    requires_approval: bool = False
    access_requests: list[dict[str, Any]] = Field(default_factory=list)
    execution_results: list[dict[str, Any]] = Field(default_factory=list)
    verification_results: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AuditEvent(PlatformModel):
    event_id: UUID = Field(default_factory=uuid4)
    company_id: str
    event_type: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class CompanyContact(PlatformModel):
    contact_id: UUID = Field(default_factory=uuid4)
    company_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=100)
    phone: str = Field(default="", max_length=30)
    email: str = Field(default="", max_length=120)
    category: str = Field(default="teammate")  # "teammate" | "client"
    notes: str = Field(default="", max_length=300)
    created_at: datetime = Field(default_factory=utc_now)


class ScheduledTask(PlatformModel):
    schedule_id: UUID = Field(default_factory=uuid4)
    company_id: str = Field(min_length=1, max_length=80)
    goal: str = Field(min_length=3, max_length=2000)
    run_at: datetime
    schedule_type: str = Field(default="once")  # "once" | "recurring"
    cron_expr: str | None = None
    status: str = Field(default="pending")  # pending | running | waiting_approval | completed | cancelled | failed
    preapproved: bool = False
    approved_at: datetime | None = None
    last_run_at: datetime | None = None
    result_task_id: UUID | None = None
    created_at: datetime = Field(default_factory=utc_now)

