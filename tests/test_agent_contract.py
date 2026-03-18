import pytest

from services.agent_contract import (
    AgentExtensionRegistry,
    AgentExtensionSpec,
    AgentRegistryError,
)
from services.agents import extension_registry, get_stage_extensions


class DummyAgent:
    def execute_task(self, task_description: str, context=None) -> str:
        return task_description


def test_registry_rejects_invalid_stage():
    registry = AgentExtensionRegistry()
    with pytest.raises(AgentRegistryError):
        registry.register(
            AgentExtensionSpec(
                extension_id="dummy_agent",
                display_name="Dummy",
                owner_stages=("unknown-stage",),
                capabilities=("noop",),
            ),
            DummyAgent(),
        )


def test_registry_rejects_duplicate_extension_id():
    registry = AgentExtensionRegistry()
    spec = AgentExtensionSpec(
        extension_id="dummy_agent",
        display_name="Dummy",
        owner_stages=("code-review",),
        capabilities=("noop",),
    )
    registry.register(spec, DummyAgent())
    with pytest.raises(AgentRegistryError):
        registry.register(spec, DummyAgent())


def test_stage_extensions_are_exposed():
    extensions = get_stage_extensions("code-generation")
    assert "coder_agent" in extensions
    assert "researcher_agent" not in extensions


def test_default_registry_contains_core_agents():
    specs = {spec.extension_id for spec in extension_registry.list_specs()}
    assert {"researcher_agent", "coder_agent", "reviewer_agent", "sre_agent"}.issubset(specs)
