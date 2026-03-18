# SwarmForge Refactoring Analysis

## Corrected File Sizes

The initial exploration overstated file sizes significantly. Here are the **actual** line counts:

| File | Actual Lines | Initially Reported |
|------|-------------|-------------------|
| `orchestrator.py` | 441 | ~17K |
| `stage_dispatcher.py` | 332 | ~15K |
| `test_llm_codegen.py` | 304 | ~11K |
| `test_autonomous_executor.py` | 195 | ~7K |
| `test_quality_gate.py` | 161 | ~6.7K |

**Verdict:** These files are reasonably sized. This is NOT a "god file" crisis — it's a well-structured codebase. The refactoring opportunities below are incremental improvements, not emergency surgery.

---

## Architecture Assessment

### What's Working Well

- **Clean dependency graph** — no circular imports detected
- **Orchestrator is well-composed** — delegates to StateManager, ApprovalGate, QualityGateEvaluator, BudgetManager, CrewStageRunner, and AutonomousExecutor
- **Stage dispatcher uses a handler registry** — clean mapping from stage names to handler methods
- **Tests have good coverage patterns** — each service has a corresponding test file, fixtures are shared via conftest.py

### Areas for Improvement

#### 1. `orchestrator.py` — `handle_task()` is 192 lines (43% of file)

This single method owns: planning, execution, approval gating, quality gates, budget tracking, Jira comments, error handling, and state transitions.

**Recommendation: Extract sub-orchestration methods**

```python
# Before: one 192-line method
async def handle_task(self, envelope):
    # ... everything

# After: composed pipeline
async def handle_task(self, envelope):
    ctx = self._extract_task_context(envelope)
    await self._initialize_task(ctx)
    try:
        plan = self._build_plan(ctx)
        await self._execute_stages(ctx, plan)
        await self._run_quality_gates(ctx)
        await self._finalize_success(ctx)
    except BudgetExceededError as exc:
        await self._handle_budget_exceeded(ctx, exc)
    except Exception as exc:
        await self._handle_failure(ctx, exc)
```

**Impact:** Each sub-method becomes independently testable. No new files needed.

#### 2. Jira Comment Logic Scattered Through `handle_task()`

`_sync_jira_comment()` is called 7+ times with hardcoded message strings inline.

**Recommendation: Extract a notification service**

```python
# services/task_notifications.py
class TaskNotifications:
    def __init__(self, jira_client):
        self.jira = jira_client

    def notify_plan_created(self, issue_key, stages):
        self.jira.post_comment(issue_key, f"[SwarmForge] Planned {len(stages)} stages...")

    def notify_stage_timeout(self, issue_key, stage_name, timeout):
        ...

    def notify_approval_rejected(self, issue_key, stage_name):
        ...

    def notify_completion(self, issue_key, summary):
        ...
```

**Impact:** Decouples notification logic from orchestration. Easy to add Slack/email channels later.

#### 3. `stage_dispatcher.py` — Repetitive Quality Gate Handlers

7 of 11 handlers follow the same pattern: `git_ops.run_command() → write JSON → check exit code`.

**Recommendation: Generic gate handler**

```python
def _run_git_gate(self, stage_name: str, command: list[str], run_dir: Path, ctx: dict) -> dict:
    """Generic handler for git-ops-based quality gates."""
    result = self.git_ops.run_command(command, cwd=run_dir)
    artifact = {"tool": command[0], "exit_code": result.returncode, "output": result.stdout}
    (run_dir / f"{stage_name.upper()}.json").write_text(json.dumps(artifact))
    return {"passed": result.returncode == 0, **artifact}
```

**Impact:** Eliminates ~70 lines of near-duplicate code. New gates become one-liners.

#### 4. Async Event Loop Handling Duplicated

`_run_llm_plan()` and `_run_llm_codegen()` both contain identical asyncio event loop workaround code.

**Recommendation: Extract utility**

```python
# services/executor/async_utils.py
async def run_coroutine_safe(coro):
    """Run a coroutine handling nested event loop scenarios."""
    try:
        loop = asyncio.get_running_loop()
        return await asyncio.ensure_future(coro)
    except RuntimeError:
        return asyncio.run(coro)
```

#### 5. `FlutterCodeGenerator` — Dead Dependency

Injected into `StageDispatcher.__init__()` but never referenced in any handler method.

**Recommendation:** Remove from constructor until actually used. Dead dependencies create confusion.

---

## Test Decomposition Opportunities

Current test files are already well-sized. The largest (`test_llm_codegen.py` at 304 lines) is split into 3 logical test classes. Rather than splitting files, focus on:

### Add Parametrized Tests

No `@pytest.mark.parametrize` usage detected. The quality gate tests especially would benefit:

```python
@pytest.mark.parametrize("labels,expected_scope", [
    (["ai-task", "deploy"], "release"),
    (["ai-task", "frontend"], "ui"),
    (["ai-task", "e2e"], "e2e"),
    (["ai-task"], "default"),
])
def test_scope_detection(labels, expected_scope):
    ...
```

### Add Missing Test Coverage

| Service | Test File | Gap |
|---------|-----------|-----|
| `stage_dispatcher.py` | No dedicated test file | Only tested indirectly via executor/codegen integration |
| `executor/git_ops.py` | No dedicated test file | Only mocked in other tests |
| `executor/github_delivery.py` | No dedicated test file | Tested through executor tests only |
| `notifications.py` | No test file | Untested |
| `sla_monitor.py` | `test_sla_monitor.py` (47 lines) | Minimal |

### Fixture Improvements

```python
# tests/conftest.py — add reusable task context factory
@pytest.fixture
def make_task_context():
    def _factory(labels=None, source="jira", summary="Test task"):
        return TaskContext(
            task_id=str(uuid.uuid4()),
            source=source,
            event_type="issue_updated",
            summary=summary,
            labels=labels or ["ai-task"],
            payload={},
        )
    return _factory
```

---

## Dependency Graph

```
main.py (FastAPI)
├── api/webhooks/jira.py ──→ SQSProducer, IdempotencyService
├── api/webhooks/slack.py ──→ SQSProducer, IdempotencyService
├── api/webhooks/generic.py ─→ SQSProducer
└── api/health.py

worker.py (SQS Consumer)
└── Orchestrator
    ├── StateManager ──→ DynamoDB
    ├── BudgetManager ──→ DynamoDB
    ├── ApprovalGate ──→ Jira API
    ├── QualityGateEvaluator ──→ GitHub API
    ├── CrewStageRunner ──→ CrewAI → LLM Client
    └── AutonomousExecutor
        └── StageDispatcher
            ├── GitOperations
            ├── GitHubDeliveryService ──→ GitHub API
            ├── LLMCodeSynthesizer ──→ LLM Client
            └── FlutterCodeGenerator (unused)
```

---

## Priority Refactoring Roadmap

### Phase 1: Quick Wins (< 1 day)
1. Remove unused `FlutterCodeGenerator` injection
2. Extract `_run_git_gate()` generic handler in stage_dispatcher
3. Extract async utility from duplicated event loop code
4. Add `test_stage_dispatcher.py` with direct unit tests

### Phase 2: Structural Improvements (1-2 days)
5. Break `handle_task()` into composed sub-methods
6. Extract `TaskNotifications` service from inline Jira comments
7. Add parametrized tests for scope detection and quality gates
8. Add `make_task_context` fixture factory

### Phase 3: Architecture Evolution (when needed)
9. Extract `PipelinePlanner` if plan logic grows
10. Extract `TaskContextParser` if new sources are added
11. Add dedicated test files for git_ops, github_delivery
12. Consider dependency injection if constructor chains grow
