from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

try:
    from crewai.tools import BaseTool as CrewBaseTool
except Exception:  # pragma: no cover - fallback for local tests without crewai
    class CrewBaseTool:  # type: ignore[no-redef]
        name: str = ""
        description: str = ""

        def _run(self, *args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return self._run(*args, **kwargs)

from services.mcp_client import MCPClient, MCPClientError

_mcp_client = MCPClient()


def _format_tool_error(prefix: str, exc: Exception) -> str:
    return f"Error: {prefix}: {type(exc).__name__}: {exc}"


class JiraTools:
    """MCP-backed tools for Jira operations."""

    @staticmethod
    def get_issue_details(issue_key: str) -> str:
        """Get Jira issue summary and description by issue key."""
        try:
            data = _mcp_client.call_tool("jira.get_issue_details", {"issue_key": issue_key})
            return (
                f"Issue: {data.get('issue_key')}\n"
                f"Summary: {data.get('summary', 'No summary')}\n"
                f"Description: {data.get('description', 'No description')}"
            )
        except MCPClientError as exc:
            return _format_tool_error("failed to fetch issue", exc)

    @staticmethod
    def add_comment(issue_key: str, comment: str) -> str:
        """Add a text comment to a Jira issue."""
        try:
            _mcp_client.call_tool(
                "jira.add_comment",
                {"issue_key": issue_key, "comment": comment},
            )
            return f"Successfully added comment to {issue_key}"
        except MCPClientError as exc:
            return _format_tool_error("failed to add comment", exc)


class GitHubTools:
    """MCP-backed tools for GitHub operations."""

    @staticmethod
    def search_code(query: str) -> str:
        """Search GitHub code and return top matching repo/path pairs."""
        try:
            data = _mcp_client.call_tool("github.search_code", {"query": query})
            items = data.get("items", []) if isinstance(data, dict) else []
            if not items:
                return "No results found."
            return "\n".join(
                f"Repo: {item.get('repo')} | Path: {item.get('path')}" for item in items
            )
        except MCPClientError as exc:
            return _format_tool_error("github search failed", exc)


class _GetIssueInput(BaseModel):
    issue_key: str = Field(..., description="Jira issue key, e.g. SCRUM-18")


class _AddCommentInput(BaseModel):
    issue_key: str = Field(..., description="Jira issue key, e.g. SCRUM-18")
    comment: str = Field(..., description="Plain text comment to append to the Jira issue")


class _SearchCodeInput(BaseModel):
    query: str = Field(..., description="GitHub search query")


class JiraGetIssueTool(CrewBaseTool):
    name: str = "jira_get_issue_details"
    description: str = "Get Jira issue summary and description by issue key."
    args_schema: type[BaseModel] = _GetIssueInput

    def _run(self, issue_key: str | None = None, **kwargs: Any) -> str:
        issue_key = issue_key or str(kwargs.get("issue_key") or kwargs.get("tool_input") or "").strip()
        if not issue_key:
            return "Error: missing issue_key"
        return JiraTools.get_issue_details(issue_key)


class JiraAddCommentTool(CrewBaseTool):
    name: str = "jira_add_comment"
    description: str = "Add a text comment to a Jira issue."
    args_schema: type[BaseModel] = _AddCommentInput

    def _run(
        self,
        issue_key: str | None = None,
        comment: str | None = None,
        **kwargs: Any,
    ) -> str:
        issue_key = issue_key or str(kwargs.get("issue_key") or "").strip()
        comment = comment or str(kwargs.get("comment") or kwargs.get("tool_input") or "").strip()
        if not issue_key or not comment:
            return "Error: missing issue_key or comment"
        return JiraTools.add_comment(issue_key, comment)


class GitHubSearchCodeTool(CrewBaseTool):
    name: str = "github_search_code"
    description: str = "Search GitHub code and return top matching repo/path pairs."
    args_schema: type[BaseModel] = _SearchCodeInput

    def _run(self, query: str | None = None, **kwargs: Any) -> str:
        query = query or str(kwargs.get("query") or kwargs.get("tool_input") or "").strip()
        if not query:
            return "Error: missing query"
        return GitHubTools.search_code(query)


jira_tools = [JiraGetIssueTool(), JiraAddCommentTool()]
github_tools = [GitHubSearchCodeTool()]
all_mcp_tools = jira_tools + github_tools
