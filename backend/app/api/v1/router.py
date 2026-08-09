from fastapi import APIRouter

from app.api.v1 import (
    project,
    project_invite,
    review_comment,
    sprint,
    task,
    task_actions,
)

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(project.router, prefix="/projects", tags=["projects"])
v1_router.include_router(
    sprint.router, prefix="/projects/{project_id}/sprints", tags=["sprints"]
)
v1_router.include_router(project_invite.router, tags=["project invites"])
v1_router.include_router(
    review_comment.router,
    prefix="/projects/{project_id}/sprints/{sprint_id}/tasks",
    tags=["review comments"],
)
v1_router.include_router(
    task.router,
    prefix="/projects/{project_id}/sprints/{sprint_id}/tasks",
    tags=["tasks"],
)
v1_router.include_router(
    task_actions.router,
    prefix="/projects/{project_id}/sprints/{sprint_id}/tasks",
    tags=["task actions"],
)
