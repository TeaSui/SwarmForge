from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone

import requests

from config import settings
from services.jira_client import JiraClient


def _signature(body: bytes) -> str:
    digest = hmac.new(settings.JIRA_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def trigger_health_check_chain(limit: int, webhook_url: str, chain_labels: list[str]) -> list[str]:
    client = JiraClient.from_settings()
    label_clause = ",".join(f'"{label}"' for label in chain_labels)
    jql = (
        f'project = SCRUM AND labels in ({label_clause}) '
        'AND statusCategory != Done ORDER BY created ASC'
    )
    issues = client.search_issues(jql=jql, fields=["summary", "labels"], max_results=200)

    triggered: list[str] = []
    for issue in issues[:limit]:
        fields = issue.get("fields", {})
        payload = {
            "webhookEvent": f"jira:issue_updated:health-check-chain:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "issue": {
                "id": str(issue["id"]),
                "key": issue["key"],
                "fields": {
                    "labels": fields.get("labels", []),
                    "summary": fields.get("summary", ""),
                },
            },
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        }
        body = json.dumps(payload).encode()
        headers = {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": _signature(body),
        }
        response = requests.post(webhook_url, data=body, headers=headers, timeout=20)
        response.raise_for_status()
        triggered.append(issue["key"])

    return triggered


def main():
    parser = argparse.ArgumentParser(description="Trigger SwarmForge execution for health-check ticket chain")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument(
        "--chain-labels",
        default=os.getenv("CHAIN_LABELS", "health-check-app"),
    )
    parser.add_argument(
        "--webhook-url",
        default=os.getenv("SWARMFORGE_JIRA_WEBHOOK_URL", "http://localhost:8000/webhook/jira"),
    )
    args = parser.parse_args()

    keys = trigger_health_check_chain(
        limit=args.limit,
        webhook_url=args.webhook_url,
        chain_labels=_parse_csv(args.chain_labels),
    )
    print("Triggered issues:")
    for key in keys:
        print(f"- {key}")


if __name__ == "__main__":
    main()
