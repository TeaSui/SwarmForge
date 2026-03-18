from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are SwarmForge, an autonomous code-generation agent.
You receive a Jira ticket context (key, summary, description, labels, acceptance criteria)
and produce implementation code.

Rules:
- Output ONLY a JSON object with the schema below. No markdown fences, no commentary.
- Each file must contain syntactically valid code for its language.
- Include unit tests when the scope is clear enough.
- Keep changes minimal and focused on the ticket scope.
- Use clear naming, avoid magic numbers, prefer immutability.

Output JSON schema:
{
  "files": [
    {
      "path": "relative/path/to/file.ext",
      "content": "file content as a string",
      "language": "dart|python|yaml|..."
    }
  ],
  "summary": "one-line description of what was generated",
  "reasoning": "brief explanation of design choices"
}
"""

CODEGEN_USER_TEMPLATE = """\
Generate implementation code for the following Jira ticket.

Issue Key: {issue_key}
Summary: {summary}
Description: {description}
Labels: {labels}
Acceptance Criteria: {acceptance_criteria}

Additional context from research phase:
{research_context}
"""


@dataclass
class SynthesizedCode:
    files: list[dict[str, str]] = field(default_factory=list)
    summary: str = ""
    reasoning: str = ""
    raw_response: str = ""
    error: str | None = None


def _extract_json(text: str) -> dict[str, Any]:
    """Extract JSON from LLM response, handling markdown fences."""
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    return json.loads(cleaned)


class LLMCodeSynthesizer:
    """Generates code from Jira ticket context using the LLM client."""

    def __init__(self, llm_client: Any | None = None):
        self._llm_client = llm_client

    def _get_llm_client(self) -> Any:
        if self._llm_client is not None:
            return self._llm_client
        from services.llm_client import llm_client
        return llm_client

    def _build_description(self, context: dict[str, Any]) -> str:
        payload = context.get("payload", {})
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})

        raw_description = fields.get("description", "")
        if isinstance(raw_description, dict):
            raw_description = json.dumps(raw_description)

        return str(raw_description or context.get("summary", ""))

    def _build_acceptance_criteria(self, context: dict[str, Any]) -> str:
        payload = context.get("payload", {})
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})

        criteria = fields.get("acceptance_criteria", "")
        if not criteria:
            criteria = fields.get("customfield_10016", "")
        return str(criteria or "Not specified")

    def _build_prompt(self, context: dict[str, Any], research_output: str) -> str:
        issue_key = context.get("task_id", "UNKNOWN")
        summary = context.get("summary", "")
        labels = context.get("labels", [])
        description = self._build_description(context)
        acceptance_criteria = self._build_acceptance_criteria(context)

        return CODEGEN_USER_TEMPLATE.format(
            issue_key=issue_key,
            summary=summary,
            description=description,
            labels=", ".join(str(label) for label in labels) if labels else "none",
            acceptance_criteria=acceptance_criteria,
            research_context=research_output or "No prior research available.",
        )

    async def synthesize(
        self,
        context: dict[str, Any],
        research_output: str = "",
    ) -> SynthesizedCode:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
        except Exception:
            HumanMessage = None  # type: ignore[assignment]
            SystemMessage = None  # type: ignore[assignment]

        client = self._get_llm_client()
        user_prompt = self._build_prompt(context, research_output)

        if SystemMessage is not None and HumanMessage is not None:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
        else:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

        try:
            response = await client.chat(messages)
            raw = response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.error("LLM code synthesis failed: %s", exc)
            return SynthesizedCode(error=str(exc), raw_response="")

        try:
            parsed = _extract_json(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to parse LLM codegen response as JSON: %s", exc)
            return SynthesizedCode(
                error=f"JSON parse error: {exc}",
                raw_response=raw,
            )

        files = parsed.get("files", [])
        validated_files = []
        for entry in files:
            path = entry.get("path", "")
            content = entry.get("content", "")
            if path and content:
                validated_files.append({
                    "path": path,
                    "content": content,
                    "language": entry.get("language", ""),
                })

        return SynthesizedCode(
            files=validated_files,
            summary=parsed.get("summary", ""),
            reasoning=parsed.get("reasoning", ""),
            raw_response=raw,
        )
