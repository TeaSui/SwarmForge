# Operations Runbook

This runbook describes how to monitor and operate SwarmForge in production.

## Primary Control Surfaces

- Jira board: work state and business progress.
- GitHub PRs: code delivery and merge status.
- CloudWatch logs: runtime execution and failures.
- DynamoDB `swarmforge-tasks`: canonical task state machine.

## Key Runtime States

Canonical states (external contract):
- `PENDING`
- `INTENT_PARSED`
- `IN_PROGRESS`
- `APPROVAL_NEEDED`
- `COMPLETED`

Diagnostic sub-states (internal detail for operators/debug):
- `PROCESSING`
- `STAGE_RUNNING`
- `STAGE_COMPLETED`
- `APPROVAL_REQUESTED`
- `APPROVAL_GRANTED`
- `APPROVAL_REJECTED`
- `QUALITY_GATES_FAILED`
- `FAILED`

## Standard Monitoring Loop

1. Check Jira for tasks not `Done`.
2. Check matching GitHub PR state for each issue key.
3. Check CloudWatch logs for orchestrator stage transitions and warnings.
4. If state is `FAILED` and `metadata.sub_state=QUALITY_GATES_FAILED`, read failed checks from Jira comment and remediate.
5. Retrigger issue webhook after remediation.

## Common Failure Modes

`FAILED` + `metadata.sub_state=QUALITY_GATES_FAILED`:
- Action: inspect failed check names in Jira comment.
- Typical causes: missing PR link, test warning, security warning, missing scope-specific artifacts.

`FAILED`:
- Action: inspect worker log stream and stage error metadata in DynamoDB.

## Safe Retry Rules

- Retries must keep same issue key.
- Avoid manual state mutation in DynamoDB.
- Prefer webhook retrigger over ad-hoc local patches.
- Keep duplicate PRs closed when superseded.

## Deployment Checklist

Before deploy:

- Relevant test suite passes locally.
- Docs updated for behavior changes.

After deploy:

- CloudFormation stack reaches `UPDATE_COMPLETE`.
- API/Consumer ECS services return to steady state.
- Trigger one representative issue and verify:
  - completion comment
  - quality gate summary
  - PR delivery/merge path
