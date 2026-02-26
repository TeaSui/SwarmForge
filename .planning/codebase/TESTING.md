# Testing Patterns

**Analysis Date:** 2026-02-26

## Test Framework

**Runner:**
- No project-local test runner detected yet for SwarmForge implementation code

**Assertion Library:**
- Not applicable yet

**Run Commands (current):**
```bash
node .claude/get-shit-done/bin/gsd-tools.cjs init new-project
node .claude/get-shit-done/bin/gsd-tools.cjs init map-codebase
```

## Test File Organization

**Current location:**
- No `tests/` directory or collocated test files detected

**Current structure:**
- Validation is primarily document/workflow consistency checks in planning stage

## Test Structure

**Current pattern:**
- Preconditions checked before workflow progression (`init` guard pattern)
- Artifact existence verification (`.planning/*` docs and required folders)
- Manual/CLI verification loops rather than automated unit/integration suites

## Mocking

**Current:**
- No mocking framework detected

**Future expectation (from roadmap):**
- Unit and integration tests for orchestrator, agents, and integration adapters

## Fixtures and Factories

**Current:**
- No runtime test fixtures detected

**Planning-adjacent fixtures:**
- GSD templates under `.claude/get-shit-done/templates/` act as document generation fixtures

## Coverage

**Current:**
- No automated coverage instrumentation detected

**Gap:**
- Repository has planning docs but no executable code coverage baseline

## Test Types

**Current practical verification types:**
- Workflow precheck tests (via utility command outputs)
- Artifact integrity checks (file presence/content review)

**Missing (to add during implementation):**
- Unit tests for core orchestration logic
- Integration tests for Jira/GitHub/LLM provider adapters
- End-to-end ticket-to-PR scenario tests

## Common Patterns

**Observed validation pattern:**
- Run command
- Inspect JSON output
- Confirm generated artifacts and statuses

**Risk:**
- Without automated tests, regressions will rely on manual detection

---
*Testing analysis: 2026-02-26*
*Update when runtime test framework is added*
