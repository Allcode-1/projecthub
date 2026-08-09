from app.cache.project import ProjectCache
from app.core.errors import AppError
from app.models.project import Project
from app.models.user import User
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from sqlalchemy.orm import Session


def _project_cache_user_ids(
    project_repo: ProjectRepository,
    project: Project,
) -> set[int]:
    user_ids = {project.owner_id}
    user_ids.update(
        member.id for member in project_repo.list_project_members(project.id)
    )
    return user_ids


def create_project(
    payload: ProjectCreate,
    user: User,
    db: Session,
    project_cache: ProjectCache,
) -> Project:

    project_repo = ProjectRepository(db)

    project = project_repo.create(
        owner_id=user.id, name=payload.name, description=payload.description
    )

    db.commit()
    db.refresh(project)

    project_cache.invalidate_user_projects(user.id)

    return project


def update_project(
    payload: ProjectUpdate,
    project: Project,
    user: User,
    db: Session,
    project_cache: ProjectCache,
) -> Project:

    if project.owner_id != user.id:
        raise AppError(403, "Not enough rights")

    project_repo = ProjectRepository(db)
    affected_user_ids = _project_cache_user_ids(project_repo, project)

    updated_fields = payload.model_dump(exclude_unset=True)

    for field, value in updated_fields.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)

    project_cache.invalidate_users_projects(affected_user_ids)

    return project


def delete_project(
    project: Project,
    user: User,
    db: Session,
    project_cache: ProjectCache,
) -> None:

    if project.owner_id != user.id:
        raise AppError(403, "Not enough rights")

    project_repo = ProjectRepository(db)
    affected_user_ids = _project_cache_user_ids(project_repo, project)

    db.delete(project)
    db.commit()

    project_cache.invalidate_users_projects(affected_user_ids)
