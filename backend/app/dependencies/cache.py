from typing import Annotated

from fastapi import Depends
from redis import Redis

from app.cache.base import RedisCache
from app.cache.project import ProjectCache
from app.cache.sprint import SprintCache
from app.redis.client import get_redis

RedisDep = Annotated[Redis, Depends(get_redis)]


def get_cache(redis: RedisDep) -> RedisCache:
    return RedisCache(redis)


RedisCacheDep = Annotated[RedisCache, Depends(get_cache)]


def get_project_cache(cache: RedisCacheDep) -> ProjectCache:
    return ProjectCache(cache)


def get_sprint_cache(cache: RedisCacheDep) -> SprintCache:
    return SprintCache(cache)
