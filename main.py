from fastapi import FastAPI

from api.webhooks.jira import router as jira_router
from api.webhooks.slack import router as slack_router
from api.webhooks.generic import router as generic_router
from api.health import router as health_router
from config import settings
from services.logging_setup import configure_logging
from services.rate_limiter import RateLimitMiddleware, SlidingWindowRateLimiter

configure_logging("api", settings.CLOUDWATCH_LOG_GROUP_API)

app = FastAPI(
    title="SwarmForge Ingress",
    description="FastAPI ingress for Jira, Slack, and Generic webhooks",
    version="0.1.0"
)

_limiter = SlidingWindowRateLimiter(max_requests=settings.RATE_LIMIT_PER_MINUTE)
app.add_middleware(RateLimitMiddleware, limiter=_limiter)

# Include routers
app.include_router(jira_router, prefix="/webhook", tags=["webhooks"])
app.include_router(slack_router, prefix="/webhook", tags=["webhooks"])
app.include_router(generic_router, prefix="/webhook", tags=["webhooks"])
app.include_router(health_router, tags=["monitoring"])

@app.get("/")
async def root():
    return {"message": "SwarmForge Ingress API is running", "version": "0.1.0"}
