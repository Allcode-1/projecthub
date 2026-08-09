from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.project_invite import ProjectInvite
    from app.models.project_member import ProjectMember


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(55), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=UserRole.USER,
    )

    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project_members: Mapped[list[ProjectMember]] = relationship(
        back_populates="user", passive_deletes=True
    )

    projects: Mapped[list[Project]] = relationship(back_populates="owner")

    sent_project_invites: Mapped[list[ProjectInvite]] = relationship(
        back_populates="sender",
        foreign_keys="ProjectInvite.send_by",
    )

    received_project_invites: Mapped[list[ProjectInvite]] = relationship(
        back_populates="recipient", foreign_keys="ProjectInvite.send_to"
    )
