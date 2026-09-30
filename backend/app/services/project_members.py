from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache.project import ProjectCache
from app.core.errors import AppError
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task, TaskStatus
from app.models.user import User


def leave_project(
    project: Project,
    user: User,
    db: Session,
    project_cache: ProjectCache,
) -> None:
    if project.owner_id == user.id:
        raise AppError(409, "Project owner cannot leave own project")

    membership = db.scalar(
        select(ProjectMember)
        .where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user.id,
        )
        .with_for_update()
    )

    if membership is None:
        raise AppError(404, "Project member not found")

    has_active_assigned_task = db.scalar(
        select(Task.id)
        .where(
            Task.project_id == project.id,
            Task.worker_id == user.id,
            Task.status != TaskStatus.DONE,
        )
        .limit(1)
    )

    if has_active_assigned_task is not None:
        raise AppError(409, "Cannot leave project with active assigned tasks")

    db.delete(membership)
    db.commit()

    project_cache.invalidate_user_projects(user.id)
