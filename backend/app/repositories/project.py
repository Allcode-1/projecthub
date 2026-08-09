from sqlalchemy import String, and_, case, cast, or_, select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_member import ProjectInviteAccessLevel, ProjectMember
from app.models.user import User


def _apply_pagination(statement, limit: int | None, offset: int):
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return statement


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, owner_id: int, name: str, description: str | None) -> Project:

        project = Project(owner_id=owner_id, name=name, description=description)

        self.db.add(project)
        return project

    def get_by_id(self, project_id: int) -> Project | None:
        return self.db.scalar(select(Project).where(Project.id == project_id))

    def list_owned_by_user(
        self, user_id: int, limit: int | None = None, offset: int = 0
    ) -> list[Project]:
        statement = (
            select(Project).where(Project.owner_id == user_id).order_by(Project.id)
        )

        return list(self.db.scalars(_apply_pagination(statement, limit, offset)).all())

    def list_accessible_by_user_with_role(
        self, user_id: int, limit: int | None = None, offset: int = 0
    ) -> list[tuple[Project, ProjectInviteAccessLevel | str]]:
        statement = (
            select(
                Project,
                case(
                    (Project.owner_id == user_id, "owner"),
                    else_=cast(ProjectMember.role, String),
                ),
            )
            .outerjoin(
                ProjectMember,
                and_(
                    ProjectMember.project_id == Project.id,
                    ProjectMember.user_id == user_id,
                ),
            )
            .where(
                or_(
                    Project.owner_id == user_id,
                    ProjectMember.user_id == user_id,
                )
            )
            .order_by(Project.id)
        )

        return list(
            self.db.execute(_apply_pagination(statement, limit, offset)).tuples()
        )

    def project_worker_by_id(self, project_id: int, user_id: int) -> User | None:

        return self.db.scalar(
            select(User)
            .join(ProjectMember, User.id == ProjectMember.user_id)
            .where(
                ProjectMember.user_id == user_id,
                ProjectMember.project_id == project_id,
                ProjectMember.role == ProjectInviteAccessLevel.WORKER,
            )
        )

    def list_project_members(
        self, project_id: int, limit: int | None = None, offset: int = 0
    ) -> list[User]:
        statement = (
            select(User)
            .join(ProjectMember, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(User.id)
        )

        return list(self.db.scalars(_apply_pagination(statement, limit, offset)).all())
