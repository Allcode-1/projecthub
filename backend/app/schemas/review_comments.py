from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCommentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    comment: str | None = Field(default=None, min_length=2, max_length=512)


class ReviewCommentUpdate(BaseModel):
    comment: str | None = Field(default=None, min_length=2, max_length=512)


class ReviewCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    comment: str
    author_id: int | None
    created_at: datetime
