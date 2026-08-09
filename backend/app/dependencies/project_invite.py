from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.project_invite import ProjectInviteRepository

DbSession = Annotated[Session, Depends(get_db)]


def invite_by_id_or_404(project_id: int, recipient_id: int, db: DbSession):

    project_invite_repo = ProjectInviteRepository(db)

    invite = project_invite_repo.invite_by_user_id(project_id, recipient_id)

    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found"
        )

    return invite


def recipient_by_id_or_404(recipient_id: int, db: DbSession):

    project_invite_repo = ProjectInviteRepository(db)

    recipient = project_invite_repo.recipient_by_id(recipient_id)

    if recipient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found"
        )

    return recipient


def invites_to_user(recipient_id: int, db: DbSession):

    project_invite_repo = ProjectInviteRepository(db)

    invites = project_invite_repo.invites_to_user(recipient_id)
    return invites
