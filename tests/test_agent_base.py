import pytest
from services.agent_base import BaseSwarmAgent, AgentMemory

def test_agent_memory_save_get():
    memory = AgentMemory()
    memory.save("shared_key", "secret_value")
    assert memory.get("shared_key") == "secret_value"
    assert memory.get("non_existent") is None

def test_base_swarm_agent_init():
    # Simple init test to ensure CrewAI dependency is working
    agent_wrapper = BaseSwarmAgent(
        role="Tester",
        goal="Verify the base class",
        backstory="A specialized testing unit."
    )
    assert agent_wrapper.agent.role == "Tester"
    assert agent_wrapper.agent.goal == "Verify the base class"
