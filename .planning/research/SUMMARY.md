# Project Research Summary

**Project:** SwarmForge
**Domain:** Autonomous AI software engineering swarm (Jira-to-PR)
**Researched:** 2026-02-26
**Confidence:** MEDIUM

## Executive Summary

SwarmForge matches a high-leverage automation pattern: event-driven task ingestion, queue-backed orchestration, specialized agents, and policy-gated execution. The strongest v1 approach is to optimize the Jira ticket to PR loop with explicit reliability and governance controls before expanding scope.

Research indicates that success depends less on adding more agents and more on robust orchestration primitives: idempotent triggers, explicit task state, budget-aware execution, and traceable approvals. These create predictable behavior and operational trust.

Primary risks are runaway autonomy, duplicate task handling, and poor observability across distributed components. The roadmap should sequence controls early so scale and reliability can grow without architectural rewrites.

## Key Findings

### Recommended Stack

Use Python 3.11+, FastAPI, CrewAI, ECS Fargate, SQS + DLQ, DynamoDB, EFS, and a dual-provider model strategy (Claude primary, Bedrock fallback). This stack aligns with long-running asynchronous execution and enterprise reliability constraints.

**Core technologies:**
- Python/FastAPI: ingress and orchestration services
- CrewAI: role-based multi-agent coordination
- AWS ECS/SQS/DynamoDB/EFS: resilient execution, queueing, state, and workspace persistence
- Claude + Bedrock: quality + failover reliability

### Expected Features

**Must have (table stakes):**
- Multi-channel trigger ingestion and deduplication
- Agent pipeline for code/review/test/PR tasks
- Human approval before high-impact actions
- End-to-end observability and actionable outputs

**Should have (competitive):**
- Dynamic crew composition by task intent
- Budget-aware autonomy controls
- Seamless human feedback loops from Jira/Slack

**Defer (v2+):**
- Multi-tenant architecture
- Durable workflow engine integration
- Rich UI dashboard and sidecar execution matrix

### Architecture Approach

Adopt an event-driven layered architecture: trigger ingestion -> queue/state -> orchestrator/policies -> agent/tool execution -> output/observability. Keep boundaries explicit so each layer can be tested and scaled independently.

**Major components:**
1. Ingress and queueing layer for normalized, idempotent task intake
2. Orchestration and budget policy layer for safe autonomous execution
3. Agent and tool integration layer for code actions and external system updates

### Critical Pitfalls

1. **Unbounded agent execution**: enforce budget/time kill switches.
2. **Duplicate trigger processing**: implement deterministic idempotency keys.
3. **Autonomous actions without governance**: require explicit approval gates.
4. **Weak observability**: use correlation IDs with structured traces and metrics.

## Implications for Roadmap

### Phase 1: Ingress & Queue
**Rationale:** Reliable intake is foundational for everything else.
**Delivers:** Trigger normalization, dedupe, and queue buffering.
**Addresses:** Table-stakes trigger capabilities.
**Avoids:** Duplicate execution pitfalls.

### Phase 2: Orchestration & LLM
**Rationale:** Safe, deterministic orchestration must precede full agent rollout.
**Delivers:** Task lifecycle state machine, budget manager, provider failover.
**Uses:** CrewAI plus provider-router stack.
**Implements:** Policy-gated autonomy pattern.

### Phase 3: Agent Pool & MCP Tools
**Rationale:** Specialized agents become useful only after stable orchestration.
**Delivers:** Multi-agent execution with GitHub/Jira/shell tools.

### Phase 4: Human-in-the-Loop & Streaming
**Rationale:** Operational trust requires control and transparency.
**Delivers:** Approval flow and progress streaming.

### Phase 5: Deployment & Observability
**Rationale:** Production readiness depends on repeatable infra and telemetry.
**Delivers:** ECS/CDK deployment, tracing, metrics, alerts.

### Phase 6: End-to-End Validation
**Rationale:** Confirm business value with full Jira-to-PR runs under load.
**Delivers:** Hardening, reliability validation, and launch confidence.

### Phase Ordering Rationale

- Sequence follows dependency chain from ingestion reliability to production hardening.
- Governance and observability are first-class phases, not afterthoughts.
- Ordering explicitly reduces high-cost failure modes identified in pitfalls research.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** Provider fallback semantics and budget policy tuning.
- **Phase 3:** MCP tool permissions and sandbox boundaries.
- **Phase 5:** ECS/EFS performance tuning under concurrent workloads.

Phases with standard patterns:
- **Phase 1:** Trigger ingestion and queue setup are well-established.
- **Phase 4:** Approval-gate workflows follow standard enterprise patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Aligned with existing project intent; versions still require phase-level validation |
| Features | MEDIUM | Strongly grounded in current requirements and roadmap |
| Architecture | MEDIUM | Pattern fit is strong; concrete sizing decisions deferred to implementation |
| Pitfalls | MEDIUM | Derived from common multi-agent production failure modes |

**Overall confidence:** MEDIUM

### Gaps to Address

- Validate exact library/model versions at each implementation phase.
- Validate concurrency and cost thresholds with real load tests.
- Validate provider fallback behavior with failure-injection tests.

## Sources

### Primary (HIGH confidence)
- `/Users/tungnguyen/TYME/SwarmForge/README.md` — project scope and architecture baseline
- Existing `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`

### Secondary (MEDIUM confidence)
- Internal initialization context from this GSD session

---
*Research completed: 2026-02-26*
*Ready for roadmap: yes*
