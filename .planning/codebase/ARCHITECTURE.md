# Architecture

**Analysis Date:** 2026-02-26

## Pattern Overview

**Overall:** Planning-first repository with GSD workflow assets and generated planning documents.

**Key Characteristics:**
- Documentation-centric current state (minimal application source code)
- Workflow-driven planning under `.planning/`
- Tooling assets vendored under `.claude/` and `.gemini/`

## Layers

**Workflow Asset Layer:**
- Purpose: Defines reusable command, template, and workflow behavior
- Contains: `.claude/get-shit-done/`, `.claude/commands/gsd/`, `.gemini/...`
- Depends on: Node runtime for helper tools
- Used by: Claude/Gemini command environments

**Planning Artifact Layer:**
- Purpose: Captures product intent, requirements, roadmap, and execution state
- Contains: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`
- Depends on: GSD workflows and manual authoring
- Used by: Future plan/execute workflows

**Project Documentation Layer:**
- Purpose: High-level project description for humans
- Contains: `README.md`
- Depends on: none
- Used by: contributors and planning context

## Data Flow

**Planning Lifecycle Flow:**
1. User invokes GSD command (`npx get-shit-done-cc@latest`, slash command flow)
2. GSD tools generate/update files under `.planning/`
3. Planning docs guide future phase planning and execution
4. State is persisted via markdown/json artifacts in-repo

**State Management:**
- File-based state only (no runtime service state in current repo)

## Key Abstractions

**Workflow documents:**
- Purpose: Define deterministic planning behavior
- Examples: `.claude/get-shit-done/workflows/new-project.md`, `map-codebase.md`
- Pattern: Declarative markdown workflow specs

**Planning artifacts:**
- Purpose: Act as durable project memory and roadmap
- Examples: `.planning/PROJECT.md`, `.planning/STATE.md`
- Pattern: Structured markdown docs

## Entry Points

**Installer/Bootstrap:**
- Location: `npx get-shit-done-cc@latest` (external command execution)
- Responsibilities: install GSD assets into runtime-specific directories

**Workflow utilities:**
- Location: `.claude/get-shit-done/bin/gsd-tools.cjs`
- Responsibilities: init checks, commit helper, workflow utility operations

## Error Handling

**Strategy:** Command-level fail-fast (utility prints error and exits non-zero).

**Patterns:**
- `gsd-tools` returns structured JSON for success paths
- Missing preconditions (e.g., already initialized) are surfaced as explicit workflow guards

## Cross-Cutting Concerns

**Logging:**
- CLI/stdout oriented command output

**Validation:**
- Workflow prechecks via `gsd-tools.cjs init <workflow>`

**Security:**
- Sensitive runtime values expected to be handled outside repo (e.g., secrets manager), not committed in planning docs

---
*Architecture analysis: 2026-02-26*
*Update when executable application architecture is added*
