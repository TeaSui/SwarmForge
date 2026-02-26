# External Integrations

**Analysis Date:** 2026-02-26

## APIs & External Services

**Current repository state:**
- No executable integration code detected in this repo yet.
- Integration intent is documented in [`README.md`] and planning docs.

**Planned external services (documented, not implemented):**
- Anthropic Claude API - primary LLM provider
- AWS Bedrock - fallback LLM provider
- Jira - trigger and feedback channel
- GitHub - code/PR automation target
- Slack/Webhook endpoints - additional triggers

## Data Storage

**Current:**
- File-based documentation and planning state in `.planning/`

**Planned (not implemented in code yet):**
- AWS SQS + DLQ
- AWS DynamoDB
- AWS EFS
- AWS S3 (optional artifacts)

## Authentication & Identity

**Current:**
- No auth implementation files detected

**Planned:**
- Secrets via AWS Secrets Manager
- Service credentials for Jira/GitHub/LLM providers

## Monitoring & Observability

**Current:**
- No runtime observability implementation in repo

**Planned:**
- LangSmith tracing
- CloudWatch metrics and logs

## CI/CD & Deployment

**Current:**
- No CI workflow files detected under `.github/workflows/`
- No infra code directories with deployable stack definitions found in current checkout

**Planned:**
- AWS CDK-managed deployment flow (per planning docs)

## Environment Configuration

**Current:**
- Planning preferences in `.planning/config.json`
- Tool settings in `.claude/settings.json` and `.gemini/settings.json`

**Expected for implementation phase:**
- `.env` or secret-injected runtime variables for API keys and service endpoints

## Webhooks & Callbacks

**Current:**
- No webhook handler source files detected

**Planned:**
- Incoming: Jira/Slack/generic webhooks to FastAPI ingress
- Outgoing: Jira comments, Slack updates, GitHub PR status links

---
*Integration audit: 2026-02-26*
*Update when integration code is added*
