import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request

from app.core.logging import reset_request_id, set_request_id

logger = logging.getLogger("app.http")


def register_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        token = set_request_id(request_id)
        started_at = perf_counter()

        client_ip = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "HTTP request failed",
                extra={
                    "event": "http_request_failed",
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": client_ip,
                    "duration_ms": duration_ms,
                },
            )
            reset_request_id(token)
            raise

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "HTTP request completed",
            extra={
                "event": "http_request_completed",
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        reset_request_id(token)
        return response
