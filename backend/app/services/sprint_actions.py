from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.cache.sprint import SprintCache
from app.core.errors import AppError
from app.models.project import Project
from app.models.sprint import Sprint, SprintStatus
from app.models.user import User
from app.repositories.sprint import SprintRepository
from app.schemas.sprint import SprintCreate, SprintUpdate
from app.services.project_membership import can_manage_sprints


def _ensure_sprint_dates(starts_at: datetime | None, ends_at: datetime | None) -> None:
    if starts_at is not None and ends_at is not None and ends_at <= starts_at:
        raise AppError(422, "Sprint end must be after start")


def create_sprint(
    payload: SprintCreate,
    project: Project,
    user: User,
    db: Session,
    sprint_cache: SprintCache,
) -> Sprint:

    sprint_repo = SprintRepository(db)

    starts_at = payload.starts_at or datetime.now(UTC)
    ends_at = starts_at + timedelta(days=14)
    _ensure_sprint_dates(starts_at, ends_at)

    sprint = sprint_repo.create(
        project_id=project.id,
        creator_id=user.id,
        name=payload.name,
        description=payload.description,
        starts_at=starts_at,
        ends_at=ends_at,
    )

    db.commit()
    db.refresh(sprint)

    sprint_cache.invalidate_project_sprints(project.id)

    return sprint


def update_sprint(
    payload: SprintUpdate,
    project: Project,
    sprint: Sprint,
    user: User,
    db: Session,
    sprint_cache: SprintCache,
) -> Sprint:

    if not can_manage_sprints(db, user, project):
        raise AppError(403, "Not enough rights")

    if sprint.status == SprintStatus.CLOSED:
        raise AppError(409, "Closed sprint cannot be updated")

    updated_fields = payload.model_dump(exclude_unset=True)

    next_starts_at = updated_fields.get("starts_at", sprint.starts_at)
    next_ends_at = updated_fields.get("ends_at", sprint.ends_at)
    _ensure_sprint_dates(next_starts_at, next_ends_at)

    for field, value in updated_fields.items():
        setattr(sprint, field, value)

    db.commit()
    db.refresh(sprint)

    sprint_cache.invalidate_project_sprints(project.id)

    return sprint


def delete_sprint(
    project: Project, sprint: Sprint, user: User, db: Session, sprint_cache: SprintCache
) -> None:

    if not can_manage_sprints(db, user, project):
        raise AppError(403, "Not enough rights")

    db.delete(sprint)
    db.commit()

    sprint_cache.invalidate_project_sprints(project.id)


def start_sprint(
    project: Project, sprint: Sprint, user: User, db: Session, sprint_cache: SprintCache
) -> Sprint:

    if not can_manage_sprints(db, user, project):
        raise AppError(403, "Not enough rights")

    if sprint.status != SprintStatus.PLANNED:
        raise AppError(409, "Only planned sprint can be started")

    now = datetime.now(UTC)

    if sprint.ends_at is not None and sprint.ends_at <= now:
        raise AppError(409, "Sprint already ended")

    sprint.starts_at = now
    sprint.status = SprintStatus.ACTIVE

    db.commit()
    db.refresh(sprint)

    sprint_cache.invalidate_project_sprints(project.id)

    return sprint


def close_sprint(
    project: Project, sprint: Sprint, user: User, db: Session, sprint_cache: SprintCache
) -> Sprint:

    if not can_manage_sprints(db, user, project):
        raise AppError(403, "Not enough rights")

    if sprint.status != SprintStatus.ACTIVE:
        raise AppError(409, "Only active sprint can be closed")

    now = datetime.now(UTC)

    sprint.closed_at = now
    sprint.status = SprintStatus.CLOSED

    db.commit()
    db.refresh(sprint)

    sprint_cache.invalidate_project_sprints(project.id)

    return sprint
