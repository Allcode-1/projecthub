from collections.abc import Iterable, Sequence

from pydantic import TypeAdapter, ValidationError

from app.cache.base import RedisCache
from app.schemas.sprint import SprintRead

_PROJECT_LIST_ADAPTER = TypeAdapter(list[SprintRead])


class SprintCache:
    def __init__(
        self,
        cache: RedisCache,
        project_list_ttl_seconds: int = 60,
        ttl_jitter_seconds: int = 15,
    ):

        self.cache = cache
        self.project_list_ttl_seconds = project_list_ttl_seconds
        self.ttl_jitter_seconds = ttl_jitter_seconds

    def project_sprints_key(self, project_id: int, limit: int, offset: int) -> str:
        return self.cache.key(
            "projects", project_id, "sprints", "limit", limit, "offset", offset
        )

    def project_sprints_pattern(self, project_id: int) -> str:
        return self.cache.key("projects", project_id, "sprints", "*")

    def get_project_sprints(
        self, project_id: int, limit: int, offset: int
    ) -> list[SprintRead] | None:
        key = self.project_sprints_key(project_id, limit, offset)
        payload = self.cache.get_json(key)

        if payload is None:
            return None

        try:
            return _PROJECT_LIST_ADAPTER.validate_python(payload)
        except ValidationError:
            self.cache.delete(key)
            return None

    def set_project_sprints(
        self,
        project_id: int,
        sprints: Sequence[SprintRead],
        limit: int,
        offset: int,
    ) -> None:

        key = self.project_sprints_key(project_id, limit, offset)
        payload = _PROJECT_LIST_ADAPTER.dump_python(list(sprints), mode="json")

        self.cache.set_json(
            key,
            payload,
            ttl_seconds=self.project_list_ttl_seconds,
            jitter_seconds=self.ttl_jitter_seconds,
        )

    def invalidate_project_sprints(self, project_id: int) -> None:
        self.cache.delete_pattern(self.project_sprints_pattern(project_id))

    def invalidate_projects_sprints(self, project_ids: Iterable[int]) -> None:
        for project_id in set(project_ids):
            self.invalidate_project_sprints(project_id)
