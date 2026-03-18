# Agent Extension Contract

This contract defines how new sub-agents can be added without breaking SwarmForge core architecture.

## Core Principles

- Do not bypass orchestration stages.
- Do not bypass quality gates.
- Keep stage ownership explicit and auditable.
- Extension registration must be deterministic and validated at startup.

## Contract Surface

The contract is defined in:

- `services/agent_contract.py`
- `services/agents.py`

### Required spec fields

- `extension_id`: stable unique id (`^[a-z][a-z0-9_-]{1,63}$`)
- `display_name`: human-readable name
- `owner_stages`: tuple of allowed SwarmForge stages
- `capabilities`: tuple of capability tags
- `risk_level`: `low|medium|high`
- `version`: semantic version string

### Allowed owner stages

- `intent-analysis`
- `solution-plan`
- `code-generation`
- `code-review`
- `test-verification`
- `e2e-verification`
- `ui-accessibility-gate`
- `security-check`
- `documentation`
- `post-deploy-slo-gate`
- `release-gate`

## Lifecycle

1. Register extension in `services/agents.py`.
2. Registry validates contract.
3. Orchestrator records extension ownership in stage metadata (`extensions` list).
4. Quality gates continue to decide pass/fail before `COMPLETED`.

## Safety Rules

- Duplicate `extension_id` is rejected.
- Unknown stage ownership is rejected.
- Empty capabilities or stage ownership is rejected.
- High-risk agents should only own late-stage verification or release-related stages.

## How to add a new sub-agent

1. Implement agent class (usually extends `BaseSwarmAgent`).
2. Define and register `AgentExtensionSpec`.
3. Add tests:
   - registration success
   - stage mapping
   - invalid contract rejection
4. Validate with:
   - `pytest tests/test_agent_contract.py tests/test_orchestrator.py`

## Non-goals

- Extensions do not mutate orchestration control flow directly.
- Extensions do not alter approval gate semantics.
- Extensions do not auto-merge or release outside existing guarded pipeline.
