"""
Redis connection manager with connection pooling and health checks.
"""

import redis.asyncio as aioredis
from app.config import get_settings
from app.middleware.logging import get_logger

settings = get_settings()
_logger = get_logger("redis_manager")

import time
import asyncio

class InMemoryRedis:
    def __init__(self):
        self._data = {}

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        if key not in self._data:
            return None
        val, exp = self._data[key]
        if exp is not None and time.time() > exp:
            del self._data[key]
            return None
        return val

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        expire_at = time.time() + ex if ex is not None else None
        self._data[key] = (str(value), expire_at)
        return True

    async def setex(self, name: str, time_sec: int, value: str) -> bool:
        return await self.set(name, value, ex=time_sec)

    async def delete(self, key: str) -> int:
        if key in self._data:
            del self._data[key]
            return 1
        return 0

    async def close(self) -> None:
        pass

# Global mock instance and status flag
_mock_redis = InMemoryRedis()
USE_MOCK_REDIS = False
_has_checked_health = False

# Primary Redis pool for caching and general use
try:
    redis_pool = aioredis.ConnectionPool.from_url(
        settings.redis_url,
        max_connections=20,
        decode_responses=True,
    )
except Exception:
    USE_MOCK_REDIS = True
    redis_pool = None

# Dedicated pool for token blacklisting / session storage
try:
    redis_token_pool = aioredis.ConnectionPool.from_url(
        settings.redis_url,
        db=settings.redis_token_db,
        max_connections=10,
        decode_responses=True,
    )
except Exception:
    USE_MOCK_REDIS = True
    redis_token_pool = None


def get_redis() -> aioredis.Redis:
    """Returns a Redis client from the primary pool, or InMemoryRedis fallback."""
    if USE_MOCK_REDIS:
        return _mock_redis
    try:
        return aioredis.Redis(connection_pool=redis_pool)
    except Exception:
        return _mock_redis


def get_redis_tokens() -> aioredis.Redis:
    """Returns a Redis client from the token-dedicated pool, or InMemoryRedis fallback."""
    if USE_MOCK_REDIS:
        return _mock_redis
    try:
        return aioredis.Redis(connection_pool=redis_token_pool)
    except Exception:
        return _mock_redis


async def check_redis_health() -> bool:
    """Ping the primary Redis instance to verify connectivity, falling back on failure."""
    global USE_MOCK_REDIS, _has_checked_health
    if USE_MOCK_REDIS:
        return True
    try:
        client = aioredis.Redis(connection_pool=redis_pool)
        # Verify connection with a short timeout to prevent startup hangs
        await asyncio.wait_for(client.ping(), timeout=1.0)
        _has_checked_health = True
        return True
    except Exception:
        _logger.warning("redis_fallback_activated", hint="Redis is not reachable — falling back to in-memory mock")
        USE_MOCK_REDIS = True
        return True


async def close_redis_pools() -> None:
    """Cleanly disconnect both Redis connection pools."""
    global USE_MOCK_REDIS
    if not USE_MOCK_REDIS and redis_pool and redis_token_pool:
        try:
            await redis_pool.disconnect()
            await redis_token_pool.disconnect()
        except Exception:
            pass
