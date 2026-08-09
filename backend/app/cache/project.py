from collections.abc import Iterable, Sequence

from pydantic import TypeAdapter, ValidationError

from app.cache.base import RedisCache
from app.schemas.project import ProjectRead

_PROJECT_LIST_ADAPTER = TypeAdapter(list[ProjectRead])


class ProjectCache:
    def __init__(
        self,
        cache: RedisCache,
        project_list_ttl_seconds: int = 60,
        ttl_jitter_seconds: int = 15,
    ):

        self.cache = cache
        self.project_list_ttl_seconds = project_list_ttl_seconds
        self.ttl_jitter_seconds = ttl_jitter_seconds

    def user_projects_key(self, user_id: int, limit: int, offset: int) -> str:
        return self.cache.key(
            "users", user_id, "projects", "limit", limit, "offset", offset
        )

    def user_projects_pattern(self, user_id: int) -> str:
        return self.cache.key("users", user_id, "projects", "*")

    def get_user_projects(
        self, user_id: int, limit: int, offset: int
    ) -> list[ProjectRead] | None:
        key = self.user_projects_key(user_id, limit, offset)
        payload = self.cache.get_json(key)

        if payload is None:
            return None

        try:
            return _PROJECT_LIST_ADAPTER.validate_python(payload)
        except ValidationError:
            self.cache.delete(key)
            return None

    def set_user_projects(
        self,
        user_id: int,
        projects: Sequence[ProjectRead],
        limit: int,
        offset: int,
    ) -> None:

        key = self.user_projects_key(user_id, limit, offset)
        payload = _PROJECT_LIST_ADAPTER.dump_python(list(projects), mode="json")

        self.cache.set_json(
            key,
            payload,
            ttl_seconds=self.project_list_ttl_seconds,
            jitter_seconds=self.ttl_jitter_seconds,
        )

    def invalidate_user_projects(self, user_id: int) -> None:
        self.cache.delete_pattern(self.user_projects_pattern(user_id))

    def invalidate_users_projects(self, user_ids: Iterable[int]) -> None:
        for user_id in set(user_ids):
            self.invalidate_user_projects(user_id)
