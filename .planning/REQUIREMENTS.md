# Requirements: SwarmForge

**Defined:** 2026-02-26
**Core Value:** A Jira ticket triggers a full autonomous development cycle — write, review, test, and PR — with no human involvement until approval.

## v1 Requirements

Requirements for MVP release. Each maps to roadmap phases.

### Ingress & Trigger

- [ ] **TRG-01**: System receives Jira webhook events (issue created/updated with AI label)
- [ ] **TRG-02**: System receives Slack slash command triggers
- [ ] **TRG-03**: System receives generic HTTP webhook triggers
- [ ] **TRG-04**: FastAPI service validates and acknowledges triggers within 200ms
- [ ] **TRG-05**: SQS queue buffers incoming tasks with DLQ for failed tasks
- [ ] **TRG-06**: System deduplicates duplicate trigger events

### Orchestration

- [ ] **ORC-01**: CrewAI orchestrator parses task intent from trigger payload
- [ ] **ORC-02**: Orchestrator selects and assembles appropriate agent crew for the task
- [ ] **ORC-03**: Orchestrator manages task lifecycle (start, delegate, retry, complete)
- [ ] **ORC-04**: Task state persisted in DynamoDB (survives ECS task restarts)
- [ ] **ORC-05**: Orchestrator enforces token budget limits per task
- [ ] **ORC-06**: Orchestrator kills runaway tasks that exceed budget or time limits

### Agent Pool

- [ ] **AGT-01**: Coder Agent — reads requirements, writes code to EFS workspace
- [ ] **AGT-02**: Reviewer Agent — reviews code diff, returns structured feedback
- [ ] **AGT-03**: Tester Agent — writes and runs unit/integration tests
- [ ] **AGT-04**: Security Agent — scans code for vulnerabilities and compliance issues
- [ ] **AGT-05**: Doc Agent — generates/updates documentation for changed code
- [ ] **AGT-06**: Orchestrator Agent — delegates subtasks, aggregates results
- [ ] **AGT-07**: Agents share workspace state via EFS-mounted persistent volume

### MCP Tool Integration

- [ ] **MCP-01**: GitHub MCP server — create branch, commit, push, open PR
- [ ] **MCP-02**: Jira MCP server — read ticket, post comment, update status
- [ ] **MCP-03**: Shell/File Ops tool — execute commands, read/write files in workspace
- [ ] **MCP-04**: Code execution tool — run tests, linters, build commands in sandbox

### Human-in-the-Loop

- [ ] **HITL-01**: Agent pauses and requests approval before opening a PR
- [ ] **HITL-02**: Approval request sent to Jira comment and/or Slack
- [ ] **HITL-03**: Human can approve, reject, or provide feedback via Jira/Slack
- [ ] **HITL-04**: Agent resumes or adjusts based on human response

### Streaming & Output

- [ ] **OUT-01**: Real-time progress streamed to Jira ticket comments as agent works
- [ ] **OUT-02**: Final result (PR link, test results, summary) posted to Jira ticket
- [ ] **OUT-03**: Error states reported back to trigger source with actionable message

### LLM & Reliability

- [ ] **LLM-01**: Primary LLM: Anthropic Claude API (claude-3-5-sonnet / claude-4-sonnet)
- [ ] **LLM-02**: Fallback LLM: AWS Bedrock (global.anthropic.claude-sonnet-4-6)
- [ ] **LLM-03**: Auto-failover from Claude API to Bedrock on rate limit or 5xx errors
- [ ] **LLM-04**: Prompt caching enabled to reduce repeated token costs

### Deployment & Infrastructure

- [ ] **INF-01**: Service deployed as ECS Fargate long-running task
- [ ] **INF-02**: EFS volume mounted for persistent git workspace across restarts
- [ ] **INF-03**: All API keys stored in AWS Secrets Manager (not env vars)
- [ ] **INF-04**: CDK stack manages all infra (ECS, SQS, EFS, DynamoDB, Secrets)
- [ ] **INF-05**: Docker image built and pushed to ECR

### Observability

- [ ] **OBS-01**: LangSmith tracing for all agent runs (task ID, agent chain, token usage)
- [ ] **OBS-02**: CloudWatch metrics — task success/failure rates, duration, token spend
- [ ] **OBS-03**: Structured logs for all agent actions, tool calls, and decisions

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Sidecar Runners

- **RUN-01**: Ephemeral ECS tasks for heavy build/test jobs (isolated from main swarm)
- **RUN-02**: Sidecar runners communicate results back via S3 artifact upload
- **RUN-03**: Build matrix support (test against multiple Python/Node versions)

### Temporal.io Durable Workflows

- **DUR-01**: Temporal workflow wraps agent runs for checkpoint/resume on failure
- **DUR-02**: Temporal handles long-running tasks that exceed ECS task timeouts
- **DUR-03**: Workflow history queryable via Temporal Web UI

### Advanced Agent Capabilities

- **ADV-01**: Agents can spawn sub-agents for complex parallel sub-tasks
- **ADV-02**: Agent memory: cross-task learning stored in Redis/DynamoDB
- **ADV-03**: Multi-repo support — agents work across multiple GitHub repos
- **ADV-04**: Agents index codebase semantically for efficient code navigation

### Multi-Integration

- **INT-01**: Linear.app webhook trigger (alternative to Jira)
- **INT-02**: PagerDuty trigger — incident-triggered automated debugging
- **INT-03**: Notion integration — write design docs as part of task

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web/mobile UI dashboard | API-first, monitoring via Jira/Slack/CloudWatch is sufficient for v1 |
| Multi-tenant isolation | Single-team deployment, not a SaaS product for v1 |
| Custom model fine-tuning | Use Anthropic/Bedrock APIs only; fine-tuning overkill for current use case |
| Autonomous deployment to production | Human-in-the-loop required for all prod deploys by policy |
| GitHub Actions replacement | Complementary to CI/CD, not a replacement |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TRG-01..06 | Phase 1 | Pending |
| ORC-01..06 | Phase 2 | Pending |
| AGT-01..07 | Phase 3 | Pending |
| MCP-01..04 | Phase 3 | Pending |
| HITL-01..04 | Phase 4 | Pending |
| OUT-01..03 | Phase 4 | Pending |
| LLM-01..04 | Phase 2 | Pending |
| INF-01..05 | Phase 5 | Pending |
| OBS-01..03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 36 total
- Mapped to phases: 36
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-26*
*Last updated: 2026-02-26 after initial definition*
