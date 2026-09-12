"""Natural Language Goal Decomposition & Autonomous Temporal Parser for Vega Business OS."""

import re
from datetime import UTC, datetime, timedelta
from typing import Any


def parse_temporal_intent(
    goal: str, base_time: datetime | None = None
) -> tuple[datetime | None, str, str | None, str | None]:
    """
    Extract scheduled future run time and cleaned goal from natural language.
    Returns (run_at_utc, immediate_goal, scheduled_goal, schedule_type).
    """
    now = base_time or datetime.now(UTC)
    lowered = goal.lower().strip()
    
    # Check for "tomorrow at <time>"
    match_tomorrow_time = re.search(r"tomorrow\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", lowered)
    if match_tomorrow_time:
        hour = int(match_tomorrow_time.group(1))
        minute = int(match_tomorrow_time.group(2) or 0)
        meridiem = match_tomorrow_time.group(3)
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        
        target = now + timedelta(days=1)
        run_at = target.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return run_at, goal, goal, "once"

    # Check for "tomorrow morning" / "tomorrow afternoon"
    if "tomorrow morning" in lowered:
        target = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        return target, goal, goal, "once"
    if "tomorrow afternoon" in lowered:
        target = (now + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
        return target, goal, goal, "once"

    # Check for "in X hours" or "in X minutes" or "in X days"
    match_in_hours = re.search(r"in\s+(\d+)\s*(?:hours|hour|hrs|hr)", lowered)
    if match_in_hours:
        hours = int(match_in_hours.group(1))
        target = now + timedelta(hours=hours)
        return target, goal, goal, "once"

    match_in_mins = re.search(r"in\s+(\d+)\s*(?:minutes|minute|mins|min)", lowered)
    if match_in_mins:
        mins = int(match_in_mins.group(1))
        target = now + timedelta(minutes=mins)
        return target, goal, goal, "once"

    match_in_days = re.search(r"in\s+(\d+)\s*(?:days|day)", lowered)
    if match_in_days:
        days = int(match_in_days.group(1))
        target = now + timedelta(days=days)
        return target, goal, goal, "once"

    # Check for recurring "every weekday at X" or "every day at X" or "daily at X"
    if "every weekday" in lowered or "every day" in lowered or "daily" in lowered:
        target = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        return target, goal, goal, "recurring"

    return None, goal, None, None


def decompose_goal_into_milestones(goal: str) -> list[dict[str, Any]]:
    """
    Decompose a multi-part business goal into defined execution stages.
    """
    run_at, _, _, _ = parse_temporal_intent(goal)

    
    # Split by clauses (and, then, afterwards, schedule)
    parts = re.split(r",\s*and\s+|\s+and\s+then\s+|\s+afterwards\s+|,\s*", goal, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip()]
    
    if len(parts) <= 1:
        return [
            {
                "stage": 1,
                "description": goal,
                "execution_type": "scheduled" if run_at else "immediate",
                "run_at": run_at.isoformat() if run_at else None,
            }
        ]
    
    milestones = []
    for idx, part in enumerate(parts, 1):
        part_run_at, _, _, _ = parse_temporal_intent(part)
        milestones.append({
            "stage": idx,
            "description": part,
            "execution_type": "scheduled" if (part_run_at or (run_at and idx == len(parts))) else "immediate",
            "run_at": (part_run_at or run_at).isoformat() if (part_run_at or (run_at and idx == len(parts))) else None,
        })
    return milestones
