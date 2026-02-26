# SwarmForge

**Autonomous AI Swarm for Workflow Automation & Code Generation**

SwarmForge is a next-generation, Python-native workflow automation system powered by **CrewAI** multi-agent swarms. It transforms complex tasks (e.g., Jira ticket → code generation → review → test → PR creation) into autonomous, collaborative agent workflows using Claude API (primary) with Bedrock fallback.

Built from scratch to overcome limitations of rigid pipelines (e.g., Lambda timeouts, static orchestration), SwarmForge enables true "AI Engineer" behavior: agents self-delegate, critique, iterate, and deliver production-ready code with human-in-the-loop safety.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Features

- **Multi-Agent Swarm**: Coder, Reviewer, Tester, Security Expert, Documentation Writer – agents collaborate hierarchically or sequentially.
- **Primary LLM**: Anthropic Claude API (Claude 3.5/4 Sonnet) for speed & latest features.
- **Fallback LLM**: Amazon Bedrock (global.anthropic.claude-sonnet-4-6) for reliability & enterprise security.
- **Persistent Workspace**: EFS-mounted storage for long-running git repos, code indexing, and multi-step execution.
- **Streaming Response**: Real-time output to Jira/Slack/Webhook.
- **Budget & Safety Controls**: Token budget manager, human-in-the-loop approval for PRs/commits.
- **Observability**: LangSmith tracing, CloudWatch metrics, detailed agent logs.

## Architecture

```mermaid
graph TD
    subgraph "Client Layer"
        A[Jira / Slack / Webhook] -->|Trigger Task| B[FastAPI Ingress]
    end

    subgraph "API & Orchestration (Python)"
        B[FastAPI Service<br>(ECS Fargate / Lambda)] -->|Validate + Intent| C[CrewAI Orchestrator<br>(Flows / Crews)]
        B -->|Quick Ack| Z[Streaming Response]
    end

    subgraph "Agent Swarm (CrewAI)"
        C --> D[Agent Pool]
        D --> E[Coder Agent]
        D --> F[Reviewer Agent]
        D --> G[Tester Agent]
        D --> H[Security Agent]
        D --> I[Doc Agent]
        D --> J[Orchestrator Agent<br>(Delegate + Decide)]
        J --> K[Budget Manager<br>(Token Limit + Kill)]
        J --> L[Human-in-the-Loop<br>(Approve PR/Commit)]
    end

    subgraph "Tools & Execution"
        E --> M[Tools: GitHub API, Shell, File Ops, Code Execution]
        F --> M
        G --> M
        H --> M
        I --> M
        M --> N[Sidecar Runners<br>(Ephemeral ECS Tasks for heavy build/test)]
    end

    subgraph "LLM Layer"
        M --> O[Primary: Claude API<br>(anthropic.com)]
        O -->|Fallback (rate limit / error)| P[Bedrock Fallback<br>(global.anthropic.claude-sonnet-4-6)]
        O --> Q[Prompt Caching<br>(Reduce repeated tokens)]
    end

    subgraph "Persistence & State"
        C --> R[DynamoDB / Redis<br>(Task State, Agent Memory)]
        C --> S[EFS / S3<br>(Persistent Code Workspace)]
        C --> T[Temporal.io (optional)<br>(Durable Execution, Checkpoint)]
    end

    subgraph "Observability & Output"
        C --> U[LangSmith / CloudWatch<br>(Tracing, Metrics, Logs)]
        C --> V[Stream to Jira/Slack/Webhook]
        V --> A
    end

    subgraph "Infra (AWS)"
        B --> W[ECS Fargate<br>(Long-running Swarm)]
        W --> X[SQS + DLQ<br>(Task Queue, Retry)]
        W --> Y[Secrets Manager<br>(API Keys)]
    end

    style C fill:#f9f,stroke:#333,stroke-width:2px
    style O fill:#bbf,stroke:#333
    style P fill:#ddf,stroke:#333
    style L fill:#ff9,stroke:#333
```

Tech Stack

Core Framework: CrewAI (multi-agent orchestration)
Language: Python 3.11+
LLM: Anthropic Claude API (primary) + AWS Bedrock (fallback)
API Layer: FastAPI
Runtime: AWS ECS Fargate (long-running) + SQS (queue)
Storage: EFS (persistent workspace) + S3 + DynamoDB
Observability: LangSmith (agent tracing), CloudWatch
Optional: Temporal.io (durable workflows)

Getting Started

Clone the repo:

```bash
git clone https://github.com/yourusername/swarmforge.git
cd swarmforge
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Set environment variables (.env file):

```bash
ANTHROPIC_API_KEY=sk-...
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-6
GITHUB_TOKEN=ghp_...
JIRA_API_TOKEN=...
```

Run locally (dev mode):

```bash
uvicorn main:app --reload
Deploy to AWS (ECS Fargate):
Use provided CDK stack (in /infra)
cd infra && cdk deploy
```
