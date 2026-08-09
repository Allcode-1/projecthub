from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project_invite import ProjectInvite, ProjectInviteStatus
from app.models.user import User


def _apply_pagination(statement, limit: int | None, offset: int):
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return statement


class ProjectInviteRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_invite(
        self, project_id, user_id, recipient_id, access_level
    ) -> ProjectInvite:

        project_invite = ProjectInvite(
            project_id=project_id,
            send_by=user_id,
            send_to=recipient_id,
            access_level=access_level,
        )

        self.db.add(project_invite)
        return project_invite

    def invite_by_id(self, invite_id) -> ProjectInvite | None:

        return self.db.scalar(
            select(ProjectInvite).where(ProjectInvite.id == invite_id)
        )

    def lock_invite_by_id(self, invite_id: int) -> ProjectInvite | None:
        return self.db.scalar(
            select(ProjectInvite).where(ProjectInvite.id == invite_id).with_for_update()
        )

    def invite_by_user_id(self, project_id, recipient_id) -> ProjectInvite | None:

        return self.db.scalar(
            select(ProjectInvite).where(
                ProjectInvite.project_id == project_id,
                ProjectInvite.send_to == recipient_id,
            )
        )

    def pending_invite_by_user_id(
        self, project_id: int, recipient_id: int
    ) -> ProjectInvite | None:
        return self.db.scalar(
            select(ProjectInvite).where(
                ProjectInvite.project_id == project_id,
                ProjectInvite.send_to == recipient_id,
                ProjectInvite.status == ProjectInviteStatus.PENDING,
            )
        )

    def recipient_by_id(self, recipient_id):

        return self.db.scalar(select(User).where(User.id == recipient_id))

    def invites_to_user(
        self, recipient_id: int, limit: int | None = None, offset: int = 0
    ):
        statement = (
            select(ProjectInvite)
            .where(ProjectInvite.send_to == recipient_id)
            .order_by(ProjectInvite.id)
        )

        return self.db.scalars(_apply_pagination(statement, limit, offset)).all()
