# Coding Conventions

**Analysis Date:** 2026-02-26

## Naming Patterns

**Files:**
- Planning anchors use uppercase filenames (`PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`)
- Workflow and command docs use kebab-case (`new-project.md`, `map-codebase.md`)
- JSON config files use lowercase (`config.json`, `settings.json`)

**Functions:**
- No application function source code present in this repo yet

**Variables and Types:**
- No project runtime code present; conventions will need to be defined when `src/` is introduced

## Code Style

**Current repository style:**
- Markdown-first documentation style
- Structured headings and checklist/table formats for planning docs
- CLI utility outputs consumed as JSON where possible

**Linting/Formatting:**
- No root-level formatter/linter configuration detected for application code

## Import Organization

**Current state:**
- Not applicable yet (no application code modules)

**Recommended for implementation phase:**
1. External dependencies
2. Internal absolute/aliased modules
3. Relative modules
4. Type-only imports (if TypeScript is adopted)

## Error Handling

**Observed pattern in tooling workflow:**
- Utility command failure is surfaced by non-zero exit with explicit error message
- Workflow preconditions checked via `gsd-tools.cjs init` before running steps

## Logging

**Current:**
- CLI textual output is the primary mechanism

**Planned:**
- Structured runtime logs to CloudWatch once service code exists

## Comments

**Current documentation conventions:**
- Explain intent and operational guidance, not only syntax
- Keep actionability high (paths, commands, next steps)

## Function Design

**Current state:**
- No application function bodies to infer a concrete function style guide

**Recommendation once code exists:**
- Prefer small focused functions and explicit error boundaries
- Keep orchestration logic separated from integration adapters

## Module Design

**Current state:**
- Module design is represented by markdown workflow modules, not runtime code modules

**Recommendation for future codebase:**
- Separate ingress, orchestration, agent roles, integrations, and observability modules

---
*Convention analysis: 2026-02-26*
*Update after first implementation phase introduces source code*
