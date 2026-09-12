"""Autonomous Background Task Scheduler for Vega Business OS."""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from businessflow_ai.models import ScheduledTask
from businessflow_ai.services.registry import AgentRegistry

logger = logging.getLogger(__name__)


class VegaSchedulerService:
    """Manages scheduled multi-agent task execution in background worker loops."""

    def __init__(
        self,
        registry: AgentRegistry,
        executor_callback: Callable[[str, str], dict[str, Any]],
        approval_callback: Callable[[str, str, bool], dict[str, Any]] | None = None,
        poll_interval_seconds: float = 5.0,
    ) -> None:
        self.registry = registry
        self.executor_callback = executor_callback
        self.approval_callback = approval_callback
        self.poll_interval_seconds = poll_interval_seconds
        self._running = False
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Start the background scheduling worker loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._worker_loop())
        logger.info("Vega Autonomous Task Scheduler worker started.")

    async def stop(self) -> None:
        """Stop the background scheduling worker loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Vega Autonomous Task Scheduler worker stopped.")

    def run_once(self, as_of: datetime | None = None) -> list[dict[str, Any]]:
        """Synchronously execute all currently due scheduled tasks."""
        due_tasks = self.registry.claim_due_schedules(as_of=as_of)
        results = []
        for scheduled in due_tasks:
            result = self._execute_scheduled_task(scheduled)
            results.append(result)
        return results

    def _execute_scheduled_task(self, scheduled: ScheduledTask) -> dict[str, Any]:
        """Execute a single due scheduled task through the main agent graph."""
        now = datetime.now(UTC)
        try:
            execution_res = self.executor_callback(scheduled.company_id, scheduled.goal)

            if execution_res.get("status") == "waiting_approval" and execution_res.get("thread_id"):
                if not scheduled.preapproved or self.approval_callback is None:
                    self.registry.update_schedule_status(
                        scheduled.schedule_id,
                        status="waiting_approval",
                        last_run_at=now,
                    )
                    return {
                        "schedule_id": str(scheduled.schedule_id),
                        "status": "waiting_approval",
                        "result": execution_res,
                    }
                execution_res = self.approval_callback(
                    scheduled.company_id,
                    str(execution_res["thread_id"]),
                    True,
                )

            task_obj = execution_res.get("task")
            task_id = (
                UUID(str(task_obj.get("task_id")))
                if isinstance(task_obj, dict) and task_obj.get("task_id")
                else None
            )
            final_status = str(execution_res.get("status", "failed"))
            schedule_status = "completed" if final_status == "completed" else "failed"

            self.registry.update_schedule_status(
                scheduled.schedule_id,
                status=schedule_status,
                result_task_id=task_id,
                last_run_at=now,
            )
            return {
                "schedule_id": str(scheduled.schedule_id),
                "status": schedule_status,
                "result": execution_res,
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("Scheduled task %s failed to execute: %s", scheduled.schedule_id, exc)
            self.registry.update_schedule_status(
                scheduled.schedule_id, status="failed", last_run_at=now
            )
            return {
                "schedule_id": str(scheduled.schedule_id),
                "status": "failed",
                "error": str(exc),
            }

    async def _worker_loop(self) -> None:
        """Internal asynchronous poll loop."""
        while self._running:
            try:
                due_tasks = self.registry.claim_due_schedules()
                for scheduled in due_tasks:
                    self._execute_scheduled_task(scheduled)
            except Exception as exc:  # noqa: BLE001
                logger.error("Error in Vega Scheduler worker loop: %s", exc)
            await asyncio.sleep(self.poll_interval_seconds)

