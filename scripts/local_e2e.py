#!/usr/bin/env python3
"""Local end-to-end test: bypasses SQS/DynamoDB, invokes orchestrator directly.

Usage:
    ./venv/bin/python scripts/local_e2e.py

Requires ANTHROPIC_API_KEY and GITHUB_TOKEN in .env.
Jira is mocked (expired subscription). DynamoDB is replaced with in-memory state.
CrewAI agents and GitHub delivery run for real.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

# Force local/test mode before any imports
os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("SWARMFORGE_PRIMARY_LLM", "anthropic")
os.environ["SWARMFORGE_MOCK_EXTERNAL"] = "true"
os.environ["CREWAI_TRACING_ENABLED"] = "false"
# Single CrewAI attempt to avoid slow retries
os.environ["SWARMFORGE_CREW_STAGE_ATTEMPTS"] = "1"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_settings

settings = get_settings()
if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == "sk-ant-...":
    print("ERROR: Set ANTHROPIC_API_KEY in .env first")
    sys.exit(1)
if not settings.GITHUB_TOKEN or settings.GITHUB_TOKEN in ("", "placeholder"):
    print("ERROR: Set GITHUB_TOKEN in .env first")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Stub StateManager to avoid DynamoDB
# ---------------------------------------------------------------------------
class LocalStateManager:
    """In-memory state manager replacing DynamoDB for local testing."""

    def __init__(self):
        self.states: dict[str, dict[str, Any]] = {}

    async def update_state(self, task_id: str, state: str, metadata: dict | None = None):
        metadata = metadata or {}
        self.states[task_id] = {
            "state": state,
            "updated_at": datetime.now(UTC).isoformat(),
            "metadata": metadata,
        }
        stage = metadata.get("stage", metadata.get("sub_state", ""))
        logging.info("  STATE  %s -> %s %s", task_id, state, f"({stage})" if stage else "")


# ---------------------------------------------------------------------------
# Build a patched orchestrator
# ---------------------------------------------------------------------------
def build_local_orchestrator():
    from services.orchestrator import Orchestrator

    orch = Orchestrator()

    # Replace DynamoDB state manager with local in-memory version
    orch.state_manager = LocalStateManager()

    # Replace approval gate to auto-approve
    orch.approval_gate = MagicMock()
    orch.approval_gate.request_approval = AsyncMock(return_value="approved")

    # Everything else is real: CrewAI agents, GitHub delivery, LLM stages
    logging.info("GitHub delivery: REAL (repo=%s)", settings.SWARMFORGE_TARGET_REPO)

    return orch


# ---------------------------------------------------------------------------
# Sample task envelopes
# ---------------------------------------------------------------------------
JIRA_ENVELOPE = {
    "task_id": "LOCAL-E2E-001",
    "source": "jira",
    "event_type": "jira:issue_updated",
    "payload": {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "id": "10042",
            "key": "LOCAL-1",
            "fields": {
                "summary": "Add a health check endpoint that returns system uptime and version",
                "labels": ["ai-task"],
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "Create a /health endpoint that returns JSON with: "
                                        "status (ok/degraded), version from config, uptime in seconds, "
                                        "and current timestamp. Include a basic unit test."
                                    ),
                                }
                            ],
                        }
                    ],
                },
            },
        },
    },
    "timestamp": datetime.now(UTC).isoformat(),
    "metadata": {"correlation_id": "local-e2e-test"},
}


async def run_e2e():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    print("=" * 60)
    print("SwarmForge Local E2E Test")
    print("=" * 60)
    print(f"Model:     {settings.SWARMFORGE_ANTHROPIC_MODEL_ID}")
    print(f"Task:      {JIRA_ENVELOPE['task_id']}")
    print(f"Summary:   {JIRA_ENVELOPE['payload']['issue']['fields']['summary']}")
    print("=" * 60)

    orch = build_local_orchestrator()

    try:
        await orch.handle_task(JIRA_ENVELOPE)
    except Exception as exc:
        logging.exception("E2E test failed: %s", exc)
        return False

    # Print results
    states = orch.state_manager.states
    task_state = states.get(JIRA_ENVELOPE["task_id"], {})
    final_state = task_state.get("state", "UNKNOWN")
    metadata = task_state.get("metadata", {})

    print("\n" + "=" * 60)
    print(f"RESULT: {final_state}")
    if final_state == "COMPLETED":
        print(f"  Tokens: {metadata.get('tokens', '?')}")
        print(f"  Cost:   ${metadata.get('usd', '?')}")
        pr_url = metadata.get("quality_report", {}).get("pr_url")
        if pr_url:
            print(f"  PR:     {pr_url}")
        print("\nSUCCESS — Full pipeline completed.")
    elif final_state == "FAILED":
        print(f"  Reason: {metadata.get('sub_state', 'unknown')}")
        print(f"  Error:  {metadata.get('error', metadata.get('failed_checks', ''))}")
    else:
        print(f"  Last metadata: {json.dumps(metadata, indent=2, default=str)[:500]}")
    print("=" * 60)

    return final_state == "COMPLETED"


if __name__ == "__main__":
    success = asyncio.run(run_e2e())
    sys.exit(0 if success else 1)
