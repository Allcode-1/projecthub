from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.db.session import get_db
from app.dependencies.project import require_can_manage_sprints, require_can_take_tasks
from app.dependencies.rate_limiter import rate_limit_authenticated_mutation
from app.dependencies.sprint import get_sprint_by_id_or_404
from app.dependencies.task import get_task_by_id_or_404
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.task import Task
from app.models.user import User
from app.schemas.review_comments import ReviewCommentCreate
from app.schemas.task import TaskRead
from app.services.task_actions import (
    accept_task_review,
    decline_task_review,
    renew_task,
    send_task_to_review,
    take_task_to_work,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
ManageSprintsProject = Annotated[Project, Depends(require_can_manage_sprints)]
TakeTasksProject = Annotated[Project, Depends(require_can_take_tasks)]
CurrentSprint = Annotated[Sprint, Depends(get_sprint_by_id_or_404)]
CurrentTask = Annotated[Task, Depends(get_task_by_id_or_404)]


@router.patch(
    "/{task_id}/take_task",
    response_model=TaskRead,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def take_task_to_work_router(
    project: TakeTasksProject,
    sprint: CurrentSprint,
    task: CurrentTask,
    user: CurrentUser,
    db: DbSession,
):

    return take_task_to_work(sprint, task, user, db)


@router.patch(
    "/{task_id}/to_review",
    response_model=TaskRead,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def send_task_to_review_router(
    project: TakeTasksProject,
    sprint: CurrentSprint,
    task: CurrentTask,
    user: CurrentUser,
    db: DbSession,
):

    return send_task_to_review(sprint, task, user, db)


@router.patch(
    "/{task_id}/accept",
    response_model=TaskRead,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def accept_task_review_router(
    project: ManageSprintsProject,
    sprint: CurrentSprint,
    task: CurrentTask,
    user: CurrentUser,
    db: DbSession,
):

    return accept_task_review(sprint, task, user, db)


@router.patch(
    "/{task_id}/decline",
    response_model=TaskRead,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def decline_task_review_router(
    project: ManageSprintsProject,
    sprint: CurrentSprint,
    task: CurrentTask,
    user: CurrentUser,
    db: DbSession,
    payload: ReviewCommentCreate | None = None,
):

    return decline_task_review(payload, sprint, task, user, db)


@router.patch(
    "/{task_id}/renew",
    response_model=TaskRead,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def renew_task_router(
    project: TakeTasksProject,
    sprint: CurrentSprint,
    task: CurrentTask,
    user: CurrentUser,
    db: DbSession,
):

    return renew_task(sprint, task, user, db)
