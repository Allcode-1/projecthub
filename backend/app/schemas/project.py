from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ProjectRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    WORKER = "worker"
    VIEWER = "viewer"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=3, max_length=55)
    description: str | None = Field(default=None, max_length=255)


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    description: str | None
    created_at: datetime
    current_user_role: ProjectRole


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=55)
    description: str | None = Field(default=None, max_length=255)
