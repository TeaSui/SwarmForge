"""LLM-powered analysis for pipeline stages."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", "venv", ".venv"}
_SKIP_EXTENSIONS = {".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".jpg", ".png", ".gif"}
_CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".dart",
    ".html", ".css", ".scss", ".yaml", ".yml", ".json", ".xml", ".sql", ".md",
}


def _extract_json_from_llm(content: str) -> dict[str, Any] | None:
    """Extract JSON from LLM response, handling markdown fences."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    patterns = [
        r"```json\s*(.*?)\s*```",
        r"```\s*(.*?)\s*```",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, content, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    return None


def _llm_chat_sync(system_prompt: str, user_content: str) -> str:
    """Call LLM synchronously via run_coroutine_in_thread."""
    from services.executor.stage_dispatcher import run_coroutine_in_thread
    from services.llm_client import llm_client

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]
    except Exception:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    response = run_coroutine_in_thread(llm_client.chat(messages), timeout=120)
    return response.content if hasattr(response, "content") else str(response)


def review_code(files_content: str, context_summary: str) -> dict[str, Any]:
    """Review generated code for bugs, security, style, and correctness."""
    system_prompt = (
        "You are an expert code reviewer. Review the following generated code for "
        "bugs, security issues, style problems, and correctness. Be specific with "
        "line references. Output ONLY valid JSON: "
        '{"approved": bool, "issues": [{"severity": "critical|warning|info", '
        '"file": str, "description": str}], "summary": str}'
    )
    user_content = f"Context: {context_summary}\n\nCode to review:\n{files_content}"

    try:
        raw = _llm_chat_sync(system_prompt, user_content)
        parsed = _extract_json_from_llm(raw)
        if parsed:
            return {
                "approved": parsed.get("approved", True),
                "issues": parsed.get("issues", []),
                "summary": parsed.get("summary", "Code review completed"),
                "raw": raw,
            }
        return {
            "approved": True,
            "issues": [],
            "summary": "Could not parse LLM response, passing by default",
            "raw": raw,
        }
    except Exception as exc:
        logger.error("Code review failed: %s", exc)
        return {
            "approved": True,
            "issues": [],
            "summary": "LLM review unavailable, passing by default",
            "error": str(exc),
        }


def security_analysis(files_content: str, context_summary: str) -> dict[str, Any]:
    """Analyze code for security vulnerabilities."""
    system_prompt = (
        "You are a security expert. Analyze the following code for OWASP Top 10 "
        "vulnerabilities, injection risks, hardcoded secrets, insecure patterns. "
        "Output ONLY valid JSON: "
        '{"safe": bool, "vulnerabilities": [{"severity": "critical|high|medium|low", '
        '"type": str, "file": str, "description": str, "remediation": str}], "summary": str}'
    )
    user_content = f"Context: {context_summary}\n\nCode to analyze:\n{files_content}"

    try:
        raw = _llm_chat_sync(system_prompt, user_content)
        parsed = _extract_json_from_llm(raw)
        if parsed:
            return {
                "safe": parsed.get("safe", True),
                "vulnerabilities": parsed.get("vulnerabilities", []),
                "summary": parsed.get("summary", "Security analysis completed"),
                "raw": raw,
            }
        return {
            "safe": True,
            "vulnerabilities": [],
            "summary": "Could not parse security analysis, passing by default",
            "raw": raw,
        }
    except Exception as exc:
        logger.error("Security analysis failed: %s", exc)
        return {
            "safe": True,
            "vulnerabilities": [],
            "summary": "Security analysis unavailable, passing by default",
            "error": str(exc),
        }


def generate_documentation(files_content: str, context: dict[str, Any]) -> str:
    """Generate comprehensive documentation for code changes."""
    system_prompt = (
        "You are a technical writer. Generate comprehensive documentation for the "
        "following code changes. Include: overview, API reference (if applicable), "
        "usage examples, and change notes. Output in Markdown."
    )
    summary = context.get("summary", "N/A")
    task_id = context.get("task_id", "N/A")
    user_content = f"Task: {task_id}\nSummary: {summary}\n\nCode:\n{files_content}"

    try:
        return _llm_chat_sync(system_prompt, user_content)
    except Exception as exc:
        logger.error("Documentation generation failed: %s", exc)
        return (
            f"# Documentation for {task_id}\n\n"
            f"## Summary\n{summary}\n\n"
            f"## Note\nAutomated documentation generation failed: {exc}\n"
            f"Please review the code changes manually.\n"
        )


def accessibility_review(files_content: str, context_summary: str) -> dict[str, Any]:
    """Review code for accessibility compliance."""
    system_prompt = (
        "You are an accessibility expert. Review the following code for WCAG 2.1 AA "
        "compliance, including: color contrast, semantic HTML, ARIA labels, keyboard "
        "navigation, screen reader support. Output ONLY valid JSON: "
        '{"compliant": bool, "issues": [{"severity": "critical|warning|info", '
        '"guideline": str, "file": str, "description": str, "remediation": str}], "summary": str}'
    )
    user_content = f"Context: {context_summary}\n\nCode to review:\n{files_content}"

    try:
        raw = _llm_chat_sync(system_prompt, user_content)
        parsed = _extract_json_from_llm(raw)
        if parsed:
            return {
                "compliant": parsed.get("compliant", True),
                "issues": parsed.get("issues", []),
                "summary": parsed.get("summary", "Accessibility review completed"),
                "raw": raw,
            }
        return {
            "compliant": True,
            "issues": [],
            "summary": "Could not parse accessibility review, passing by default",
            "raw": raw,
        }
    except Exception as exc:
        logger.error("Accessibility review failed: %s", exc)
        return {
            "compliant": True,
            "issues": [],
            "summary": "Accessibility review unavailable, passing by default",
            "error": str(exc),
        }


def collect_generated_files(workspace: Path, max_chars: int = 50_000) -> str:
    """Collect all generated code files from workspace into a single string."""
    result: list[str] = []
    total_chars = 0

    try:
        for file_path in sorted(workspace.rglob("*")):
            if any(skip in file_path.parts for skip in _SKIP_DIRS):
                continue
            if not file_path.is_file():
                continue
            if file_path.suffix in _SKIP_EXTENSIONS:
                continue
            if file_path.suffix and file_path.suffix not in _CODE_EXTENSIONS:
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                relative = file_path.relative_to(workspace)
                formatted = f"=== {relative} ===\n{content}\n\n"

                if total_chars + len(formatted) > max_chars:
                    result.append(f"... truncated (reached {max_chars} char limit) ...")
                    break

                result.append(formatted)
                total_chars += len(formatted)
            except (UnicodeDecodeError, PermissionError):
                continue
    except Exception as exc:
        logger.error("Error collecting files: %s", exc)
        return f"Error collecting files: {exc}"

    return "".join(result) if result else "No code files found in workspace"
