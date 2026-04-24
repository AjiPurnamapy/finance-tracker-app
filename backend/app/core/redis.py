"""
Redis connection pool and helper utilities.

Provides a lazy-initialized async Redis client used by:
- Rate limiting middleware (Phase 7)
- Future: session caching, pub/sub, background task queuing

Design: lazy singleton — Redis is NOT required to start the app.
If Redis is unreachable, rate limiting degrades gracefully (fail-open).
"""

import structlog
import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import get_settings

log = structlog.get_logger(__name__)

_redis_client: Redis | None = None


async def get_redis() -> Redis | None:
    """
    Lazily initialize and return the Redis async client.
    Returns None if Redis is unavailable (fail-open design).
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    settings = get_settings()
    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,   # fast timeout — don't block startup
            socket_timeout=2,
        )
        # Verify connection
        await client.ping()
        _redis_client = client
        log.info("redis_connected", url=settings.REDIS_URL)
        return _redis_client
    except (RedisError, OSError, ConnectionRefusedError) as exc:
        log.warning("redis_unavailable", error=str(exc), detail="Rate limiting will be disabled")
        return None


async def close_redis() -> None:
    """Close the Redis connection pool on shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        log.info("redis_disconnected")


async def check_redis_connection() -> bool:
    """Health check — returns True if Redis is reachable."""
    try:
        client = await get_redis()
        if client is None:
            return False
        await client.ping()
        return True
    except (RedisError, OSError):
        return False
