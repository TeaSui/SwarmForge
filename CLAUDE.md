# SwarmForge

AI-driven task automation platform that receives webhooks (Jira, Slack, generic), queues work via SQS, and executes tasks using LLM-powered agents.

## Stack

- **Language**: Python 3.12+ (target 3.13 in Docker)
- **Framework**: FastAPI (ingress API) + SQS consumer (worker)
- **AI**: CrewAI + LangChain + Anthropic Claude (Bedrock in prod, direct API locally)
- **Infrastructure**: AWS CDK — ECS Fargate, SQS, DynamoDB, Secrets Manager, CloudWatch
- **Config**: pydantic-settings with `.env` file, lazy-loaded singleton (`config.settings`)

## Project Structure

```
main.py              — FastAPI app entrypoint
worker.py            — SQS consumer entrypoint
config.py            — Settings (pydantic-settings, AWS Secrets Manager)
api/webhooks/        — Jira, Slack, Generic webhook routers
api/health.py        — Health check endpoint
models/              — Pydantic models (webhook payloads, SQS messages)
services/            — Business logic (orchestrator, agents, LLM, SQS, budget, quality gates)
services/executor/   — Task execution engine
tests/               — pytest test suite
scripts/             — Operational scripts (SLA monitor, health checks)
infrastructure/      — AWS CDK stack
```

## Development Commands

```bash
# Run API locally
uvicorn main:app --reload --port 8000

# Run tests
./venv/bin/python -m pytest tests/ -v --tb=short

# Run tests with coverage
./venv/bin/python -m pytest tests/ --cov=services --cov=api --cov=models --cov-report=term-missing --tb=short

# Lint
./venv/bin/ruff check .

# Install dependencies
./venv/bin/pip install -r requirements.txt
```

## Testing

- Framework: pytest with `asyncio_mode = auto`
- Coverage threshold: 80% (services, api, models)
- Use `APP_ENV=test` to skip AWS Secrets Manager loading
- Mock external dependencies (boto3, anthropic, requests)
- Test files: `tests/test_*.py`, fixtures in `tests/conftest.py`

## Key Patterns

- **Config**: `from config import settings` — lazy proxy, no import-time AWS calls
- **Webhook flow**: webhook endpoint -> validate -> SQS publish -> consumer polls -> orchestrator -> agents
- **Idempotency**: DynamoDB-backed deduplication for webhook events
- **Budget**: Token + USD soft/hard limits per task execution
- **Quality gates**: Automated validation before agent output is committed
- **Approval gate**: Human-in-the-loop approval for high-risk changes

## Environment

- Virtual env at `./venv/`
- Config via `.env` file (see `.env.example`)
- Never commit `.env`, API keys, or credentials
