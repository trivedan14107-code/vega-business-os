"""Normalize the supplied Business Second Brain dataset to platform v0.1."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

VALUE_ALIASES = {
    "meeting_management": "meeting",
    "sales_follow_up": "sales_followup",
    "inventory_management": "inventory",
    "procurement_agent": "procurement",
    "finance_collection_agent": "finance_collection",
    "sales_reporting_agent": "sales_reporting",
    "calendar.check_availability": "calendar.read",
    "calendar.read_availability": "calendar.read",
    "calendar.create_event": "calendar.create",
    "google_meet.create_meeting": "google_meet.create",
    "zoom.create_meeting": "zoom.create",
    "slack.send_message": "slack.send",
    "whatsapp.send_message": "whatsapp.send",
    "email.send": "gmail.send",
    "accounting.get_invoice": "invoice.read",
    "accounting.get_payment_status": "payment_status.read",
    "crm.get_lead": "crm.read",
    "crm.update_lead": "crm.update",
    "inventory.get_stock": "inventory.read",
    "support.get_ticket": "support_ticket.read",
    "support.update_ticket": "support_ticket.update",
}


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        normalized = {
            ("expected" if key == "expected_scorecard" else key): normalize(item)
            for key, item in value.items()
        }
        if "expected_message" in normalized:
            expected = {"message": normalized.pop("expected_message")}
            if "data_minimization" in normalized:
                expected["data_minimization"] = normalized.pop("data_minimization")
            normalized["expected"] = expected
        return normalized
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, str):
        return VALUE_ALIASES.get(value, value)
    return value


def validate(dataset: dict[str, Any]) -> None:
    families = dataset["families"]
    rows = [row for scenarios in families.values() for row in scenarios]
    ids = [row["scenario_id"] for row in rows]
    if len(ids) != len(set(ids)):
        duplicates = [item for item, count in Counter(ids).items() if count > 1]
        raise ValueError(f"Duplicate scenario IDs: {duplicates}")
    if not all(re.fullmatch(r"[A-Z]{3,4}-\d{3}", item) for item in ids):
        raise ValueError("One or more scenario IDs do not match the canonical pattern")
    if not all("expected" in row for row in rows):
        raise ValueError("Every scenario must contain one normalized expected object")
    if not all(row["split"] in {"train", "validation", "test"} for row in rows):
        raise ValueError("Invalid split label")
    if not all(
        row["difficulty"] in {"easy", "medium", "hard", "adversarial"}
        for row in rows
    ):
        raise ValueError("Invalid difficulty label")

    declared = dataset["dataset_statistics"]
    split_counts = dict(Counter(row["split"] for row in rows))
    if declared["families"] != len(families) or declared["examples"] != len(rows):
        raise ValueError("Declared family/example counts do not match the data")
    if declared["split_counts"] != split_counts:
        raise ValueError("Declared split counts do not match the data")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    dataset = normalize(json.loads(args.source.read_text(encoding="utf-8")))
    dataset["dataset_name"] = "Business Second Brain Evaluation Dataset"
    dataset["dataset_version"] = "1.1.0"
    dataset["purpose"] = (
        "Synthetic evaluation and regression data for safe Main Agent orchestration. "
        "It is not large enough for model training."
    )
    dataset["reference_time"] = "2026-09-11T00:00:00+05:30"
    dataset["compatibility"] = {
        "platform_version": "0.1",
        "canonical_roles": [
            "meeting",
            "communication",
            "finance_collection",
            "sales_followup",
            "customer_support",
            "inventory",
            "procurement",
            "sales_reporting",
        ],
        "normalization_note": (
            "Legacy role and tool aliases were converted to platform canonical names."
        ),
    }
    dataset["dataset_statistics"]["difficulty_counts"] = dict(
        Counter(
            row["difficulty"]
            for scenarios in dataset["families"].values()
            for row in scenarios
        )
    )
    validate(dataset)
    args.destination.write_text(
        json.dumps(dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
