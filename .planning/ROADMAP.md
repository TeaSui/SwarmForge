# Roadmap: SwarmForge

## Overview

SwarmForge builds from a minimal trigger-ingress layer through a fully autonomous agent swarm capable of completing a Jira ticket end-to-end. Each phase ships a working, testable layer: ingress first, then orchestration, then agents, then approval flow, then production-ready deployment with observability.

## Phases

- [ ] **Phase 1: Ingress & Queue** — FastAPI webhook receiver + SQS task queue
- [ ] **Phase 2: Orchestration & LLM** — CrewAI setup, intent parsing, LLM with Bedrock fallback
- [ ] **Phase 3: Agent Pool & MCP Tools** — all 6 agents + GitHub/Jira/Shell MCP integrations
- [ ] **Phase 4: Human-in-the-Loop & Streaming** — approval gates + real-time progress to Jira/Slack
- [ ] **Phase 5: Deployment & Observability** — ECS Fargate CDK stack + LangSmith + CloudWatch
- [ ] **Phase 6: End-to-End Validation** — full Jira→code→PR flow, load testing, hardening

## Phase Details

### Phase 1: Ingress & Queue
**Goal**: Accept triggers from Jira, Slack, and generic webhooks; buffer them via SQS; deduplicate.
**Depends on**: Nothing (first phase)
**Requirements**: TRG-01, TRG-02, TRG-03, TRG-04, TRG-05, TRG-06
**Success Criteria** (what must be TRUE):
  1. Jira webhook with AI label triggers task creation and is acknowledged within 200ms
  2. Task payload is placed on SQS queue and visible in AWS console
  3. Duplicate events are silently deduplicated (idempotent processing)
  4. FastAPI service starts, handles `/health` endpoint, returns 200

**Plans**: 3 plans

Plans:
- [ ] 01-01: FastAPI service skeleton — `/webhook/jira`, `/webhook/slack`, `/webhook/generic`, `/health`
- [ ] 01-02: SQS producer — serialize trigger payload, publish to queue, DLQ config
- [ ] 01-03: Deduplication — idempotency key (Jira issue ID + event type), Redis or DynamoDB lock

---

### Phase 2: Orchestration & LLM
**Goal**: Parse task intent from SQS messages, route to correct agent crew, manage task lifecycle with DynamoDB state, enforce token budgets.
**Depends on**: Phase 1
**Requirements**: ORC-01, ORC-02, ORC-03, ORC-04, ORC-05, ORC-06, LLM-01, LLM-02, LLM-03, LLM-04
**Success Criteria** (what must be TRUE):
  1. SQS consumer picks up task and CrewAI crew is assembled for it
  2. Task state (PENDING → IN_PROGRESS → COMPLETE) persists in DynamoDB
  3. LLM calls fail over from Claude API to Bedrock on simulated error
  4. Task exceeding token budget is killed and error state written to DynamoDB
  5. Prompt caching reduces repeated tokens on sequential agent calls

**Plans**: 4 plans

Plans:
- [ ] 02-01: SQS consumer — poll queue, deserialize payload, dispatch to orchestrator
- [ ] 02-02: CrewAI orchestrator — intent parsing, crew assembly, task lifecycle management
- [ ] 02-03: LLM layer — Claude API client, Bedrock fallback, auto-failover logic, prompt caching
- [ ] 02-04: Token Budget Manager — per-task token limit, usage tracking, kill switch

---

### Phase 3: Agent Pool & MCP Tools
**Goal**: Implement all 6 specialized agents (Coder, Reviewer, Tester, Security, Doc, Orchestrator) connected to GitHub, Jira, and Shell MCP servers; agents share EFS workspace.
**Depends on**: Phase 2
**Requirements**: AGT-01, AGT-02, AGT-03, AGT-04, AGT-05, AGT-06, AGT-07, MCP-01, MCP-02, MCP-03, MCP-04
**Success Criteria** (what must be TRUE):
  1. Coder Agent writes a file to EFS workspace and commits it via GitHub MCP
  2. Reviewer Agent reads a git diff and returns structured review feedback
  3. Tester Agent writes and runs a pytest test file, returns pass/fail result
  4. Security Agent scans a sample vulnerable code file and flags issues
  5. Jira MCP posts a comment to a real Jira ticket
  6. Shell tool executes `pytest` in EFS workspace and captures output

**Plans**: 4 plans

Plans:
- [ ] 03-01: GitHub + Jira MCP server connections — auth, tool registration, smoke tests
- [ ] 03-02: Coder + Reviewer agents — system prompts, tool binding, EFS workspace access
- [ ] 03-03: Tester + Security + Doc agents — system prompts, shell tool, output parsing
- [ ] 03-04: Orchestrator agent + crew wiring — agent delegation, result aggregation, crew flow

---

### Phase 4: Human-in-the-Loop & Streaming
**Goal**: Pause agent flow before PR creation to request human approval via Jira/Slack; stream real-time progress updates; handle approval/rejection.
**Depends on**: Phase 3
**Requirements**: HITL-01, HITL-02, HITL-03, HITL-04, OUT-01, OUT-02, OUT-03
**Success Criteria** (what must be TRUE):
  1. Before PR is opened, Jira ticket receives a comment asking for approval
  2. Human approves via Jira comment reply and agent resumes, opens PR
  3. Human rejects with feedback; agent adjusts and re-requests approval
  4. During agent run, Jira ticket shows incremental progress comments
  5. Final PR link posted to Jira ticket on completion

**Plans**: 3 plans

Plans:
- [ ] 04-01: Streaming output — agent progress events written to Jira as incremental comments
- [ ] 04-02: HITL approval gate — pause point, Jira/Slack approval request, polling for response
- [ ] 04-03: Feedback loop — rejection handling, re-queue with feedback context, max retry limit

---

### Phase 5: Deployment & Observability
**Goal**: Full production deployment via CDK (ECS Fargate, EFS, SQS, DynamoDB, Secrets Manager); LangSmith tracing; CloudWatch metrics/alerts; Docker image to ECR.
**Depends on**: Phase 4
**Requirements**: INF-01, INF-02, INF-03, INF-04, INF-05, OBS-01, OBS-02, OBS-03
**Success Criteria** (what must be TRUE):
  1. `cdk deploy` completes with all resources created
  2. ECS Fargate service starts and passes health check
  3. LangSmith shows agent traces for a real task run
  4. CloudWatch dashboard shows task success rate, duration, token spend
  5. All secrets accessed from Secrets Manager (no plaintext API keys anywhere)

**Plans**: 3 plans

Plans:
- [ ] 05-01: CDK stack — ECS Fargate service, EFS, SQS+DLQ, DynamoDB, Secrets Manager, ECR
- [ ] 05-02: Docker image — Dockerfile, ECR push, ECS task definition, EFS mount
- [ ] 05-03: Observability — LangSmith tracing integration, CloudWatch dashboard + alarms

---

### Phase 6: End-to-End Validation
**Goal**: Run a real Jira ticket through the full autonomous cycle (write → review → test → PR). Fix integration issues, load test SQS consumer, harden error handling.
**Depends on**: Phase 5
**Requirements**: All v1 requirements
**Success Criteria** (what must be TRUE):
  1. A real Jira ticket labeled `ai-task` triggers the full autonomous flow
  2. A PR is opened on the target GitHub repo with working code
  3. Jira ticket shows complete progress trail in comments
  4. System handles 10 concurrent tasks without degradation
  5. All errors produce actionable messages in Jira, no silent failures

**Plans**: 2 plans

Plans:
- [ ] 06-01: End-to-end integration test — real Jira→SQS→CrewAI→GitHub→Jira flow
- [ ] 06-02: Load test + hardening — concurrent task stress test, error injection, edge cases

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Ingress & Queue | 0/3 | Not started | - |
| 2. Orchestration & LLM | 0/4 | Not started | - |
| 3. Agent Pool & MCP Tools | 0/4 | Not started | - |
| 4. Human-in-the-Loop & Streaming | 0/3 | Not started | - |
| 5. Deployment & Observability | 0/3 | Not started | - |
| 6. End-to-End Validation | 0/2 | Not started | - |
