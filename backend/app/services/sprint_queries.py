from app.cache.sprint import SprintCache
from app.repositories.sprint import SprintRepository
from app.schemas.sprint import SprintRead


class SprintQueryService:
    def __init__(self, sprint_repo: SprintRepository, sprint_cache: SprintCache):

        self.sprint_repo = sprint_repo
        self.sprint_cache = sprint_cache

    def list_accessible_by_project(
        self, project_id: int, limit: int, offset: int
    ) -> list[SprintRead]:

        cached_sprints = self.sprint_cache.get_project_sprints(
            project_id, limit, offset
        )

        if cached_sprints is not None:
            return cached_sprints

        sprints = self.sprint_repo.all_sprints(project_id, limit, offset)

        sprint_reads = [
            SprintRead.model_validate(sprint, from_attributes=True)
            for sprint in sprints
        ]

        self.sprint_cache.set_project_sprints(project_id, sprint_reads, limit, offset)

        return sprint_reads
