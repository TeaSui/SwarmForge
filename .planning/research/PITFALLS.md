# Pitfalls Research

**Domain:** Autonomous AI software engineering swarm (Jira-to-PR workflow)
**Researched:** 2026-02-26
**Confidence:** MEDIUM

## Critical Pitfalls

### Pitfall 1: Unbounded agent execution

**What goes wrong:**
Tasks run too long, consume excessive tokens, or loop without progress.

**Why it happens:**
No enforced budget/time ceilings and no termination criteria.

**How to avoid:**
Implement per-task token and time budgets with explicit kill switch states.

**Warning signs:**
Growing token spend, repeated tool calls, stagnant task state.

**Phase to address:**
Phase 2 (Orchestration & LLM)

---

### Pitfall 2: Non-idempotent trigger handling

**What goes wrong:**
Duplicate Jira/Slack events generate duplicate tasks and conflicting PRs.

**Why it happens:**
Trigger payloads are processed without dedupe keys.

**How to avoid:**
Use deterministic idempotency keys and short-lived dedupe store checks.

**Warning signs:**
Multiple tasks for one ticket update, duplicate comments/branches.

**Phase to address:**
Phase 1 (Ingress & Queue)

---

### Pitfall 3: Tool actions without governance gates

**What goes wrong:**
Agents open PRs or mutate repositories without explicit human approval.

**Why it happens:**
Autonomy prioritized over policy in early implementation.

**How to avoid:**
Define mandatory approval checkpoints before high-impact actions.

**Warning signs:**
Unexpected PR creation or branch changes in sensitive repositories.

**Phase to address:**
Phase 4 (Human-in-the-Loop & Streaming)

---

### Pitfall 4: Weak observability of multi-agent decisions

**What goes wrong:**
Failures cannot be diagnosed quickly; teams lose trust in automation.

**Why it happens:**
Logs are unstructured and agent/tool chains are not traced end-to-end.

**How to avoid:**
Emit structured events, per-task correlation IDs, and full trace pipelines.

**Warning signs:**
"Unknown failure" incidents and high MTTR for ticket triage.

**Phase to address:**
Phase 5 (Deployment & Observability)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded provider fallback logic | Faster initial coding | Hard to evolve policies and monitor behavior | MVP only, then refactor |
| Direct tool calls from agents | Fewer abstraction layers | Weak policy enforcement and poor testability | Rarely acceptable |
| Minimal state transitions | Simpler early flow | Retry/resume logic becomes brittle | Only in very early prototypes |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Jira webhooks | Trusting all payloads blindly | Validate schema and signature, normalize fields |
| GitHub API | Missing branch protection assumptions | Enforce repo policy checks before write actions |
| Bedrock fallback | Switching provider without prompt parity checks | Keep provider-normalized prompt contract tests |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Single-worker queue consumer | Queue lag spikes | Horizontal worker scaling and backpressure | Moderate concurrent load |
| Large prompt context accumulation | Latency and cost drift | Prompt budgeting and context pruning | Long-running tasks |
| Tool call chatter | Slow end-to-end cycle | Batch/compose tool operations where safe | Multi-agent complex tickets |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing API keys in repo/env files | Secret exposure | Secrets Manager + least-privilege IAM |
| Over-broad tool permissions | Unintended repo/data mutation | Role-scoped policies and explicit allowlists |
| Missing audit trail for approvals | Compliance and accountability gaps | Persist approval actor, time, and decision evidence |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Sparse progress updates | Users think task is stalled | Stream milestone-level updates with ETA hints |
| Non-actionable failure messages | Teams cannot recover quickly | Provide root cause and next action in ticket comments |
| Excessive approval prompts | Approval fatigue | Gate only high-impact actions |

## "Looks Done But Isn't" Checklist

- [ ] **Trigger pipeline:** verify dedupe under retry and replay scenarios.
- [ ] **Agent outputs:** verify reproducible branch/commit behavior.
- [ ] **Approval flow:** verify reject-and-rework path, not just approve path.
- [ ] **Observability:** verify one task can be traced across all components.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Unbounded execution | MEDIUM | Kill task, persist failure reason, tune budget policy |
| Duplicate processing | MEDIUM | Reconcile duplicate tasks, add stronger idempotency keying |
| Unsafe autonomous actions | HIGH | Freeze write actions, introduce mandatory gates, audit incident |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Unbounded execution | Phase 2 | Budget breach triggers task termination and audit log |
| Duplicate processing | Phase 1 | Replay test shows no duplicate task execution |
| Unsafe autonomous actions | Phase 4 | PR creation blocked until explicit human approval |
| Weak observability | Phase 5 | Single correlation ID trace spans ingress to completion |

## Sources

- `/Users/tungnguyen/TYME/SwarmForge/README.md`
- Existing `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md`
- Prior integration/debug context in current project notes

---
*Pitfalls research for: Autonomous AI engineering swarm*
*Researched: 2026-02-26*
