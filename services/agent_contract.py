from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class AgentRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class AgentExecutionResult:
    success: bool
    summary: str
    artifacts: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SwarmSubAgent(Protocol):
    def execute_task(self, task_description: str, context: list[Any] | None = None) -> str:
        ...


@dataclass(frozen=True)
class AgentExtensionSpec:
    extension_id: str
    display_name: str
    owner_stages: tuple[str, ...]
    capabilities: tuple[str, ...]
    risk_level: AgentRiskLevel = AgentRiskLevel.MEDIUM
    version: str = "1.0.0"


class AgentRegistryError(ValueError):
    pass


class AgentExtensionRegistry:
    _EXT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
    CORE_STAGES = {
        "intent-analysis",
        "solution-plan",
        "code-generation",
        "code-review",
        "test-verification",
        "e2e-verification",
        "ui-accessibility-gate",
        "security-check",
        "documentation",
        "post-deploy-slo-gate",
        "release-gate",
    }

    def __init__(self):
        self._entries: dict[str, tuple[AgentExtensionSpec, SwarmSubAgent]] = {}

    def register(self, spec: AgentExtensionSpec, agent: SwarmSubAgent) -> None:
        self._validate_spec(spec)
        if spec.extension_id in self._entries:
            raise AgentRegistryError(f"Duplicate extension_id: {spec.extension_id}")
        self._entries[spec.extension_id] = (spec, agent)

    def get(self, extension_id: str) -> tuple[AgentExtensionSpec, SwarmSubAgent]:
        try:
            return self._entries[extension_id]
        except KeyError as exc:
            raise AgentRegistryError(f"Unknown extension_id: {extension_id}") from exc

    def list_specs(self) -> list[AgentExtensionSpec]:
        return [entry[0] for entry in self._entries.values()]

    def for_stage(self, stage: str) -> list[tuple[AgentExtensionSpec, SwarmSubAgent]]:
        return [entry for entry in self._entries.values() if stage in entry[0].owner_stages]

    def _validate_spec(self, spec: AgentExtensionSpec) -> None:
        if not self._EXT_ID_PATTERN.match(spec.extension_id):
            raise AgentRegistryError(f"Invalid extension_id format: {spec.extension_id}")
        if not spec.display_name.strip():
            raise AgentRegistryError("display_name is required")
        if not spec.owner_stages:
            raise AgentRegistryError("owner_stages is required")
        unknown_stages = [s for s in spec.owner_stages if s not in self.CORE_STAGES]
        if unknown_stages:
            raise AgentRegistryError(f"Unknown owner_stages: {', '.join(sorted(unknown_stages))}")
        if not spec.capabilities:
            raise AgentRegistryError("capabilities is required")
