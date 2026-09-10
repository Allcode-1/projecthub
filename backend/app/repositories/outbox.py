from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.outbox_event import OutboxEvent


class OutboxRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_event(self, event_type: str, payload: dict[str, Any]) -> OutboxEvent:
        event = OutboxEvent(event_type=event_type, payload=payload)
        self.db.add(event)
        return event

    def pending_events(self, limit: int) -> list[OutboxEvent]:
        statement = (
            select(OutboxEvent)
            .where(OutboxEvent.sent.is_(False))
            .order_by(OutboxEvent.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(self.db.scalars(statement).all())

    @staticmethod
    def mark_sent(event: OutboxEvent) -> None:
        event.sent = True
