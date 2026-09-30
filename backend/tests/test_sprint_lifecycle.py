from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.jobs.celery_app import celery_app
from app.jobs.sprint_lifecycle import synchronize_sprint_lifecycle
from app.models.project import Project
from app.models.sprint import Sprint, SprintStatus
from app.models.user import User


def _get_sprint(db: Session, sprint_id: int) -> Sprint:
    sprint = db.get(Sprint, sprint_id)
    assert sprint is not None
    return sprint


def test_synchronize_sprint_lifecycle_is_idempotent(
    db_session: Session,
):
    now = datetime(2035, 1, 15, 12, tzinfo=UTC)

    owner = User(
        username="lifecycle-owner",
        email="lifecycle-owner@example.com",
        hashed_password="not-used",
    )
    db_session.add(owner)
    db_session.flush()

    project = Project(
        owner_id=owner.id,
        name="Lifecycle project",
        description=None,
    )
    db_session.add(project)
    db_session.flush()

    due_to_start = Sprint(
        project_id=project.id,
        creator_id=owner.id,
        name="Due to start",
        status=SprintStatus.PLANNED,
        starts_at=now - timedelta(minutes=1),
        ends_at=now + timedelta(days=1),
    )
    another_due_to_start = Sprint(
        project_id=project.id,
        creator_id=owner.id,
        name="Another due to start",
        status=SprintStatus.PLANNED,
        starts_at=now - timedelta(minutes=2),
        ends_at=now + timedelta(days=2),
    )
    due_to_close = Sprint(
        project_id=project.id,
        creator_id=owner.id,
        name="Due to close",
        status=SprintStatus.ACTIVE,
        starts_at=now - timedelta(days=1),
        ends_at=now - timedelta(minutes=1),
    )
    missed_window = Sprint(
        project_id=project.id,
        creator_id=owner.id,
        name="Missed window",
        status=SprintStatus.PLANNED,
        starts_at=now - timedelta(days=2),
        ends_at=now - timedelta(days=1),
    )
    future_sprint = Sprint(
        project_id=project.id,
        creator_id=owner.id,
        name="Future sprint",
        status=SprintStatus.PLANNED,
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=15),
    )
    already_closed_at = now - timedelta(days=2)
    already_closed = Sprint(
        project_id=project.id,
        creator_id=owner.id,
        name="Already closed",
        status=SprintStatus.CLOSED,
        starts_at=now - timedelta(days=4),
        ends_at=now - timedelta(days=3),
        closed_at=already_closed_at,
    )

    db_session.add_all(
        [
            due_to_start,
            another_due_to_start,
            due_to_close,
            missed_window,
            future_sprint,
            already_closed,
        ]
    )
    db_session.flush()

    first_result = synchronize_sprint_lifecycle(db_session, now)
    db_session.expire_all()

    assert first_result.started == 2
    assert first_result.closed == 2
    assert first_result.project_ids == frozenset({project.id})

    assert _get_sprint(db_session, due_to_start.id).status == SprintStatus.ACTIVE
    assert (
        _get_sprint(db_session, another_due_to_start.id).status == SprintStatus.ACTIVE
    )

    closed_sprint = _get_sprint(db_session, due_to_close.id)
    assert closed_sprint.status == SprintStatus.CLOSED
    assert closed_sprint.closed_at == now

    expired_planned_sprint = _get_sprint(db_session, missed_window.id)
    assert expired_planned_sprint.status == SprintStatus.CLOSED
    assert expired_planned_sprint.closed_at == now

    assert _get_sprint(db_session, future_sprint.id).status == SprintStatus.PLANNED

    unchanged_closed_sprint = _get_sprint(db_session, already_closed.id)
    assert unchanged_closed_sprint.status == SprintStatus.CLOSED
    assert unchanged_closed_sprint.closed_at == already_closed_at

    second_result = synchronize_sprint_lifecycle(db_session, now)

    assert second_result.started == 0
    assert second_result.closed == 0
    assert second_result.project_ids == frozenset()


def test_celery_schedules_sprint_lifecycle_every_minute():
    schedule = celery_app.conf.beat_schedule["sync-sprint-lifecycle-every-minute"]

    assert schedule["task"] == "project_hub.sprints.sync_lifecycle"
    assert schedule["schedule"] == 60.0
    assert schedule["options"] == {"expires": 55}
