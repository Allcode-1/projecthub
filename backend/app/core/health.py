import socket
from urllib.parse import urlparse

from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import SessionLocal
from app.redis.client import get_redis


def liveness_payload() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
    }


def _check_database() -> dict:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return {
            "status": "down",
            "required": True,
            "error": type(exc).__name__,
        }

    return {"status": "ok", "required": True}


def _check_redis() -> dict:
    try:
        get_redis().ping()
    except RedisError as exc:
        return {
            "status": "down",
            "required": settings.readiness_require_redis,
            "error": type(exc).__name__,
        }

    return {"status": "ok", "required": settings.readiness_require_redis}


def _check_rabbitmq() -> dict:
    broker_url = urlparse(settings.celery_broker_url)
    host = broker_url.hostname
    port = broker_url.port or 5672

    if host is None:
        return {
            "status": "down",
            "required": settings.readiness_require_rabbitmq,
            "error": "InvalidBrokerUrl",
        }

    try:
        with socket.create_connection(
            (host, port), timeout=settings.healthcheck_timeout_seconds
        ):
            pass
    except OSError as exc:
        return {
            "status": "down",
            "required": settings.readiness_require_rabbitmq,
            "error": type(exc).__name__,
        }

    return {"status": "ok", "required": settings.readiness_require_rabbitmq}


def readiness_payload() -> tuple[dict, int]:
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
        "rabbitmq": _check_rabbitmq(),
    }

    is_ready = all(
        check["status"] == "ok"
        for check in checks.values()
        if check.get("required", False)
    )

    return (
        {
            "status": "ready" if is_ready else "not_ready",
            "service": settings.app_name,
            "checks": checks,
        },
        200 if is_ready else 503,
    )
