# Definition of Done

This document defines when a SwarmForge task or chain can be considered complete.

## Task-Level DoD

A task is `Done` only when all required conditions are true:

- Orchestrator state is `COMPLETED`.
- Quality gates pass with no required failures.
- Jira task has a completion comment from SwarmForge.
- GitHub delivery PR exists and is mergeable.
- Required tests for scope pass (unit/integration/e2e as applicable).
- Security gate passes.

## Scope-Aware Quality Requirements

Baseline requirements:

- `artifacts-complete`
- `tests-pass`
- `security-pass`
- `delivery-pr`

UI scope adds:

- `ui-a11y-pass`
- `ui-files-changed`
- `ui-design-signal`

Release/UAT/E2E scope adds:

- `e2e-pass`
- `post-deploy-slo-pass` (release scope)

## Chain-Level DoD

A chain is `Done` only when:

- All story/task issues are `Done`.
- The chain epic is `Done`.
- No blocking/open PR remains for the chain.
- No unresolved task with `state=FAILED` and `metadata.sub_state=QUALITY_GATES_FAILED` remains in the chain.

## Not Done Signals

Any of the following means work is not complete:

- Task state `FAILED`.
- Missing delivery PR on Jira-sourced task.
- Open duplicates/partial PRs for the same issue key.

## Recovery Procedure

When quality gates fail:

1. Read failed checks from Jira comment.
2. Fix root cause in code or pipeline.
3. Redeploy SwarmForge if runtime logic changed.
4. Retrigger the same Jira issue webhook.
5. Verify new completion comment includes gate pass evidence.
