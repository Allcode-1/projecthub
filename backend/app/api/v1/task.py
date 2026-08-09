from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.db.session import get_db
from app.dependencies.pagination import Pagination, get_pagination
from app.dependencies.project import (
    require_can_manage_sprints,
    require_can_take_tasks,
    require_can_view_project,
)
from app.dependencies.rate_limiter import rate_limit_authenticated_mutation
from app.dependencies.sprint import get_sprint_by_id_or_404
from app.dependencies.task import get_task_by_id_or_404
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.task import Task
from app.models.user import User
from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.task_actions import add_task, delete_task, update_task

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
ViewProject = Annotated[Project, Depends(require_can_view_project)]
ManageSprintsProject = Annotated[Project, Depends(require_can_manage_sprints)]
TakeTasksProject = Annotated[Project, Depends(require_can_take_tasks)]
CurrentSprint = Annotated[Sprint, Depends(get_sprint_by_id_or_404)]
CurrentTask = Annotated[Task, Depends(get_task_by_id_or_404)]
PaginationDep = Annotated[Pagination, Depends(get_pagination)]


@router.post(
    "/",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def add_task_router(
    payload: TaskCreate,
    project: ManageSprintsProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
):

    return add_task(payload, project, sprint, user, db)


@router.get("/", response_model=list[TaskRead])
def get_tasks_router(
    project: ViewProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
):

    task_repo = TaskRepository(db)
    tasks = task_repo.all_tasks_of_sprint(
        project.id, sprint.id, pagination.limit, pagination.offset
    )
    return tasks


@router.get("/todo", response_model=list[TaskRead])
def get_tasks_todo(
    project: ViewProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
):

    task_repo = TaskRepository(db)
    tasks = task_repo.tasks_todo(
        project.id, sprint.id, pagination.limit, pagination.offset
    )
    return tasks


@router.get("/in_progress", response_model=list[TaskRead])
def get_tasks_in_progress(
    project: ViewProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
):

    task_repo = TaskRepository(db)
    tasks = task_repo.tasks_in_progress(
        project.id, sprint.id, pagination.limit, pagination.offset
    )
    return tasks


@router.get("/on_review", response_model=list[TaskRead])
def get_tasks_on_review(
    project: ViewProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
):

    task_repo = TaskRepository(db)
    tasks = task_repo.tasks_on_review(
        project.id, sprint.id, pagination.limit, pagination.offset
    )
    return tasks


@router.get("/done", response_model=list[TaskRead])
def get_tasks_done(
    project: ViewProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
):

    task_repo = TaskRepository(db)
    tasks = task_repo.tasks_done(
        project.id, sprint.id, pagination.limit, pagination.offset
    )
    return tasks


@router.get("/rejected", response_model=list[TaskRead])
def get_tasks_rejected(
    project: ViewProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
):

    task_repo = TaskRepository(db)
    tasks = task_repo.tasks_rejected(
        project.id, sprint.id, pagination.limit, pagination.offset
    )
    return tasks


@router.get("/mine", response_model=list[TaskRead])
def get_my_created_tasks(
    project: ManageSprintsProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
):

    task_repo = TaskRepository(db)
    tasks = task_repo.tasks_created_by_user(
        project.id, sprint.id, user.id, pagination.limit, pagination.offset
    )
    return tasks


@router.get("/my_workspace", response_model=list[TaskRead])
def get_my_workspace_tasks(
    project: TakeTasksProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
):

    task_repo = TaskRepository(db)
    tasks = task_repo.tasks_assigned_to_user(
        project.id, sprint.id, user.id, pagination.limit, pagination.offset
    )
    return tasks


@router.get("/{task_id}", response_model=TaskRead)
def get_task_router(
    project: ViewProject,
    sprint: CurrentSprint,
    task: CurrentTask,
    user: CurrentUser,
    db: DbSession,
):

    return task


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def delete_task_router(
    project: ManageSprintsProject,
    sprint: CurrentSprint,
    task: CurrentTask,
    user: CurrentUser,
    db: DbSession,
):

    return delete_task(project, sprint, task, user, db)


@router.patch(
    "/{task_id}",
    response_model=TaskRead,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def update_task_router(
    payload: TaskUpdate,
    project: ManageSprintsProject,
    sprint: CurrentSprint,
    task: CurrentTask,
    user: CurrentUser,
    db: DbSession,
):

    return update_task(payload, project, sprint, task, user, db)
