from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    worker_id: int | None = Field(default=None)
    title: str = Field(min_length=3, max_length=55)
    description: str | None = Field(default=None, max_length=255)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    sprint_id: int
    creator_id: int | None
    worker_id: int | None
    title: str
    description: str | None
    status: TaskStatus
    created_at: datetime
    updated_at: datetime


class TaskUpdate(BaseModel):
    worker_id: int | None = None
    title: str | None = Field(default=None, min_length=3, max_length=55)
    description: str | None = Field(default=None, min_length=3, max_length=255)
