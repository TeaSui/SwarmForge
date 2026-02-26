# SwarmForge — Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-02-26)

**Core value:** A Jira ticket triggers a full autonomous development cycle — write, review, test, and PR — with no human involvement until approval.
**Current focus:** Phase 1 — Ingress & Queue (not started)

## Where We Are

```
Initialized: 2026-02-26
Milestone:   v1.0 MVP (Phases 1–6)
Phase:       0 of 6 complete
Status:      Ready to start Phase 1
```

## What's Done

- [x] PROJECT.md — project context and decisions
- [x] REQUIREMENTS.md — 36 v1 requirements across 9 categories
- [x] ROADMAP.md — 6 phases, 19 plans

## What's Next

**Run Phase 1:**
```
/gsd:plan-phase 1
```

This will research and plan Phase 1: FastAPI ingress, SQS queue, deduplication.

## Active Phase

_(none — not started)_

## Key Context for Next Session

- Existing Jira + GitHub MCP servers have been prototyped (env vars configured via Secrets Manager)
- Jira webhook label trigger and comment-based `@ai` mention both tested and working
- AWS CDK stack exists in `/infra` (partial — needs ECS Fargate, EFS, SQS for SwarmForge)
- Primary Claude model: `claude-3-5-sonnet-20241022` or `claude-sonnet-4` (check latest)
- Bedrock fallback model ID: `global.anthropic.claude-sonnet-4-6`
- LangSmith project: configure `LANGSMITH_API_KEY` in Secrets Manager

---
*Last updated: 2026-02-26 after initialization*
