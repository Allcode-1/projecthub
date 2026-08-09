from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.repositories.project import ProjectRepository
from app.services.project_membership import (
    can_manage_sprints,
    can_take_tasks,
    can_view_project,
)

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]


def get_project_by_id_or_404(project_id: int, db: DbSession):

    project_repo = ProjectRepository(db)

    project = project_repo.get_by_id(project_id)

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    return project


ProjectById = Annotated[Project, Depends(get_project_by_id_or_404)]


def require_can_view_project(
    project: ProjectById,
    user: CurrentUser,
    db: DbSession,
):

    if not can_view_project(db, user, project):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough rights",
        )

    return project


def require_can_take_tasks(
    project: ProjectById,
    user: CurrentUser,
    db: DbSession,
):

    if not can_take_tasks(db, user, project):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough rights",
        )

    return project


def require_can_manage_sprints(
    project: ProjectById,
    user: CurrentUser,
    db: DbSession,
):

    if not can_manage_sprints(db, user, project):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough rights",
        )

    return project


def get_project_worker_id_or_404(
    project_id: int,
    user_id: int,
    db: DbSession,
):

    project_repo = ProjectRepository(db)

    worker = project_repo.project_worker_by_id(project_id, user_id)

    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    return worker
