from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable


def parse_jira_datetime(value: str) -> datetime:
    """
    Parse Jira datetime string with or without millisecond precision.
    """
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        pass

    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported Jira datetime format: {raw}")


def build_sla_jql(
    project_key: str,
    statuses: Iterable[str],
    labels: Iterable[str],
    sprint_id: str | None = None,
) -> str:
    status_clause = ",".join(f'"{s.strip()}"' for s in statuses if s.strip())
    label_clause = ",".join(f'"{l.strip()}"' for l in labels if l.strip())

    parts = [
        f'project = "{project_key}"',
        f"status in ({status_clause})" if status_clause else "",
        f"labels in ({label_clause})" if label_clause else "",
    ]

    if sprint_id:
        parts.append(f"sprint = {sprint_id}")

    where_clause = " AND ".join(p for p in parts if p)
    return f"{where_clause} ORDER BY updated ASC"


def get_stale_issues(
    issues: list[dict],
    threshold_hours: int,
    now: datetime | None = None,
) -> list[dict]:
    if now is None:
        now = datetime.now(timezone.utc)

    stale: list[dict] = []
    for issue in issues:
        fields = issue.get("fields", {})
        updated_str = fields.get("updated")
        if not updated_str:
            continue

        updated_at = parse_jira_datetime(updated_str).astimezone(timezone.utc)
        age_hours = (now - updated_at).total_seconds() / 3600.0
        if age_hours >= threshold_hours:
            stale.append(issue)

    return stale
