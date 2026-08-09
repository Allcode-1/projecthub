from datetime import datetime, timezone

from app.cache.project import ProjectCache
from app.core.errors import AppError
from app.models.project import Project
from app.models.project_invite import (
    ProjectInvite,
    ProjectInviteStatus,
)
from app.models.project_member import ProjectMember
from app.models.user import User
from app.repositories.project_invite import ProjectInviteRepository
from app.schemas.project_invite import ProjectInviteCreate, ProjectInviteUpdate
from app.services.project_membership import can_view_project, get_project_access
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def invite_to_project_by_id(
    payload: ProjectInviteCreate,
    project: Project,
    user: User,
    recipient: User,
    db: Session,
) -> ProjectInvite:

    invites_repo = ProjectInviteRepository(db)

    existing_invite = invites_repo.pending_invite_by_user_id(project.id, recipient.id)

    if existing_invite:
        raise AppError(409, "User already invited to this project")

    if can_view_project(db, recipient, project):
        raise AppError(409, "Project member already")

    invite = invites_repo.create_invite(
        project.id, user.id, recipient.id, payload.access_level
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "User already invited to this project") from exc
    db.refresh(invite)
    return invite


def update_invite(
    payload: ProjectInviteUpdate,
    project: Project,
    user: User,
    recipient: User,
    db: Session,
) -> ProjectInvite:

    invites_repo = ProjectInviteRepository(db)

    existing_invite = invites_repo.pending_invite_by_user_id(project.id, recipient.id)

    if not existing_invite:
        raise AppError(404, "Invite not found")

    if existing_invite.send_by != user.id:
        raise AppError(404, "Invite not found")

    updated_fields = payload.model_dump(exclude_unset=True)

    for field, value in updated_fields.items():
        setattr(existing_invite, field, value)

    db.commit()
    db.refresh(existing_invite)

    return existing_invite


def delete_invite(project: Project, user: User, recipient: User, db: Session) -> None:

    invites_repo = ProjectInviteRepository(db)

    existing_invite = invites_repo.pending_invite_by_user_id(project.id, recipient.id)

    if not existing_invite:
        raise AppError(404, "Invite not found")

    if existing_invite.send_by != user.id:
        raise AppError(404, "Invite not found")

    db.delete(existing_invite)
    db.commit()


def accept_invite(
    invite_id: int,
    user: User,
    db: Session,
    project_cache: ProjectCache,
) -> ProjectInvite:

    invites_repo = ProjectInviteRepository(db)

    existing_invite = invites_repo.lock_invite_by_id(invite_id)

    if not existing_invite or existing_invite.send_to != user.id:
        raise AppError(404, "Invite not found")

    if existing_invite.status != ProjectInviteStatus.PENDING:
        raise AppError(409, "Invite already responced")

    if get_project_access(db, user.id, existing_invite.project_id) is not None:
        raise AppError(409, "Project member already")

    existing_invite.status = ProjectInviteStatus.ACCEPTED

    now = datetime.now(timezone.utc)

    new_project_member = ProjectMember(
        project_id=existing_invite.project_id,
        user_id=user.id,
        role=existing_invite.access_level,
        joined_at=now,
    )

    db.add(new_project_member)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "Project member already") from exc
    db.refresh(existing_invite)

    project_cache.invalidate_user_projects(user.id)

    return existing_invite


def decline_invite(invite_id: int, user: User, db: Session) -> ProjectInvite:

    invites_repo = ProjectInviteRepository(db)

    existing_invite = invites_repo.lock_invite_by_id(invite_id)

    if not existing_invite or existing_invite.send_to != user.id:
        raise AppError(404, "Invite not found")

    if existing_invite.status != ProjectInviteStatus.PENDING:
        raise AppError(409, "Invite already responced")

    existing_invite.status = ProjectInviteStatus.DECLINED

    db.commit()
    db.refresh(existing_invite)

    return existing_invite
