from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.cache.project import ProjectCache
from app.core.errors import AppError
from app.db.session import get_db
from app.dependencies.cache import get_project_cache
from app.dependencies.pagination import Pagination, get_pagination
from app.dependencies.project import require_can_manage_sprints
from app.dependencies.project_invite import recipient_by_id_or_404
from app.dependencies.rate_limiter import rate_limit_authenticated_mutation
from app.models.project import Project
from app.models.user import User
from app.repositories.project_invite import ProjectInviteRepository
from app.schemas.project_invite import (
    ProjectInviteCreate,
    ProjectInviteRead,
    ProjectInviteUpdate,
)
from app.services.project_invites import (
    accept_invite,
    decline_invite,
    delete_invite,
    invite_to_project_by_id,
    update_invite,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
ManageSprintsProject = Annotated[Project, Depends(require_can_manage_sprints)]
InviteRecipient = Annotated[User, Depends(recipient_by_id_or_404)]
ProjectCacheDep = Annotated[ProjectCache, Depends(get_project_cache)]
PaginationDep = Annotated[Pagination, Depends(get_pagination)]


@router.post(
    "/projects/{project_id}/invites/users/{recipient_id}",
    response_model=ProjectInviteRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def invite_user_to_project(
    payload: ProjectInviteCreate,
    recipient: InviteRecipient,
    project: ManageSprintsProject,
    user: CurrentUser,
    db: DbSession,
):

    return invite_to_project_by_id(payload, project, user, recipient, db)


@router.patch(
    "/projects/{project_id}/invites/users/{recipient_id}",
    response_model=ProjectInviteRead,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def update_user_invite(
    payload: ProjectInviteUpdate,
    recipient: InviteRecipient,
    project: ManageSprintsProject,
    user: CurrentUser,
    db: DbSession,
):

    return update_invite(payload, project, user, recipient, db)


@router.delete(
    "/projects/{project_id}/invites/users/{recipient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def delete_user_invite(
    project: ManageSprintsProject,
    recipient: InviteRecipient,
    user: CurrentUser,
    db: DbSession,
):

    return delete_invite(project, user, recipient, db)


@router.get("/invites", response_model=list[ProjectInviteRead])
def get_my_invites(user: CurrentUser, db: DbSession, pagination: PaginationDep):

    invites_repo = ProjectInviteRepository(db)
    my_invites = invites_repo.invites_to_user(
        user.id, pagination.limit, pagination.offset
    )
    return my_invites


@router.get("/invites/{invite_id}", response_model=ProjectInviteRead)
def get_invite_by_id(
    invite_id: int,
    user: CurrentUser,
    db: DbSession,
):

    invites_repo = ProjectInviteRepository(db)
    invite = invites_repo.invite_by_id(invite_id)

    if not invite or invite.send_to != user.id:
        raise AppError(404, "Invite not found")

    return invite


@router.patch(
    "/invites/accept/{invite_id}",
    response_model=ProjectInviteRead,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def accept_invite_router(
    invite_id: int,
    user: CurrentUser,
    db: DbSession,
    project_cache: ProjectCacheDep,
):

    return accept_invite(invite_id, user, db, project_cache)


@router.patch(
    "/invites/decline/{invite_id}",
    response_model=ProjectInviteRead,
    dependencies=[Depends(rate_limit_authenticated_mutation)],
)
def decline_invite_router(
    invite_id: int,
    user: CurrentUser,
    db: DbSession,
):

    return decline_invite(invite_id, user, db)
