# Cost Guardrails

**Updated:** 2026-02-26
**Owner:** SwarmForge Orchestrator

## Budget Policy

- Monthly AI budget cap: **$1,500**
- Weekly AI budget cap: **$375**
- Per-task soft cap: **$3.00**
- Per-task hard cap: **$6.00** (force terminate)

## Token Policy

- Default token budget per task: **120,000**
- Hard stop threshold: **140,000** tokens
- Max retries per task: **2**
- Max full-crew reruns: **1**

## Runtime Policy

- Max wall time per task: **25 minutes**
- SQS reprocess attempts before DLQ: **3**
- Max concurrent active tasks (initial): **5**

## Provider Policy

- Primary: Claude API
- Fallback: Bedrock only on 429/5xx
- No automatic fallback for 4xx prompt/input errors

## Escalation Rules

- Pause new executions when weekly burn > 85%
- Enter read-only mode when monthly burn > 95%
- Send alert to Jira + Slack when hard cap terminate happens

## Metrics to Track

- Cost per completed task
- Cost per failed task
- Token burn by agent role
- Fallback rate (%)
- Retry rate (%)

## Enforcement Points

- `orchestrator/budget.py`: token and dollar guard checks
- `orchestrator/orchestrator.py`: task timeout + retry cap enforcement
- `orchestrator/state_manager.py`: persist usage and termination reason
- `infra/swarmforge_stack.py`: CloudWatch alarms for budget thresholds
