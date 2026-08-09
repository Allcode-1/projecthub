from datetime import datetime

from pydantic import BaseModel, Field

from app.models.sprint import SprintStatus


class SprintCreate(BaseModel):
    name: str = Field(min_length=3, max_length=55)
    description: str | None = Field(default=None, max_length=255)
    starts_at: datetime | None = None


class SprintRead(BaseModel):
    id: int
    project_id: int
    creator_id: int | None
    name: str
    description: str | None
    status: SprintStatus
    starts_at: datetime | None
    ends_at: datetime | None
    created_at: datetime
    closed_at: datetime | None


class SprintUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=55)
    description: str | None = Field(default=None, max_length=255)
    starts_at: datetime | None = Field(default=None)
    ends_at: datetime | None = Field(default=None)
