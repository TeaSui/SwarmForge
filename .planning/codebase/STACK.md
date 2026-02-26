# Technology Stack

**Analysis Date:** 2026-02-26

## Languages

**Primary:**
- Markdown - project documentation and planning artifacts

**Secondary:**
- JavaScript (CommonJS) - GSD tool/runtime files under `.claude/get-shit-done/` and `.gemini/get-shit-done/`
- JSON - configuration files (`.claude/settings.json`, `.planning/config.json`)

## Runtime

**Environment:**
- Node.js (required by `npx get-shit-done-cc@latest` and `gsd-tools.cjs`)
- Claude Code slash-command environment (`.claude/commands/gsd/*.md`)

**Package Manager:**
- npm/npx
- Local package manifest present at `.claude/package.json` (type commonjs)

## Frameworks

**Core:**
- Get Shit Done (GSD) command/workflow system installed into `.claude/` and `.gemini/`

**Testing:**
- No project-local test framework detected yet for SwarmForge implementation code

**Build/Dev:**
- No application build tool detected yet (no `src/`, no project `package.json`, no `pyproject.toml`)

## Key Dependencies

**Critical:**
- `gsd-tools.cjs` in `.claude/get-shit-done/bin/` - planning utilities (`init`, `commit`, etc.)
- GSD workflow docs in `.claude/get-shit-done/workflows/` - command behavior source of truth

**Infrastructure:**
- Git repository metadata in `.git/`
- IDE/project metadata in `.idea/`

## Configuration

**Environment:**
- Planning configuration at `.planning/config.json`
- Claude command integration via `.claude/settings.json`

**Build:**
- No app build config detected in repository root

## Platform Requirements

**Development:**
- macOS/Linux shell with Node.js and npm
- Claude Code installed (`claude` command available)

**Production:**
- Not applicable yet (project currently in planning/document stage)

---
*Stack analysis: 2026-02-26*
*Update after adding real application runtime and dependencies*
