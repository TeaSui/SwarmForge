# Codebase Structure

**Analysis Date:** 2026-02-26

## Directory Layout

```text
SwarmForge/
├── .claude/                     # Claude Code runtime assets and GSD workflows
│   ├── commands/gsd/            # Slash command specs
│   ├── get-shit-done/           # Templates, references, workflows, tools
│   └── hooks/                   # Runtime hooks (status/update/context)
├── .gemini/                     # Gemini runtime assets (parallel to .claude)
├── .planning/                   # Project planning artifacts and phase docs
│   ├── research/                # Project-level research outputs
│   ├── codebase/                # Codebase map outputs (this mapping set)
│   └── phases/                  # Per-phase plan artifacts
├── .idea/                       # IDE metadata
├── .git/                        # Git metadata
└── README.md                    # Project overview and target architecture
```

## Directory Purposes

**`.claude/`:**
- Purpose: Claude Code command/workflow runtime package
- Key files: `.claude/commands/gsd/new-project.md`, `.claude/get-shit-done/bin/gsd-tools.cjs`

**`.gemini/`:**
- Purpose: Gemini runtime package for same GSD workflows
- Key files: `.gemini/commands/gsd/new-project.toml`, `.gemini/get-shit-done/workflows/`

**`.planning/`:**
- Purpose: Living planning state for this project
- Key files: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`

## Key File Locations

**Entry Points:**
- `README.md` - high-level project description
- `.claude/get-shit-done/bin/gsd-tools.cjs` - utility entry for workflow init/commit helpers

**Configuration:**
- `.planning/config.json` - planning mode/profile settings
- `.claude/settings.json` - Claude runtime integration settings

**Core Logic (current state):**
- No application source directories (e.g., `src/`, `app/`, `infra/`) currently present

**Testing:**
- No test directories currently present in this checkout

**Documentation:**
- `README.md`, `.planning/`, and GSD templates/workflows under `.claude/get-shit-done/`

## Naming Conventions

**Files:**
- Planning docs use uppercase names (`PROJECT.md`, `ROADMAP.md`, `STATE.md`)
- Workflow/template files use kebab-case (`new-project.md`, `plan-phase.md`)

**Directories:**
- Hidden dot-directories for tool/runtime state (`.claude`, `.gemini`, `.planning`)

**Special Patterns:**
- Phase plans: `.planning/phases/<phase-slug>/<phase-plan>.md`
- Research docs: `.planning/research/*.md`

## Where to Add New Code

**Future application implementation:**
- Primary code: `src/` (recommended to create)
- Tests: `tests/` or `src/**/__tests__/` (recommended to create)
- Infra code: `infra/` (recommended to create for AWS/CDK)

**Planning additions:**
- New phase plans: `.planning/phases/`
- New research artifacts: `.planning/research/`

---
*Structure analysis: 2026-02-26*
*Update when source code directories are introduced*
