import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import or_, update
from sqlalchemy.orm import Session

from app.cache.base import RedisCache
from app.cache.sprint import SprintCache
from app.db.session import SessionLocal
from app.jobs.celery_app import celery_app
from app.models.sprint import Sprint, SprintStatus
from app.redis.client import get_redis

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SprintLifecycleResult:
    started: int
    closed: int
    project_ids: frozenset[int]


def synchronize_sprint_lifecycle(
    db: Session,
    now: datetime,
) -> SprintLifecycleResult:

    closed_planned_project_ids = list(
        db.scalars(
            update(Sprint)
            .where(
                Sprint.status == SprintStatus.PLANNED,
                Sprint.ends_at.is_not(None),
                Sprint.ends_at <= now,
            )
            .values(
                status=SprintStatus.CLOSED,
                closed_at=now,
            )
            .returning(Sprint.project_id)
        ).all()
    )

    restarted_project_ids = list(
        db.scalars(
            update(Sprint)
            .where(
                Sprint.status == SprintStatus.ACTIVE,
                Sprint.ends_at.is_not(None),
                Sprint.ends_at <= now,
            )
            .values(
                status=SprintStatus.CLOSED,
                closed_at=now,
            )
            .returning(Sprint.project_id)
        ).all()
    )

    started_project_ids = list(
        db.scalars(
            update(Sprint)
            .where(
                Sprint.status == SprintStatus.PLANNED,
                Sprint.starts_at.is_not(None),
                Sprint.starts_at <= now,
                or_(
                    Sprint.ends_at.is_(None),
                    Sprint.ends_at > now,
                ),
            )
            .values(status=SprintStatus.ACTIVE)
            .returning(Sprint.project_id)
        ).all()
    )

    return SprintLifecycleResult(
        started=len(started_project_ids),
        closed=len(closed_planned_project_ids + restarted_project_ids),
        project_ids=frozenset(
            started_project_ids + restarted_project_ids + closed_planned_project_ids
        ),
    )


@celery_app.task(name="project_hub.sprints.sync_lifecycle")
def sync_sprint_lifecycle() -> None:
    now = datetime.now(UTC)

    with SessionLocal.begin() as db:
        result = synchronize_sprint_lifecycle(db, now)

    if result.project_ids:
        sprint_cache = SprintCache(RedisCache(get_redis()))
        sprint_cache.invalidate_projects_sprints(result.project_ids)

    logger.info(
        "Sprint lifecycle synchronized: started=%s closed=%s",
        result.started,
        result.closed,
    )
