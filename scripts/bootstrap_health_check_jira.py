from __future__ import annotations

import argparse
from datetime import datetime, timezone

from services.jira_client import JiraClient, JiraClientError


DEFAULT_BOARD_ID = 1
DEFAULT_PROJECT_KEY = "SCRUM"
DEFAULT_EPIC_SUMMARY = "Health Check App (Production) via SwarmForge"


def _find_epic_link_field_id(client: JiraClient) -> str | None:
    try:
        fields = client.get_fields()
    except JiraClientError:
        return None

    candidates = {"Epic Link", "Parent Link"}
    for field in fields:
        name = field.get("name", "")
        if name in candidates:
            return field.get("id")
    return None


def _create_issue(
    client: JiraClient,
    project_key: str,
    issue_type: str,
    summary: str,
    description: str,
    labels: list[str],
    epic_link_field_id: str | None,
    epic_key: str | None,
) -> str:
    fields: dict[str, object] = {
        "project": {"key": project_key},
        "issuetype": {"name": issue_type},
        "summary": summary,
        "labels": labels,
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description}],
                }
            ],
        },
    }

    if epic_key and epic_link_field_id:
        fields[epic_link_field_id] = epic_key

    created = client.create_issue({"fields": fields})
    return created["key"]


def bootstrap_health_check_chain(
    board_id: int,
    project_key: str,
    epic_summary: str,
) -> list[str]:
    client = JiraClient.from_settings()
    epic_link_field_id = _find_epic_link_field_id(client)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    base_labels = ["ai-task", "swarmforge", "health-check-app", "production"]

    existing_epics = client.search_issues(
        jql=(
            f'project = {project_key} AND issuetype = Epic AND summary ~ "\\"{epic_summary}\\"" '
            "AND statusCategory != Done ORDER BY created DESC"
        ),
        fields=["summary"],
        max_results=1,
    )
    if existing_epics:
        epic_key = existing_epics[0]["key"]
    else:
        epic_key = _create_issue(
            client=client,
            project_key=project_key,
            issue_type="Epic",
            summary=epic_summary,
            description=(
                "Goal: ship a production-grade health risk check app using SwarmForge autonomous workflow. "
                "Scope includes Flutter frontend, backend API, security, observability, CI/CD, and end-to-end validation."
            ),
            labels=base_labels,
            epic_link_field_id=None,
            epic_key=None,
        )

    backlog = [
        ("Architecture & Product Spec", "Define architecture, domain model, NFRs, API contract, and release criteria."),
        ("Flutter App Shell & Navigation", "Set up production Flutter app structure, routing, environment config, and base theme."),
        ("Risk Scoring Engine", "Implement deterministic health risk scoring and thresholds with unit tests."),
        ("Bedrock Explanation Service", "Integrate Bedrock to generate user-friendly explanation from scoring output with guardrails."),
        ("Backend API & Validation", "Implement FastAPI endpoints, request validation, error handling, and OpenAPI docs."),
        ("Persistence & Audit Trail", "Store assessments, request logs, and audit metadata for traceability."),
        ("Security Hardening", "Apply secrets management, auth strategy, PII minimization, and dependency/security scanning."),
        ("Observability & SLO", "Set up CloudWatch logs/metrics/alarms and define SLO dashboards."),
        ("CI/CD Pipeline", "Create automated lint, unit/integration tests, build/release pipeline, and environment promotion gates."),
        ("Automation Test Suite", "Add API and UI automation tests, smoke tests, and regression suite."),
        ("Load/Resilience Validation", "Run concurrency and failure-injection tests with remediation checklist."),
        ("UAT & Production Readiness", "Execute UAT, DR checklist, rollback plan, and launch sign-off."),
    ]

    created_keys = [epic_key]
    for idx, (title, desc) in enumerate(backlog, start=1):
        story_summary = f"HC-{idx:02d} {title}"
        exists = client.search_issues(
            jql=(
                f'project = {project_key} AND summary ~ "\\"{story_summary}\\"" '
                "AND statusCategory != Done ORDER BY created DESC"
            ),
            fields=["summary"],
            max_results=1,
        )
        if exists:
            created_keys.append(exists[0]["key"])
            continue

        key = _create_issue(
            client=client,
            project_key=project_key,
            issue_type="Story",
            summary=story_summary,
            description=f"{desc} (Created {timestamp})",
            labels=base_labels,
            epic_link_field_id=epic_link_field_id,
            epic_key=epic_key,
        )
        created_keys.append(key)

    sprints = client.get_active_sprints(board_id)
    if sprints:
        sprint_id = sprints[0]["id"]
        # Avoid adding epic (many Jira boards hide Epic in sprint board columns)
        client.add_issues_to_sprint(sprint_id, created_keys[1:])

    client.add_comment(
        epic_key,
        "[SwarmForge] Ticket chain bootstrap completed. All delivery stories created and added to active sprint.",
    )

    return created_keys


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Jira ticket-chain for Health Check app delivery")
    parser.add_argument("--board-id", type=int, default=DEFAULT_BOARD_ID)
    parser.add_argument("--project-key", default=DEFAULT_PROJECT_KEY)
    parser.add_argument("--epic-summary", default=DEFAULT_EPIC_SUMMARY)
    args = parser.parse_args()

    keys = bootstrap_health_check_chain(
        board_id=args.board_id,
        project_key=args.project_key,
        epic_summary=args.epic_summary,
    )
    print("Created issues:")
    for key in keys:
        print(f"- {key}")


if __name__ == "__main__":
    main()
