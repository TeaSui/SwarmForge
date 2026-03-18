# Architecture Research

**Domain:** Autonomous AI software engineering swarm (Jira-to-PR workflow)
**Researched:** 2026-02-26
**Confidence:** MEDIUM

## Standard Architecture

### System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                      Trigger Layer                           │
├─────────────────────────────────────────────────────────────┤
│ Jira Webhook | Slack Command | Generic Webhook             │
└───────────────┬───────────────┬───────────────┬────────────┘
                │               │               │
┌───────────────┴─────────────────────────────────────────────┐
│                 Ingress + Queueing Layer                    │
├─────────────────────────────────────────────────────────────┤
│ FastAPI ingress -> validator -> dedupe -> SQS + DLQ        │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────┴─────────────────────────────────────────────┐
│                  Orchestration Layer                         │
├─────────────────────────────────────────────────────────────┤
│ SQS consumer -> CrewAI orchestrator -> budget manager       │
│                         -> provider router (Claude/Bedrock) │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────┴─────────────────────────────────────────────┐
│                    Agent Execution Layer                     │
├─────────────────────────────────────────────────────────────┤
│ Coder | Reviewer | Tester | Security | Docs | Orchestrator │
│ via MCP tools (GitHub/Jira/Shell/File/Exec) over EFS state │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────┴─────────────────────────────────────────────┐
│               Output + Observability Layer                   │
├─────────────────────────────────────────────────────────────┤
│ Jira/Slack updates | LangSmith traces | CloudWatch metrics  │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Ingress API | Accept, validate, and normalize triggers | FastAPI endpoints with strict schema validation |
| Queue/State | Buffer tasks and persist lifecycle state | SQS + DLQ and DynamoDB status records |
| Orchestrator | Build crews, sequence agents, enforce limits | CrewAI orchestrator service with policy hooks |
| Tool Layer | Expose GitHub/Jira/shell capabilities | MCP servers with auth and guardrails |
| Execution Workspace | Persist repo and artifacts | EFS mount shared by agent processes |
| Observability | Trace, metrics, and incident debugging | LangSmith + CloudWatch dashboards/alarms |

## Recommended Project Structure

```text
src/
  api/              # FastAPI routes and request models
  orchestrator/     # Crew assembly, lifecycle policies, budgets
  agents/           # Agent prompts, role config, execution wrappers
  tools/            # MCP adapters and tool policy enforcement
  infra/            # Runtime config and service wiring
  observability/    # Logging, tracing, metrics emitters
tests/
  unit/
  integration/
```

### Structure Rationale

- **Clear runtime boundaries:** ingress, orchestration, tools, and observability evolve independently.
- **Testability-first layout:** each layer has a direct test target (unit + integration).
- **Lower coupling:** agents consume tool interfaces, not raw infra clients.

## Architectural Patterns

### Pattern 1: Event-driven orchestration

**What:** Trigger events enqueue tasks, orchestrator consumes asynchronously.
**When to use:** Variable task duration and bursty trigger traffic.
**Trade-offs:** Better resilience, more operational components.

### Pattern 2: Policy-gated autonomy

**What:** Autonomous agent decisions constrained by explicit policies (budget, approval, allowed tools).
**When to use:** Production systems with governance requirements.
**Trade-offs:** Safer operations, but extra state transitions and user checkpoints.

### Pattern 3: Shared workspace with isolated execution intent

**What:** Agents share an EFS-backed workspace but act through scoped tool permissions.
**When to use:** Collaborative multi-agent coding workflows.
**Trade-offs:** Faster collaboration, requires careful locking and provenance.

## Data Flow

### Request Flow

```text
Trigger -> FastAPI -> Validation/Dedup -> SQS
SQS -> Orchestrator -> Agent Crew -> Tools
Tools -> Workspace/External APIs -> Results
Results -> Jira/Slack updates + traces + final status
```

### Key Data Flows

1. **Task lifecycle flow:** incoming trigger to persisted completion state.
2. **Agent artifact flow:** generated code/tests/docs in EFS with commit lineage.
3. **Governance flow:** approval request, human response, resume/rework logic.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-50 tasks/day | Single ECS service, moderate queue depth, basic alarms |
| 50-500 tasks/day | Increase ECS concurrency, stronger DLQ handling, better retry policies |
| 500+ tasks/day | Split orchestrator/worker services, tighter sharding and cost controls |

### Scaling Priorities

1. **First bottleneck:** orchestration throughput and queue lag.
2. **Second bottleneck:** tool-call latency and external API quotas.

## Anti-Patterns

### Anti-Pattern 1: Direct synchronous trigger-to-agent execution

**What people do:** Handle full task in webhook request path.
**Why it's wrong:** Timeouts and poor failure recovery.
**Do this instead:** Queue immediately, process asynchronously.

### Anti-Pattern 2: No explicit task state machine

**What people do:** Infer state from logs only.
**Why it's wrong:** Hard to resume/retry safely.
**Do this instead:** Persist explicit states and transitions in DynamoDB.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Jira | Webhook in + comment/status out | Use idempotency keys for repeated events |
| GitHub | MCP tools for branch/commit/PR | Keep human approval before PR action |
| Anthropic + Bedrock | Provider router with failover policy | Track provider usage and fallback rates |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| API -> Orchestrator | Queue events | Keeps ingress fast and reliable |
| Orchestrator -> Agents | Crew tasks + tool contracts | Avoid agent direct infra access |
| Orchestrator -> Observability | Structured events | Supports debugging and audits |

## Sources

- `/Users/tungnguyen/TYME/SwarmForge/README.md`
- Existing `.planning/ROADMAP.md` phase decomposition
- Existing `.planning/REQUIREMENTS.md` requirement clusters

---
*Architecture research for: Autonomous AI engineering swarm*
*Researched: 2026-02-26*
