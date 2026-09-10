from fastapi import HTTPException, status
from redis import Redis


class RateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis

    def check(self, key: str, limit: int, window_seconds: int) -> None:

        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        count, current_ttl = pipe.execute()

        if current_ttl == -1:
            self.redis.expire(key, window_seconds)
            current_ttl = window_seconds

        if count > limit:
            retry_after = current_ttl if current_ttl > 0 else window_seconds
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
                headers={"Retry-After": str(retry_after)},
            )
            # raise AppError(status_code=409, detail="Too many requests")
