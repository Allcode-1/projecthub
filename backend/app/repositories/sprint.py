from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sprint import Sprint


def _apply_pagination(statement, limit: int | None, offset: int):
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return statement


class SprintRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        project_id: int,
        creator_id: int,
        name: str,
        description: str | None,
        starts_at: datetime,
        ends_at: datetime,
    ) -> Sprint:

        sprint = Sprint(
            project_id=project_id,
            creator_id=creator_id,
            name=name,
            description=description,
            starts_at=starts_at,
            ends_at=ends_at,
        )

        self.db.add(sprint)
        return sprint

    def get_by_id(self, project_id: int, sprint_id: int) -> Sprint | None:

        return self.db.scalar(
            select(Sprint).where(
                Sprint.project_id == project_id, Sprint.id == sprint_id
            )
        )

    def all_sprints(
        self, project_id: int, limit: int | None = None, offset: int = 0
    ) -> list[Sprint]:
        statement = (
            select(Sprint).where(Sprint.project_id == project_id).order_by(Sprint.id)
        )

        return list(self.db.scalars(_apply_pagination(statement, limit, offset)).all())
