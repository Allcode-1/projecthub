from datetime import datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SprintStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    CLOSED = "closed"


class Sprint(Base):
    __tablename__ = "sprints"
    __table_args__ = (
        CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at",
            name="ck_sprints_ends_after_starts",
        ),
        CheckConstraint(
            "status != 'active' OR starts_at IS NOT NULL",
            name="ck_sprints_active_has_starts_at",
        ),
        CheckConstraint(
            "status != 'closed' OR closed_at IS NOT NULL",
            name="ck_sprints_closed_has_closed_at",
        ),
        Index("ix_sprints_project_status", "project_id", "status"),
        Index("ix_sprints_lifecycle", "status", "starts_at", "ends_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    creator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(55), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[SprintStatus] = mapped_column(
        SAEnum(
            SprintStatus,
            name="sprint_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=SprintStatus.PLANNED,
    )

    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
