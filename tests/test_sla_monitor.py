from datetime import datetime, timezone

from services.sla_monitor import build_sla_jql, get_stale_issues, parse_jira_datetime


def test_parse_jira_datetime_z_suffix():
    value = "2026-02-26T10:15:30.000Z"
    parsed = parse_jira_datetime(value)
    assert parsed.tzinfo is not None
    assert parsed.astimezone(timezone.utc).hour == 10


def test_build_sla_jql_contains_core_clauses():
    jql = build_sla_jql(
        project_key="SCRUM",
        statuses=["To Do", "In Progress"],
        labels=["ai-task", "swarmforge"],
        sprint_id="35",
    )
    assert 'project = "SCRUM"' in jql
    assert 'status in ("To Do","In Progress")' in jql
    assert 'labels in ("ai-task","swarmforge")' in jql
    assert "sprint = 35" in jql
    assert jql.endswith("ORDER BY updated ASC")


def test_get_stale_issues_filters_by_threshold():
    now = datetime(2026, 2, 26, 18, 0, 0, tzinfo=timezone.utc)
    issues = [
        {
            "id": "1",
            "key": "SCRUM-1",
            "fields": {"updated": "2026-02-26T08:00:00.000+0000"},
        },
        {
            "id": "2",
            "key": "SCRUM-2",
            "fields": {"updated": "2026-02-26T16:30:00.000+0000"},
        },
        {
            "id": "3",
            "key": "SCRUM-3",
            "fields": {},
        },
    ]
    stale = get_stale_issues(issues, threshold_hours=6, now=now)
    assert [issue["key"] for issue in stale] == ["SCRUM-1"]
