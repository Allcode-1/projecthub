from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.cache.sprint import SprintCache
from app.db.session import get_db
from app.dependencies.cache import get_sprint_cache
from app.dependencies.pagination import Pagination, get_pagination
from app.dependencies.project import (
    require_can_manage_sprints,
    require_can_view_project,
)
from app.dependencies.rate_limiter import rate_limit_authenticated_mutation
from app.dependencies.sprint import get_sprint_by_id_or_404
from app.dependencies.sprint_queries import get_sprint_query_service
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.user import User
from app.schemas.sprint import SprintCreate, SprintRead, SprintUpdate
from app.services.sprint_actions import (
    close_sprint,
    create_sprint,
    delete_sprint,
    start_sprint,
    update_sprint,
)
from app.services.sprint_queries import SprintQueryService

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
ViewProject = Annotated[Project, Depends(require_can_view_project)]
ManageSprintsProject = Annotated[Project, Depends(require_can_manage_sprints)]
CurrentSprint = Annotated[Sprint, Depends(get_sprint_by_id_or_404)]
SprintCacheDep = Annotated[SprintCache, Depends(get_sprint_cache)]
SprintQueries = Annotated[SprintQueryService, Depends(get_sprint_query_service)]
PaginationDep = Annotated[Pagination, Depends(get_pagination)]


@router.post(
    "/",
    response_model=SprintRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def add_sprint_router(
    payload: SprintCreate,
    project: ManageSprintsProject,
    user: CurrentUser,
    db: DbSession,
    sprint_cache: SprintCacheDep,
):

    return create_sprint(payload, project, user, db, sprint_cache)


@router.get("/", response_model=list[SprintRead])
def get_sprints_router(
    project: ViewProject,
    user: CurrentUser,
    sprint_queries: SprintQueries,
    pagination: PaginationDep,
):

    return sprint_queries.list_accessible_by_project(
        project.id, pagination.limit, pagination.offset
    )


@router.get("/{sprint_id}", response_model=SprintRead)
def get_sprint_router(
    project: ViewProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
):

    return sprint


@router.delete(
    "/{sprint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def delete_sprint_router(
    project: ManageSprintsProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
    sprint_cache: SprintCacheDep,
):

    return delete_sprint(project, sprint, user, db, sprint_cache)


@router.patch(
    "/{sprint_id}",
    response_model=SprintRead,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def update_sprint_router(
    payload: SprintUpdate,
    project: ManageSprintsProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
    sprint_cache: SprintCacheDep,
):

    return update_sprint(payload, project, sprint, user, db, sprint_cache)


@router.patch(
    "/{sprint_id}/start",
    response_model=SprintRead,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def start_sprint_router(
    project: ManageSprintsProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
    sprint_cache: SprintCacheDep,
):

    return start_sprint(project, sprint, user, db, sprint_cache)


@router.patch(
    "/{sprint_id}/close",
    response_model=SprintRead,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def close_sprint_rputer(
    project: ManageSprintsProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
    sprint_cache: SprintCacheDep,
):

    return close_sprint(project, sprint, user, db, sprint_cache)
