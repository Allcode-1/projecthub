from app.cache.project import ProjectCache
from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectRead, ProjectRole


def project_to_read(project: Project, current_user_role: ProjectRole) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        owner_id=project.owner_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        current_user_role=current_user_role,
    )


class ProjectQueryService:
    def __init__(self, project_repo: ProjectRepository, project_cache: ProjectCache):

        self.project_repo = project_repo
        self.project_cache = project_cache

    def list_accessible_by_user(
        self, user_id: int, limit: int, offset: int
    ) -> list[ProjectRead]:

        cached_projects = self.project_cache.get_user_projects(user_id, limit, offset)

        if cached_projects is not None:
            return cached_projects

        projects_with_roles = self.project_repo.list_accessible_by_user_with_role(
            user_id, limit, offset
        )

        project_reads = [
            project_to_read(project, ProjectRole(role))
            for project, role in projects_with_roles
        ]

        self.project_cache.set_user_projects(user_id, project_reads, limit, offset)

        return project_reads
