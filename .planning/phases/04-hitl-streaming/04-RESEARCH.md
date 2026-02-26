# Phase 4: Human-in-the-Loop & Streaming — Research

**Phase:** 4 — Human-in-the-Loop & Streaming
**Researched:** 2026-02-26
**Goal:** Implement approval gates (HITL), real-time progress updates to Jira, and a feedback loop for rejected tasks.

## RESEARCH COMPLETE

---

## 1. Real-time Streaming to Jira

- **Mechanism:** As agents progress through tasks, the Orchestrator emits events.
- **Implementation:** 
  - `CrewAI` provides `on_step_end` callbacks.
  - The orchestrator captures these events and uses the `Jira MCP` tool to post incremental comments.
- **Payload:** "Agent [X] started [Task Y]", "Agent [X] finished [Task Y] with result: [Z]".

## 2. Human-in-the-Loop (HITL)

- **Approval Trigger:** Before a "Critical Action" (e.g., Opening a PR, Merging code), the agent pauses.
- **Process:**
  1. Orchestrator writes `APPROVAL_NEEDED` status to DynamoDB.
  2. Orchestrator posts an "Approval Required" comment to Jira with a diff/summary.
  3. Worker (Agent run) waits for an external signal or polls DynamoDB for a status change.
- **Resuming:** Once a human replies to the Jira ticket (captured via Phase 1 webhook) or updates a status in a custom UI (deferred), the orchestrator updates DynamoDB to `APPROVED` or `REJECTED`.

## 3. Feedback Loop for Rejection

- If `REJECTED`, the Orchestrator agent receives the human feedback.
- A new task cycle is triggered where the `feedback` is passed as a mandatory input.
- The Coder agent adjusts the code based on the feedback.

## 4. Polling vs. WebSocket

- For MVP, **Jira polling/webhook** is sufficient.
- The agent thread can "sleep" for 30s intervals while checking DynamoDB for the approval bit.

---

*Phase: 04-hitl-streaming | Research: 2026-02-26*
