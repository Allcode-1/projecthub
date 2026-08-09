import json
import logging
import random
from collections.abc import Iterable
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self, redis: Redis, prefix: str = "project-hub:v1"):
        self.redis = redis
        self.prefix = prefix

    def key(self, *parts: object) -> str:
        return ":".join([self.prefix, *(str(part) for part in parts)])

    def get_json(self, key: str) -> Any | None:

        try:
            raw = self.redis.get(key)
        except RedisError:
            logger.warning("Redis cache get failed", exc_info=True)
            return None

        if raw is None:
            return None

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            self.delete(key)
            return None

    def set_json(
        self, key: str, value: Any, ttl_seconds: int, jitter_seconds: int = 0
    ) -> None:

        ttl = ttl_seconds + random.randint(0, jitter_seconds)

        try:
            self.redis.set(
                key,
                json.dumps(value, separators=(",", ":"), ensure_ascii=False),
                ex=ttl,
            )
        except RedisError:
            logger.warning("Redis cache set failed", exc_info=True)

    def delete(self, key: str) -> None:

        try:
            self.redis.delete(key)
        except RedisError:
            logger.warning("Redis cache delete failed", exc_info=True)

    def delete_many(self, keys: Iterable[str]) -> None:

        keys = list(keys)

        if not keys:
            return

        try:
            self.redis.delete(*keys)
        except RedisError:
            logger.warning("Redis cache delete_many failed", exc_info=True)

    def delete_pattern(self, pattern: str) -> None:
        try:
            keys = list(self.redis.scan_iter(match=pattern))
        except RedisError:
            logger.warning("Redis cache scan failed", exc_info=True)
            return

        self.delete_many(keys)
