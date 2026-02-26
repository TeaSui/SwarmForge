# Phase 5: Deployment & Observability — Research

**Phase:** 5 — Deployment & Observability
**Researched:** 2026-02-26
**Goal:** Full production deployment via CDK (ECS Fargate, EFS, SQS, DynamoDB, Secrets Manager); LangSmith tracing; CloudWatch metrics.

## RESEARCH COMPLETE

---

## 1. AWS CDK Infrastructure

### Core Resources
- **VPC:** Shared VPC or new dedicated VPC with private subnets for ECS tasks.
- **ECS Cluster:** Fargate-based cluster for long-running agent swarms.
- **EFS File System:** Mounted at `/mnt/efs/workspace` in ECS tasks for persistent workspace sharing.
- **SQS + DLQ:** Task queue with a Dead Letter Queue for failed message handling.
- **DynamoDB Tables:** `swarmforge-tasks` (task state) and `swarmforge-idempotency` (dedup).
- **Secrets Manager:** Secure storage for `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `JIRA_API_TOKEN`, and `LANGSMITH_API_KEY`.

### Integration
- ECS tasks will use IAM Task Roles for secure access to SQS, DynamoDB, EFS, and Secrets Manager.

---

## 2. Docker & ECS Task Configuration

- **Base Image:** `python:3.11-slim`.
- **Dependencies:** Install all requirements from Phase 1-4.
- **Environment:**
  - `OTEL_SDK_DISABLED=true` (if not using OpenTelemetry).
  - `CONFIG_SOURCE=secrets_manager` (signal to load settings from AWS).
- **EFS Mount:** Use `EfsVolumeConfiguration` in the Task Definition.

---

## 3. Observability

### LangSmith Tracing
- **Initialization:**
  ```python
  from langsmith import Client
  client = Client()
  # Use LangChain/CrewAI native integration for tracing
  ```
- **Tracing:** Capture every agent step, tool call, and LLM interaction.

### CloudWatch Metrics & Dashboards
- **Metrics:** `TaskExecutionCount`, `TaskSuccessRate`, `LlmTokenUsage`, `TaskDuration`.
- **Alarms:** Alert on high DLQ message count or consistent failure rates.

---

*Phase: 05-deployment-observability | Research: 2026-02-26*
