from services.agent_base import BaseSwarmAgent
from services.agent_contract import AgentExtensionRegistry, AgentExtensionSpec, AgentRiskLevel
from services.mcp_tools import all_mcp_tools, jira_tools, github_tools

class ResearchAgent(BaseSwarmAgent):
    def __init__(self):
        super().__init__(
            role="Technical Researcher",
            goal="Scan Jira tickets, GitHub code, and Slack history to gather full context for a task.",
            backstory="You are an expert at information gathering. You know where to find obscure details in deep documentation or legacy code.",
            tools=all_mcp_tools
        )

class CoderAgent(BaseSwarmAgent):
    def __init__(self):
        super().__init__(
            role="Full-Stack Engineer",
            goal="Implement technical solutions based on research. Write clean, tested, and efficient code.",
            backstory="You are a logic specialist. You translate requirements into high-quality code and prioritize maintainability.",
            tools=github_tools
        )

class ReviewerAgent(BaseSwarmAgent):
    def __init__(self):
        super().__init__(
            role="Quality Assurance Lead",
            goal="Review code changes for bugs, style consistency, and architectural alignment.",
            backstory="You have a sharp eye for detail. You ensure that every piece of code meets the highest standards before deployment.",
            tools=jira_tools # For commenting on PRs/Tickets
        )

class SREAgent(BaseSwarmAgent):
    def __init__(self):
        super().__init__(
            role="Site Reliability Engineer",
            goal="Verify the stability and performance of deployments. Monitor health checks and logs.",
            backstory="You are the guardian of uptime. You ensure that the system is healthy and performant.",
            tools=[] # To be populated with monitoring tools later
        )

class LazyAgentAdapter:
    """
    Adapter that lazily creates real agents and delegates execution.
    """

    def __init__(self, agent_key: str):
        self.agent_key = agent_key

    def _resolve(self) -> BaseSwarmAgent:
        if self.agent_key not in agent_pool:
            agent_pool.update(build_agent_pool())
        return agent_pool[self.agent_key]

    def execute_task(self, task_description: str, context=None) -> str:
        return self._resolve().execute_task(task_description, context=context)


extension_registry = AgentExtensionRegistry()
extension_registry.register(
    AgentExtensionSpec(
        extension_id="researcher_agent",
        display_name="Research Agent",
        owner_stages=("intent-analysis", "solution-plan"),
        capabilities=("context-gathering", "requirements-discovery"),
        risk_level=AgentRiskLevel.LOW,
    ),
    LazyAgentAdapter("researcher"),
)
extension_registry.register(
    AgentExtensionSpec(
        extension_id="coder_agent",
        display_name="Coder Agent",
        owner_stages=("code-generation",),
        capabilities=("implementation", "refactoring"),
        risk_level=AgentRiskLevel.MEDIUM,
    ),
    LazyAgentAdapter("coder"),
)
extension_registry.register(
    AgentExtensionSpec(
        extension_id="reviewer_agent",
        display_name="Reviewer Agent",
        owner_stages=("code-review", "documentation"),
        capabilities=("review", "documentation-feedback"),
        risk_level=AgentRiskLevel.MEDIUM,
    ),
    LazyAgentAdapter("reviewer"),
)
extension_registry.register(
    AgentExtensionSpec(
        extension_id="sre_agent",
        display_name="SRE Agent",
        owner_stages=(
            "test-verification",
            "e2e-verification",
            "ui-accessibility-gate",
            "security-check",
            "post-deploy-slo-gate",
            "release-gate",
        ),
        capabilities=("reliability-validation", "slo-monitoring", "release-readiness"),
        risk_level=AgentRiskLevel.HIGH,
    ),
    LazyAgentAdapter("sre"),
)


def get_stage_extensions(stage: str) -> list[str]:
    return [spec.extension_id for spec, _ in extension_registry.for_stage(stage)]


def get_stage_agents(stage: str):
    return extension_registry.for_stage(stage)


def build_agent_pool() -> dict[str, BaseSwarmAgent]:
    """
    Lazy instantiation avoids import-time side effects in test environments.
    """
    return {
        "researcher": ResearchAgent(),
        "coder": CoderAgent(),
        "reviewer": ReviewerAgent(),
        "sre": SREAgent(),
    }


# Backward-compatible lazy pool holder.
agent_pool: dict[str, BaseSwarmAgent] = {}
