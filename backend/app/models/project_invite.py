from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class ProjectInviteAccessLevel(str, Enum):
    VIEWER = "viewer"
    WORKER = "worker"
    ADMIN = "admin"


class ProjectInviteStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    REVOKED = "revoked"


class ProjectInvite(Base):
    __tablename__ = "project_invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    send_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    send_to: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    access_level: Mapped[ProjectInviteAccessLevel] = mapped_column(
        SAEnum(
            ProjectInviteAccessLevel,
            name="project_invite_access_level",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=ProjectInviteAccessLevel.VIEWER,
    )

    status: Mapped[ProjectInviteStatus] = mapped_column(
        SAEnum(
            ProjectInviteStatus,
            name="project_invite_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=ProjectInviteStatus.PENDING,
    )

    project: Mapped[Project] = relationship(back_populates="project_invites")

    sender: Mapped[User] = relationship(
        back_populates="sent_project_invites",
        foreign_keys=[send_by],
    )

    recipient: Mapped[User] = relationship(
        back_populates="received_project_invites",
        foreign_keys=[send_to],
    )


Index(
    "ix_project_invites_pending_project_send_to",
    ProjectInvite.project_id,
    ProjectInvite.send_to,
    unique=True,
    postgresql_where=ProjectInvite.status == ProjectInviteStatus.PENDING,
    sqlite_where=ProjectInvite.status == ProjectInviteStatus.PENDING,
)
Index(
    "ix_project_invites_send_to_status",
    ProjectInvite.send_to,
    ProjectInvite.status,
)
