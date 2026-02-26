# Phase 3: Agent Pool & MCP Tools — Research

**Phase:** 3 — Agent Pool & MCP Tools
**Researched:** 2026-02-26
**Goal:** Implement specialized agents (Coder, Reviewer, Tester, Security, Doc, Orchestrator) and connect them to GitHub, Jira, and Shell MCP servers.

## RESEARCH COMPLETE

---

## 1. Agent Definitions & Roles

### Coder Agent
- **Role:** Professional Software Engineer
- **Goal:** Write clean, efficient, and well-tested code that follows project standards.
- **Tools:** GitHub MCP, Shell/File Ops, Code Execution.
- **System Prompt Focus:** TDD, clean code, handling edge cases.

### Reviewer Agent
- **Role:** Principal Engineer / Technical Lead
- **Goal:** Audit code changes for logic, security, performance, and style.
- **Tools:** GitHub MCP (Read Diff), File Ops.
- **System Prompt Focus:** Finding bugs, architectural alignment, style guide adherence.

### Tester Agent
- **Role:** QA Automation Engineer
- **Goal:** Ensure 100% functional correctness via unit and integration tests.
- **Tools:** Shell (pytest/unittest), File Ops, Code Execution.
- **System Prompt Focus:** Boundary testing, mocking external dependencies.

### Security Agent
- **Role:** Security Researcher / AppSec Engineer
- **Goal:** Identify vulnerabilities (OWASP Top 10) and sensitive data leaks.
- **Tools:** Shell (bandit/semgrep), File Ops.
- **System Prompt Focus:** SQL injection, XSS, credential handling.

### Doc Agent
- **Role:** Technical Writer
- **Goal:** Ensure API docs, READMEs, and internal wikis stay in sync with code.
- **Tools:** File Ops, GitHub MCP.
- **System Prompt Focus:** Clarity, accuracy, developer experience.

### Orchestrator Agent (Manager)
- **Role:** Engineering Manager
- **Goal:** Coordinate the work of other agents, resolve conflicts, and verify overall completion.
- **Tools:** Delegates to other agents.

---

## 2. MCP Tool Integration

### GitHub MCP Configuration
- **Server:** `@modelcontextprotocol/server-github`
- **Capabilities:** 
  - `create_or_update_file_contents`
  - `get_file_contents`
  - `create_pull_request`
  - `list_commits`
- **Auth:** `GITHUB_TOKEN` from Secrets Manager.

### Jira MCP Configuration
- **Server:** `jira-mcp-server`
- **Capabilities:**
  - `add_comment`
  - `get_issue`
  - `update_issue_status`
- **Auth:** `JIRA_API_TOKEN` + `JIRA_EMAIL` + `JIRA_BASE_URL`.

### Shell/File Ops Integration
- **Capabilities:**
  - Standard Unix commands (ls, mkdir, cat).
  - Python execution (pip, pytest).
  - Git commands (local branch management).
- **Workspace:** All ops restricted to `/mnt/efs/workspace` (Phase 5 CDK setup).

---

## 3. Persistent Workspace (EFS)

- Multiple agents running in different ECS tasks (or sequential steps) need shared state.
- **EFS (Elastic File System)** allows standard file system access across agents.
- **Local Git Clone:** The first agent in the wave clones the repo to EFS. Subsequent agents work on the same directory.

---

## 4. Testing & Verification Patterns

### Mocking MCP Servers in Dev
- Use local Docker containers or mock classes for GitHub/Jira APIs during local testing.

### Tool Call Limits
- Enforce max 20 tool calls per agent run to prevent infinite loops.

---

*Phase: 03-agent-pool-mcp-tools | Research: 2026-02-26*
