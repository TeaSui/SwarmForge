"""Backwards-compatible alias for the consolidated idempotency module."""
from __future__ import annotations

from services.idempotency import IdempotencyStore

# Re-export for backwards compatibility with tests
DynamoDBDeduplicator = IdempotencyStore
