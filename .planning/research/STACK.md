# Stack Research

**Domain:** Autonomous AI software engineering swarm (Jira-to-PR workflow)
**Researched:** 2026-02-26
**Confidence:** MEDIUM

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime for orchestrator and agents | Strong ecosystem for AI tooling and async services |
| FastAPI | 0.11x+ | Ingress API for Jira/Slack/Webhook triggers | Fast async handling with good validation and OpenAPI support |
| CrewAI | Latest stable | Multi-agent orchestration | Native abstraction for role-based agents and crew execution |
| AWS ECS Fargate | Current | Long-running runtime | Handles long tasks better than short-lived serverless patterns |
| AWS SQS + DLQ | Current | Queueing and retry isolation | Decouples trigger spikes from orchestration execution |
| Anthropic Claude API + AWS Bedrock fallback | Current | Primary and fallback LLM providers | Balances model quality with enterprise reliability and compliance |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| boto3 | Latest stable | AWS integration for SQS, DynamoDB, Secrets Manager, EFS-related flows | Always in production deployment |
| pydantic | v2 | Payload contracts and config validation | Validate trigger schema and agent message envelopes |
| httpx | Latest stable | Async HTTP client | Provider clients and external webhook callbacks |
| pytest | Latest stable | Unit and integration testing | Validate agent/tool contracts and orchestration flows |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Docker | Build and run production-like container image | Keep local image close to ECS task definition |
| AWS CDK | Infrastructure as code | Single deploy path for ECS, SQS, EFS, DynamoDB, Secrets |
| Ruff + mypy | Linting and type checking | Catch orchestration bugs early in async code paths |

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| ECS Fargate | AWS Lambda | Use only for short, bursty tasks with strict runtime limits |
| CrewAI | LangGraph/custom orchestration | Use if deterministic graph control is the top priority |
| FastAPI | API Gateway direct to queue | Use for minimal trigger-only ingestion with no app logic |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Single-provider LLM only | Outage/rate-limit risk can stall all automation | Dual-provider strategy with automatic fallback |
| Stateless ephemeral workspace only | Agents lose git context and intermediate artifacts | EFS-backed persistent workspace |
| Unbounded agent autonomy | Runaway token/cost and unintended repo changes | Budget manager + human approval gates |

## Stack Patterns by Variant

**If team is cost-sensitive early:**
- Use smaller Claude model tiers for non-critical sub-agents
- Keep Bedrock fallback enabled for resilience

**If enterprise security requirements increase:**
- Shift more traffic to Bedrock-hosted models
- Tighten IAM, VPC endpoints, and secrets access boundaries

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| FastAPI (Pydantic v2 era) | Python 3.11+ | Keep pydantic and framework versions aligned |
| CrewAI latest stable | Python 3.11+ | Re-verify dependency set during each phase plan |
| boto3 latest stable | AWS APIs | Pin for reproducible deploy behavior |

## Sources

- `/Users/tungnguyen/TYME/SwarmForge/README.md` — product intent, runtime, infra baseline
- Existing `.planning/*.md` artifacts — requirement and roadmap assumptions
- Internal project context from initialization session

---
*Stack research for: Autonomous AI engineering swarm*
*Researched: 2026-02-26*
