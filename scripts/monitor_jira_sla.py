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
from services.sla_monitor import build_sla_jql, get_stale_issues


def _jira_auth() -> tuple[str, str]:
    return (settings.JIRA_EMAIL, settings.JIRA_API_TOKEN)


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _jira_search(jql: str, max_results: int) -> list[dict[str, Any]]:
    url = f"{settings.JIRA_BASE_URL}/rest/api/3/search/jql"
    params = {
        "jql": jql,
        "maxResults": max_results,
        "fields": "summary,status,labels,updated",
    }
    response = requests.get(url, params=params, auth=_jira_auth(), timeout=30)
    response.raise_for_status()
    return response.json().get("issues", [])


def _jira_comment(issue_key: str, text: str):
    url = f"{settings.JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/comment"
    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": text}],
                }
            ],
        }
    }
    response = requests.post(url, auth=_jira_auth(), json=payload, timeout=30)
    response.raise_for_status()


def _sign_webhook(body: bytes) -> str:
    signature = hmac.new(
        settings.JIRA_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"


def _retrigger_swarmforge(issue: dict[str, Any], event_name: str) -> requests.Response:
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


def run():
    project_key = os.getenv("SLA_JIRA_PROJECT_KEY", "SCRUM")
    statuses = os.getenv("SLA_JIRA_STATUSES", "To Do,In Progress").split(",")
    sprint_id = os.getenv("SLA_JIRA_SPRINT_ID")
    chain_labels_csv = os.getenv("SLA_CHAIN_LABELS", os.getenv("SLA_CHAIN_LABEL", "")).strip()
    threshold_hours = int(os.getenv("SLA_THRESHOLD_HOURS", "6"))
    max_issues = int(os.getenv("SLA_MAX_ISSUES", "100"))
    retrigger_limit = int(os.getenv("SLA_MAX_RETRIGGERS_PER_RUN", "20"))
    labels = _parse_csv(chain_labels_csv) if chain_labels_csv else list(settings.ai_labels_set)

    jql = build_sla_jql(
        project_key=project_key,
        statuses=statuses,
        labels=labels,
        sprint_id=sprint_id,
    )
    issues = _jira_search(jql=jql, max_results=max_issues)
    stale_issues = get_stale_issues(issues, threshold_hours=threshold_hours)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    retriggered = 0
    failed = 0

    print(f"[SLA] Query returned={len(issues)} stale={len(stale_issues)} threshold_hours={threshold_hours}")
    for issue in stale_issues[:retrigger_limit]:
        key = issue["key"]
        updated = issue.get("fields", {}).get("updated", "unknown")
        status_name = issue.get("fields", {}).get("status", {}).get("name", "unknown")
        text = (
            f"[SwarmForge SLA Monitor] Ticket is stale for >= {threshold_hours}h "
            f"(status={status_name}, updated={updated}). Retriggering automation now."
        )
        try:
            _jira_comment(key, text)
            event_name = f"jira:issue_stalled:{run_id}"
            retrigger_response = _retrigger_swarmforge(issue, event_name)
            if retrigger_response.status_code != 200:
                failed += 1
                print(
                    f"[SLA][WARN] Retrigger failed for {key}: "
                    f"{retrigger_response.status_code} {retrigger_response.text}"
                )
                continue

            retriggered += 1
            print(f"[SLA][OK] {key} retriggered")
        except Exception as exc:
            failed += 1
            print(f"[SLA][ERROR] {key}: {exc}")

    print(
        f"[SLA] Completed: retriggered={retriggered} failed={failed} "
        f"limit={retrigger_limit}"
    )


if __name__ == "__main__":
    run()
