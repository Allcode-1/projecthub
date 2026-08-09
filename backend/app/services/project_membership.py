from app.models.project import Project
from app.models.project_member import ProjectInviteAccessLevel, ProjectMember
from app.models.user import User
from app.schemas.project import ProjectRole
from sqlalchemy import select
from sqlalchemy.orm import Session


def get_project_access(
    db: Session, user_id: int, project_id: int
) -> ProjectMember | None:

    return db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
    )


def get_project_role(db: Session, user: User, project: Project) -> ProjectRole:
    if is_project_owner(user, project):
        return ProjectRole.OWNER

    access = get_project_access(db, user.id, project.id)
    if access is None:
        raise ValueError("User has no access to project")

    return ProjectRole(access.role)


def is_project_owner(user: User, project: Project) -> bool:

    return project.owner_id == user.id


def can_view_project(db: Session, user: User, project: Project) -> bool:

    if is_project_owner(user, project):
        return True

    access = get_project_access(db, user.id, project.id)

    return access is not None and access.role in (
        ProjectInviteAccessLevel.VIEWER,
        ProjectInviteAccessLevel.WORKER,
        ProjectInviteAccessLevel.ADMIN,
    )


def can_take_tasks(db: Session, user: User, project: Project) -> bool:
    if is_project_owner(user, project):
        return True

    access = get_project_access(db, user.id, project.id)

    return access is not None and access.role in (
        ProjectInviteAccessLevel.WORKER,
        ProjectInviteAccessLevel.ADMIN,
    )


def can_manage_sprints(db: Session, user: User, project: Project) -> bool:
    if is_project_owner(user, project):
        return True

    access = get_project_access(db, user.id, project.id)

    return access is not None and access.role == ProjectInviteAccessLevel.ADMIN
