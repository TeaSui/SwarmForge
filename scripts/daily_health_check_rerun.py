from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import settings
from services.jira_client import JiraClient


def _sign_webhook(body: bytes) -> str:
    signature = hmac.new(
        settings.JIRA_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"


def _retrigger(issue: dict[str, Any], event_name: str) -> requests.Response:
    issue_fields = issue.get("fields", {})
    payload = {
        "webhookEvent": event_name,
        "issue": {
            "id": str(issue["id"]),
            "key": issue["key"],
            "fields": {
                "labels": issue_fields.get("labels", []),
                "summary": issue_fields.get("summary"),
            },
        },
        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
    }
    body = json.dumps(payload).encode()
    webhook_url = os.getenv("SWARMFORGE_JIRA_WEBHOOK_URL", "http://localhost:8000/webhook/jira")
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": _sign_webhook(body),
    }
    return requests.post(webhook_url, data=body, headers=headers, timeout=30)


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def run():
    project_key = os.getenv("DAILY_JIRA_PROJECT_KEY", "SCRUM")
    labels_csv = os.getenv("DAILY_CHAIN_LABELS", os.getenv("DAILY_CHAIN_LABEL", "health-check-app"))
    status_filter = os.getenv("DAILY_STATUS_FILTER", "To Do,In Progress,In Review")
    rerun_limit = int(os.getenv("DAILY_MAX_RERUNS", "20"))

    statuses = [s.strip() for s in status_filter.split(",") if s.strip()]
    labels = _parse_csv(labels_csv)
    status_clause = ",".join(f'"{s}"' for s in statuses)
    label_clause = ",".join(f'"{label}"' for label in labels)
    jql = (
        f'project = "{project_key}" '
        f'AND labels in ({label_clause}) '
        f'AND status in ({status_clause}) '
        "ORDER BY updated ASC"
    )

    client = JiraClient.from_settings()
    issues = client.search_issues(
        jql=jql,
        fields=["summary", "labels", "status", "updated"],
        max_results=200,
    )

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    retriggered = 0
    failed = 0

    print(f"[DAILY] Query returned={len(issues)} chain_labels={labels} limit={rerun_limit}")

    for issue in issues[:rerun_limit]:
        key = issue["key"]
        summary = issue.get("fields", {}).get("summary", "")
        status_name = issue.get("fields", {}).get("status", {}).get("name", "unknown")
        try:
            client.add_comment(
                key,
                (
                    "[SwarmForge Daily Rerun] Re-triggering health-check-app chain ticket "
                    f"(status={status_name}) for autonomous continuation."
                ),
            )
            event_name = f"jira:issue_daily_rerun:health-check-app:{run_id}"
            response = _retrigger(issue, event_name)
            if response.status_code != 200:
                failed += 1
                print(f"[DAILY][WARN] {key} retrigger failed: {response.status_code} {response.text}")
                continue

            retriggered += 1
            print(f"[DAILY][OK] {key} retriggered | {summary}")
        except Exception as exc:
            failed += 1
            print(f"[DAILY][ERROR] {key}: {exc}")

    print(f"[DAILY] Completed: retriggered={retriggered} failed={failed} limit={rerun_limit}")


if __name__ == "__main__":
    run()
