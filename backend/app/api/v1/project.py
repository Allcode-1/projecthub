from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.auth.schemas import UserRead
from app.cache.project import ProjectCache
from app.db.session import get_db
from app.dependencies.cache import get_project_cache
from app.dependencies.pagination import Pagination, get_pagination
from app.dependencies.project import (
    require_can_manage_sprints,
    require_can_view_project,
)
from app.dependencies.project_queries import get_project_query_service
from app.dependencies.rate_limiter import rate_limit_authenticated_mutation
from app.models.project import Project
from app.models.user import User
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectRead, ProjectRole, ProjectUpdate
from app.services.project_actions import create_project, delete_project, update_project
from app.services.project_members import leave_project
from app.services.project_membership import get_project_role
from app.services.project_queries import ProjectQueryService, project_to_read

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
ViewProject = Annotated[Project, Depends(require_can_view_project)]
ManageSprintsProject = Annotated[Project, Depends(require_can_manage_sprints)]
ProjectCacheDep = Annotated[ProjectCache, Depends(get_project_cache)]
ProjectQueries = Annotated[ProjectQueryService, Depends(get_project_query_service)]
PaginationDep = Annotated[Pagination, Depends(get_pagination)]


@router.post(
    "/",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def add_project_router(
    payload: ProjectCreate,
    user: CurrentUser,
    db: DbSession,
    project_cache: ProjectCacheDep,
):

    project = create_project(payload, user, db, project_cache)
    return project_to_read(project, ProjectRole.OWNER)


@router.get("/", response_model=list[ProjectRead])
def get_projects_router(
    user: CurrentUser,
    project_queries: ProjectQueries,
    pagination: PaginationDep,
):

    return project_queries.list_accessible_by_user(
        user.id, pagination.limit, pagination.offset
    )


@router.get("/{project_id}", response_model=ProjectRead)
def get_project_router(
    project: ViewProject,
    user: CurrentUser,
    db: DbSession,
):

    return project_to_read(project, get_project_role(db, user, project))


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def delete_project_router(
    project: ManageSprintsProject,
    user: CurrentUser,
    db: DbSession,
    project_cache: ProjectCacheDep,
):

    return delete_project(project, user, db, project_cache)


@router.patch(
    "/{project_id}",
    response_model=ProjectRead,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def update_project_router(
    payload: ProjectUpdate,
    project: ManageSprintsProject,
    user: CurrentUser,
    db: DbSession,
    project_cache: ProjectCacheDep,
):

    updated_project = update_project(payload, project, user, db, project_cache)
    return project_to_read(updated_project, ProjectRole.OWNER)


@router.get("/{project_id}/members", response_model=list[UserRead])
def get_project_members(
    project: ViewProject,
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
):

    project_repo = ProjectRepository(db)
    project_members = project_repo.list_project_members(
        project.id, pagination.limit, pagination.offset
    )

    return project_members


@router.delete(
    "/{project_id}/members/me",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def leave_project_router(
    project: ViewProject,
    user: CurrentUser,
    db: DbSession,
    project_cache: ProjectCacheDep,
):
    return leave_project(project, user, db, project_cache)
