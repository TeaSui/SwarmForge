# Phase 2: Orchestration & LLM — Research

**Phase:** 2 — Orchestration & LLM
**Researched:** 2026-02-26
**Goal:** Parse task intent from SQS messages, assemble CrewAI crews, manage task lifecycle in DynamoDB, enforce token budgets, LLM failover.

## RESEARCH COMPLETE

---

## 1. CrewAI 2025 Patterns (v0.80+)

### Recommended Architecture: Flows + Crews
```python
# CrewAI Flows = orchestration layer (routing, state, conditionals)
# CrewAI Crews = agent execution layer (actual work)
from crewai.flow.flow import Flow, listen, start, router
from crewai import Crew, Agent, Task, Process

class SwarmForgeFlow(Flow):
    @start()
    def parse_intent(self):
        # Parse incoming SQS message, determine task type
        ...

    @router(parse_intent)
    def route_to_crew(self):
        # Route to "code_generation" | "code_review" | "doc_update" etc.
        ...

    @listen("code_generation")
    def run_code_generation_crew(self):
        crew = CodeGenerationCrew().crew()
        result = crew.kickoff(inputs=self.state)
        ...
```

### Key CrewAI Concepts
- **Flow**: Top-level orchestrator — handles routing, state, conditional execution
- **Crew**: A group of agents + tasks executing together (hierarchical or sequential)
- **Process**: `Process.hierarchical` (one manager agent delegates to workers) vs `Process.sequential`
- **Kickoff**: `crew.kickoff(inputs={...})` — synchronous; `crew.kickoff_async(...)` — async

### CrewAI State Management
```python
from pydantic import BaseModel
from crewai.flow.flow import FlowState

class TaskFlowState(FlowState):
    task_id: str
    source: str
    event_type: str
    jira_issue_id: str
    intent: str = ""
    code_written: str = ""
    review_passed: bool = False
    pr_url: str = ""
```

---

## 2. SQS Consumer Pattern

### Long-Polling Consumer Loop
```python
import boto3, json, asyncio
from concurrent.futures import ThreadPoolExecutor

class SQSConsumer:
    def __init__(self, queue_url: str, region: str):
        self.sqs = boto3.client("sqs", region_name=region)
        self.queue_url = queue_url
        self.running = True

    def consume(self):
        while self.running:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,       # Long polling — saves cost
                VisibilityTimeout=1800,   # 30 min — long enough for agent run
            )
            messages = response.get("Messages", [])
            for msg in messages:
                self._process_message(msg)

    def _process_message(self, msg: dict):
        try:
            body = json.loads(msg["Body"])
            # Dispatch to orchestrator
            orchestrator.dispatch(body)
            # Delete from queue on success
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=msg["ReceiptHandle"],
            )
        except Exception as e:
            # Do NOT delete — let visibility timeout expire → DLQ after maxReceiveCount
            logger.error(f"Failed to process {msg['MessageId']}: {e}")
```

---

## 3. Intent Parsing

### Use LLM-Backed Intent Classification
```python
INTENT_PROMPT = """
You are an intent classifier for a software engineering AI system.
Given this Jira ticket content, classify the primary intent.

Ticket: {summary}
Description: {description}
Labels: {labels}

Respond with exactly one of:
- code_generation: Write new code or implement a feature
- code_review: Review and analyze existing code
- bug_fix: Debug and fix an existing issue
- documentation: Write or update documentation
- test_generation: Write tests for existing code
- unknown: Cannot determine intent

Intent:"""

# Or use rule-based fast-path first, LLM as fallback
def classify_intent(ticket: dict) -> str:
    summary = ticket.get("summary", "").lower()
    if any(kw in summary for kw in ["write test", "add test", "unit test"]):
        return "test_generation"
    if any(kw in summary for kw in ["fix", "bug", "error", "broken"]):
        return "bug_fix"
    # Fallback to LLM
    return llm_classify(ticket)
```

---

## 4. DynamoDB Task State Schema

```python
# Table: swarmforge-tasks
# PK: task_id (String)
# GSI: source-status-index (source + status for querying active tasks)

TASK_STATUSES = ["PENDING", "INTENT_PARSED", "IN_PROGRESS", "APPROVAL_NEEDED",
                 "COMPLETE", "FAILED", "BUDGET_EXCEEDED", "CANCELLED"]

# Item shape:
{
    "task_id": "uuid",
    "source": "jira",
    "jira_issue_id": "PROJ-123",
    "event_type": "jira:issue_updated",
    "intent": "code_generation",
    "status": "IN_PROGRESS",
    "created_at": "ISO8601",
    "updated_at": "ISO8601",
    "token_usage": {"input": 12500, "output": 4800, "total": 17300},
    "token_budget": 100000,
    "result": null,
    "error": null,
    "ttl": 1700000000  # 7-day TTL
}
```

---

## 5. Token Budget Manager

```python
from dataclasses import dataclass, field

@dataclass
class TokenBudget:
    task_id: str
    limit: int = 100_000
    used: int = 0

    def check_and_add(self, tokens: int) -> bool:
        """Returns True if within budget, False if exceeded."""
        if self.used + tokens > self.limit:
            return False
        self.used += tokens
        return True

# CrewAI callback to track token usage
class BudgetTracker:
    def __init__(self, budget: TokenBudget):
        self.budget = budget

    def on_llm_end(self, response):
        usage = response.llm_output.get("token_usage", {})
        total = usage.get("total_tokens", 0)
        if not self.budget.check_and_add(total):
            raise BudgetExceededException(
                f"Token budget exceeded: used={self.budget.used}, limit={self.budget.limit}"
            )
```

---

## 6. LLM Failover Architecture

```python
from anthropic import Anthropic, APIStatusError, RateLimitError
import boto3

class LLMClient:
    def __init__(self):
        self.anthropic = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.bedrock = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)
        self.primary_model = "claude-3-5-sonnet-20241022"
        self.fallback_model = "global.anthropic.claude-sonnet-4-6"

    def chat(self, messages: list, system: str = "", **kwargs) -> str:
        try:
            return self._call_anthropic(messages, system, **kwargs)
        except (RateLimitError, APIStatusError) as e:
            logger.warning(f"Claude API error {e.status_code}, failing over to Bedrock")
            return self._call_bedrock(messages, system, **kwargs)

    def _call_anthropic(self, messages, system, **kwargs) -> str:
        resp = self.anthropic.messages.create(
            model=self.primary_model,
            messages=messages,
            system=system,
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        return resp.content[0].text

    def _call_bedrock(self, messages, system, **kwargs) -> str:
        import json
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": messages,
            "system": system,
            "max_tokens": kwargs.get("max_tokens", 4096),
        })
        resp = self.bedrock.invoke_model(
            modelId=self.fallback_model,
            body=body,
            contentType="application/json",
        )
        return json.loads(resp["body"].read())["content"][0]["text"]
```

---

## 7. Prompt Caching

```python
# Anthropic prompt caching: mark large stable system prompts with cache_control
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": large_system_context,  # e.g., codebase summary
                "cache_control": {"type": "ephemeral"},  # Cache for up to 5 min
            },
            {"type": "text", "text": task_specific_prompt},
        ]
    }
]
```

---

## 8. Key Libraries & Versions

```txt
crewai==0.80.0
crewai-tools==0.17.0
anthropic==0.40.0
boto3==1.35.91       # Already in Phase 1
langsmith==0.1.147   # Early integration for tracing
pydantic==2.10.4     # Already
```

---

## 9. Pitfalls

| Pitfall | Prevention |
|---------|-----------|
| CrewAI `kickoff()` blocks thread → SQS consumer stalls | Run crew in `ThreadPoolExecutor` with `max_workers=5` |
| Budget exceeded mid-crew → partial work in EFS | Write checkpoint to DynamoDB before each agent handoff |
| Bedrock model ID changes frequently | Store model ID in Secrets Manager, not hardcoded |
| CrewAI verbose logging floods CloudWatch | Set `verbose=False` in prod, use LangSmith for tracing instead |
| SQS message deleted before crew finishes → lost on crash | Only `delete_message` AFTER crew.kickoff() returns successfully |

---
*Phase: 02-orchestration-llm | Research: 2026-02-26*
