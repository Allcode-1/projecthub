import logging
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.jobs.celery_app import celery_app
from app.jobs.email import send_email
from app.models.outbox_event import OutboxEvent
from app.repositories.outbox import OutboxRepository

logger = logging.getLogger(__name__)


def _publish_event(event: OutboxEvent) -> None:
    if event.event_type != "user.registered":
        raise ValueError(f"Unsupported outbox event type: {event.event_type}")

    payload: dict[str, Any] = event.payload
    send_email.delay(  # pyright: ignore
        payload["email"],
        "Welcome!",
        "welcome.html",
        {"username": payload["username"]},
    )


def dispatch_pending_events(db: Session, limit: int = 100) -> int:
    outbox_repo = OutboxRepository(db)
    events = outbox_repo.pending_events(limit)

    for event in events:
        _publish_event(event)
        outbox_repo.mark_sent(event)

    return len(events)


@celery_app.task(name="project_hub.outbox.dispatch")
def dispatch_outbox_events() -> None:
    with SessionLocal.begin() as db:
        dispatched_events = dispatch_pending_events(db)

    logger.info("Outbox events dispatched: %s", dispatched_events)
