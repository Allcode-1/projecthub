import logging
from typing import Any

from celery import Celery
from celery.signals import task_failure, task_postrun, task_prerun

from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger("app.celery")


celery_app = Celery(
    "project_hub",
    broker=settings.celery_broker_url,
    include=[
        "app.jobs.demo",
        "app.jobs.sprint_lifecycle",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    worker_enable_remote_control=False,
    beat_schedule={
        "sync-sprint-lifecycle-every-minute": {
            "task": "project_hub.sprints.sync_lifecycle",
            "schedule": 60.0,
            "options": {"expires": 55},
        },
    },
)


@task_prerun.connect
def log_task_started(sender: Any = None, task_id: str | None = None, **_: Any) -> None:
    logger.info(
        "Celery task started",
        extra={
            "event": "celery_task_started",
            "task_name": getattr(sender, "name", None),
            "task_id": task_id,
        },
    )


@task_postrun.connect
def log_task_finished(
    sender: Any = None,
    task_id: str | None = None,
    state: str | None = None,
    **_: Any,
) -> None:
    logger.info(
        "Celery task finished",
        extra={
            "event": "celery_task_finished",
            "task_name": getattr(sender, "name", None),
            "task_id": task_id,
            "state": state,
        },
    )


@task_failure.connect
def log_task_failed(
    sender: Any = None,
    task_id: str | None = None,
    exception: BaseException | None = None,
    traceback: Any = None,
    **_: Any,
) -> None:
    exc_info = None
    if exception is not None:
        exc_info = (type(exception), exception, traceback)

    logger.error(
        "Celery task failed",
        extra={
            "event": "celery_task_failed",
            "task_name": getattr(sender, "name", None),
            "task_id": task_id,
            "exception_type": type(exception).__name__ if exception else None,
        },
        exc_info=exc_info,
    )
