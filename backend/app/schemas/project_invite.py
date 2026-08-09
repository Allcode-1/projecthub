from pydantic import BaseModel, ConfigDict

from app.models.project_invite import ProjectInviteAccessLevel, ProjectInviteStatus


class ProjectInviteCreate(BaseModel):
    access_level: ProjectInviteAccessLevel = ProjectInviteAccessLevel.VIEWER


class ProjectInviteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    send_by: int
    send_to: int
    access_level: ProjectInviteAccessLevel
    status: ProjectInviteStatus


class ProjectInviteUpdate(BaseModel):
    access_level: ProjectInviteAccessLevel
