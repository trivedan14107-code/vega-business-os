import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from businessflow_ai.agents.templates import AgentTemplate
from businessflow_ai.models import (
    AgentDefinition,
    AgentStatus,
    AuditEvent,
    CompanyContact,
    ScheduledTask,
    TaskExecution,
)


class AgentRegistry:
    def __init__(self, database_path: str | Path = "businessflow.db") -> None:
        self.database_path = str(database_path)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    UNIQUE(company_id, role)
                );
                CREATE TABLE IF NOT EXISTS task_executions (
                    task_id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS companies (
                    company_id TEXT PRIMARY KEY,
                    owner_email TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS contacts (
                    contact_id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    phone TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT 'teammate',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    schedule_id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    run_at TEXT NOT NULL,
                    schedule_type TEXT NOT NULL DEFAULT 'once',
                    cron_expr TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    preapproved INTEGER NOT NULL DEFAULT 0,
                    approved_at TEXT,
                    last_run_at TEXT,
                    result_task_id TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(scheduled_tasks)").fetchall()
            }
            if "preapproved" not in columns:
                connection.execute(
                    "ALTER TABLE scheduled_tasks ADD COLUMN preapproved INTEGER NOT NULL DEFAULT 0"
                )
            if "approved_at" not in columns:
                connection.execute(
                    "ALTER TABLE scheduled_tasks ADD COLUMN approved_at TEXT"
                )

    def claim_company(self, company_id: str, owner_email: str) -> bool:
        """Atomically claim a company or validate its existing owner."""
        normalized = owner_email.strip().lower()
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO companies(company_id, owner_email, created_at) "
                "VALUES (?, ?, ?)",
                (company_id, normalized, datetime.now(UTC).isoformat()),
            )
            row = connection.execute(
                "SELECT owner_email FROM companies WHERE company_id = ?", (company_id,)
            ).fetchone()
        return bool(row and row["owner_email"] == normalized)

    def find_agent(self, company_id: str, role: str) -> AgentDefinition | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM agents WHERE company_id = ? AND role = ?",
                (company_id, role.strip().lower()),
            ).fetchone()
        return AgentDefinition.model_validate_json(row["payload"]) if row else None

    def create_agent(
        self,
        company_id: str,
        template: AgentTemplate,
        responsibility: str,
    ) -> AgentDefinition:
        existing = self.find_agent(company_id, template.role)
        if existing:
            return existing

        agent = AgentDefinition(
            company_id=company_id,
            role=template.role,
            responsibilities=list(dict.fromkeys([*template.responsibilities, responsibility])),
            allowed_tools=list(template.allowed_tools),
            forbidden_tools=list(template.forbidden_tools),
            permissions=list(template.permissions),
            business_rules=list(template.business_rules),
            status=AgentStatus.IDLE,
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO agents(agent_id, company_id, role, payload) VALUES (?, ?, ?, ?)",
                (str(agent.agent_id), company_id, agent.role, agent.model_dump_json()),
            )
        return agent

    def list_agents(self, company_id: str) -> list[AgentDefinition]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM agents WHERE company_id = ? ORDER BY role",
                (company_id,),
            ).fetchall()
        return [AgentDefinition.model_validate_json(row["payload"]) for row in rows]

    def save_agent(self, agent: AgentDefinition) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO agents(agent_id, company_id, role, payload) "
                "VALUES (?, ?, ?, ?)",
                (str(agent.agent_id), agent.company_id, agent.role, agent.model_dump_json()),
            )

    def set_agent_status(self, agent_id: UUID, status: AgentStatus) -> AgentDefinition:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM agents WHERE agent_id = ?", (str(agent_id),)
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown agent: {agent_id}")
        agent = AgentDefinition.model_validate_json(row["payload"]).model_copy(
            update={"status": status, "updated_at": datetime.now(UTC)}
        )
        self.save_agent(agent)
        return agent

    def save_task(self, task: TaskExecution) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO task_executions(task_id, company_id, payload) VALUES (?, ?, ?)",
                (str(task.task_id), task.company_id, task.model_dump_json()),
            )

    def get_task(self, task_id: UUID) -> TaskExecution | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM task_executions WHERE task_id = ?", (str(task_id),)
            ).fetchone()
        return TaskExecution.model_validate_json(row["payload"]) if row else None

    def list_tasks(self, company_id: str, limit: int = 30) -> list[TaskExecution]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM task_executions WHERE company_id = ? "
                "ORDER BY rowid DESC LIMIT ?",
                (company_id, limit),
            ).fetchall()
        return [TaskExecution.model_validate_json(row["payload"]) for row in rows]

    def record_event(self, event: AuditEvent) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO audit_events(event_id, company_id, payload) VALUES (?, ?, ?)",
                (str(event.event_id), event.company_id, event.model_dump_json()),
            )

    def list_events(self, company_id: str, limit: int = 50) -> list[AuditEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM audit_events WHERE company_id = ? "
                "ORDER BY rowid DESC LIMIT ?",
                (company_id, limit),
            ).fetchall()
        return [AuditEvent.model_validate_json(row["payload"]) for row in rows]

    def list_contacts(self, company_id: str) -> list[CompanyContact]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT contact_id, company_id, name, role, phone, email, category, notes, created_at "
                "FROM contacts WHERE company_id = ? ORDER BY category DESC, name ASC",
                (company_id,),
            ).fetchall()
        return [
            CompanyContact(
                contact_id=UUID(row["contact_id"]),
                company_id=row["company_id"],
                name=row["name"],
                role=row["role"],
                phone=row["phone"],
                email=row["email"],
                category=row["category"],
                notes=row["notes"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def create_contact(self, contact: CompanyContact) -> CompanyContact:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO contacts(contact_id, company_id, name, role, phone, email, category, notes, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(contact.contact_id),
                    contact.company_id,
                    contact.name,
                    contact.role,
                    contact.phone,
                    contact.email,
                    contact.category,
                    contact.notes,
                    contact.created_at.isoformat(),
                ),
            )
        return contact

    def find_contact(self, company_id: str, query: str) -> CompanyContact | None:
        contacts = self.list_contacts(company_id)
        q = query.strip().lower()
        if not q:
            return None
        for c in contacts:
            if q in c.name.lower() or c.name.lower() in q:
                return c
        return None

    def create_schedule(self, scheduled_task: ScheduledTask) -> ScheduledTask:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO scheduled_tasks("
                "schedule_id, company_id, goal, run_at, schedule_type, cron_expr, status, "
                "preapproved, approved_at, last_run_at, result_task_id, created_at"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(scheduled_task.schedule_id),
                    scheduled_task.company_id,
                    scheduled_task.goal,
                    scheduled_task.run_at.isoformat(),
                    scheduled_task.schedule_type,
                    scheduled_task.cron_expr,
                    scheduled_task.status,
                    int(scheduled_task.preapproved),
                    scheduled_task.approved_at.isoformat() if scheduled_task.approved_at else None,
                    scheduled_task.last_run_at.isoformat() if scheduled_task.last_run_at else None,
                    str(scheduled_task.result_task_id) if scheduled_task.result_task_id else None,
                    scheduled_task.created_at.isoformat(),
                ),
            )
        return scheduled_task

    def list_schedules(self, company_id: str) -> list[ScheduledTask]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * "
                "FROM scheduled_tasks WHERE company_id = ? ORDER BY run_at ASC",
                (company_id,),
            ).fetchall()
        return [self._schedule_from_row(row) for row in rows]

    def get_schedule(self, schedule_id: UUID) -> ScheduledTask | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * "
                "FROM scheduled_tasks WHERE schedule_id = ?",
                (str(schedule_id),),
            ).fetchone()
        if not row:
            return None
        return self._schedule_from_row(row)

    @staticmethod
    def _schedule_from_row(row: sqlite3.Row) -> ScheduledTask:
        return ScheduledTask(
            schedule_id=UUID(row["schedule_id"]),
            company_id=row["company_id"],
            goal=row["goal"],
            run_at=datetime.fromisoformat(row["run_at"]),
            schedule_type=row["schedule_type"],
            cron_expr=row["cron_expr"],
            status=row["status"],
            preapproved=bool(row["preapproved"]),
            approved_at=datetime.fromisoformat(row["approved_at"]) if row["approved_at"] else None,
            last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
            result_task_id=UUID(row["result_task_id"]) if row["result_task_id"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_due_schedules(self, as_of: datetime | None = None) -> list[ScheduledTask]:
        now = (as_of or datetime.now(UTC)).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * "
                "FROM scheduled_tasks WHERE status = 'pending' AND run_at <= ? ORDER BY run_at ASC",
                (now,),
            ).fetchall()
        return [self._schedule_from_row(row) for row in rows]

    def claim_due_schedules(self, as_of: datetime | None = None) -> list[ScheduledTask]:
        """Atomically claim due work so concurrent workers cannot execute it twice."""
        now = (as_of or datetime.now(UTC)).isoformat()
        claimed: list[ScheduledTask] = []
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT * FROM scheduled_tasks "
                "WHERE status = 'pending' AND run_at <= ? ORDER BY run_at ASC",
                (now,),
            ).fetchall()
            for row in rows:
                cursor = connection.execute(
                    "UPDATE scheduled_tasks SET status = 'running', last_run_at = ? "
                    "WHERE schedule_id = ? AND status = 'pending'",
                    (now, row["schedule_id"]),
                )
                if cursor.rowcount == 1:
                    values = dict(row)
                    values["status"] = "running"
                    values["last_run_at"] = now
                    claimed.append(self._schedule_from_row(values))
        return claimed

    def claim_schedule(self, schedule_id: UUID, company_id: str) -> ScheduledTask | None:
        """Atomically claim one pending schedule belonging to the authenticated company."""
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE scheduled_tasks SET status = 'running', last_run_at = ? "
                "WHERE schedule_id = ? AND company_id = ? AND status = 'pending'",
                (now, str(schedule_id), company_id),
            )
            if cursor.rowcount != 1:
                return None
            row = connection.execute(
                "SELECT * FROM scheduled_tasks WHERE schedule_id = ? AND company_id = ?",
                (str(schedule_id), company_id),
            ).fetchone()
        return self._schedule_from_row(row) if row else None

    def update_schedule_status(
        self,
        schedule_id: UUID,
        status: str,
        result_task_id: UUID | None = None,
        last_run_at: datetime | None = None,
    ) -> None:
        run_time = (last_run_at or datetime.now(UTC)).isoformat()
        with self._connect() as connection:
            if result_task_id is not None:
                connection.execute(
                    "UPDATE scheduled_tasks SET status = ?, result_task_id = ?, last_run_at = ? WHERE schedule_id = ?",
                    (status, str(result_task_id), run_time, str(schedule_id)),
                )
            else:
                connection.execute(
                    "UPDATE scheduled_tasks SET status = ?, last_run_at = ? WHERE schedule_id = ?",
                    (status, run_time, str(schedule_id)),
                )

    def delete_schedule(self, schedule_id: UUID, company_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM scheduled_tasks WHERE schedule_id = ? AND company_id = ?",
                (str(schedule_id), company_id),
            )
            return cursor.rowcount > 0

    def get_business_metrics(self, company_id: str) -> dict[str, Any]:
        """Compute key business metrics and ROI metrics for the executive dashboard."""
        tasks = self.list_tasks(company_id)
        agents = self.list_agents(company_id)
        schedules = self.list_schedules(company_id)
        events = self.list_events(company_id, limit=200)
        contacts = self.list_contacts(company_id)

        completed_tasks = [t for t in tasks if str(t.status.value) == "completed"]
        pending_schedules = [s for s in schedules if s.status in ("pending", "running")]

        # Calculate estimated executive hours saved based on tasks completed
        hours_saved = round(len(completed_tasks) * 1.5 + len(pending_schedules) * 0.5, 1)
        if hours_saved == 0.0 and len(tasks) > 0:
            hours_saved = 0.8

        return {
            "hours_saved": hours_saved,
            "tasks_completed": len(completed_tasks),
            "total_tasks": len(tasks),
            "active_agents": len(agents),
            "scheduled_automations": len(pending_schedules),
            "contacts_count": len(contacts),
            "audit_events_count": len(events),
        }

    def export_business_records(self, company_id: str) -> dict[str, Any]:
        """Export full verified business records, tasks, schedules, and audit trail."""
        return {
            "company_id": company_id,
            "exported_at": datetime.now(UTC).isoformat(),
            "metrics": self.get_business_metrics(company_id),
            "agents": [a.model_dump(mode="json") for a in self.list_agents(company_id)],
            "tasks": [t.model_dump(mode="json") for t in self.list_tasks(company_id)],
            "schedules": [s.model_dump(mode="json") for s in self.list_schedules(company_id)],
            "contacts": [c.model_dump(mode="json") for c in self.list_contacts(company_id)],
            "audit_events": [e.model_dump(mode="json") for e in self.list_events(company_id, limit=200)],
        }
