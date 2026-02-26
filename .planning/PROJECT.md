# SwarmForge

## What This Is

SwarmForge is a Python-native autonomous AI swarm system powered by CrewAI multi-agent orchestration. It transforms complex engineering tasks (e.g., Jira ticket → code generation → review → test → PR) into fully autonomous, collaborative agent workflows deployed on AWS ECS Fargate. Built for TYME's engineering automation needs, it replaces rigid pipeline systems with dynamic, self-coordinating agent swarms.

## Core Value

**A Jira ticket triggers a full autonomous development cycle — write, review, test, and PR — with no human involvement until approval.**

## Requirements

### Validated

- ✓ Project architecture defined (FastAPI ingress, CrewAI orchestrator, ECS Fargate runtime) — existing
- ✓ LLM strategy defined (Claude API primary, Bedrock fallback) — existing
- ✓ Jira + GitHub MCP integration scaffolded — existing
- ✓ Webhook/SQS trigger mechanism designed — existing

### Active

- [ ] FastAPI ingress service — receive Jira/Slack/Webhook triggers
- [ ] CrewAI Orchestrator — parse intent, delegate to agent pool
- [ ] Agent Pool — Coder, Reviewer, Tester, Security, Doc, Orchestrator agents
- [ ] MCP Tool Layer — GitHub API, Jira API, Shell/File Ops via MCP servers
- [ ] Token Budget Manager — enforce limits, kill runaway tasks
- [ ] Human-in-the-Loop — approval gate for PR/commit actions
- [ ] Streaming Response — real-time output back to Jira/Slack/Webhook
- [ ] ECS Fargate deployment — persistent swarm runtime with EFS workspace
- [ ] SQS queue + DLQ — task queue with retry logic
- [ ] Observability — LangSmith tracing + CloudWatch metrics

### Out of Scope

- Temporal.io durable workflows — optional/deferred, adds complexity for v1
- Multi-tenant isolation — single-team deployment for v1
- Mobile/web UI — API-first, no frontend needed for v1
- Training or fine-tuning custom models — use Anthropic/Bedrock only

## Context

SwarmForge was created to overcome the limitations of TYME's existing agent-based automation:
- Previous system hit ECS task timeouts for long-running workflows
- Static orchestration couldn't handle dynamic task complexity
- Jira and GitHub MCP integrations have been prototyped (per conversation history: MCP server env vars fixed, agent trigger debugging completed)
- Claude 3.5/4 Sonnet selected for primary LLM due to latest feature support
- AWS Bedrock configured as fallback (`global.anthropic.claude-sonnet-4-6`)
- LangSmith selected for agent tracing/observability

## Constraints

- **Tech Stack**: Python 3.11+, CrewAI, FastAPI — established, not negotiable
- **Runtime**: AWS ECS Fargate — TYME's existing cloud infrastructure
- **LLM**: Anthropic Claude API (primary) + AWS Bedrock (fallback) — security/compliance requirement
- **Storage**: EFS for persistent git workspace, S3/DynamoDB for state
- **Integration**: Jira + GitHub as primary trigger/output surfaces
- **Security**: API keys via AWS Secrets Manager, not env vars in code

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CrewAI over custom orchestration | Battle-tested multi-agent framework, faster time-to-value | — Pending |
| Claude API primary + Bedrock fallback | Speed/features + reliability/enterprise security | — Pending |
| FastAPI over async Lambda | Long-running workflows exceed Lambda limits | — Pending |
| EFS for workspace | Persistent git repos across agent task restarts | — Pending |
| MCP for tool integration | Standard protocol for agent-tool communication | — Pending |
| SQS over direct invocation | Retry logic, backpressure, DLQ for failed tasks | — Pending |

---
*Last updated: 2026-02-26 after initialization*
