from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.db.session import get_db
from app.dependencies.pagination import Pagination, get_pagination
from app.dependencies.project import require_can_take_tasks
from app.dependencies.sprint import get_sprint_by_id_or_404
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.user import User
from app.schemas.review_comments import ReviewCommentRead
from app.services.review_comments import get_my_review_comment, get_my_review_comments

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
TakeTasksProject = Annotated[Project, Depends(require_can_take_tasks)]
CurrentSprint = Annotated[Sprint, Depends(get_sprint_by_id_or_404)]
PaginationDep = Annotated[Pagination, Depends(get_pagination)]


@router.get("/my_review_comments", response_model=list[ReviewCommentRead])
def get_my_review_comments_router(
    project: TakeTasksProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
):

    return get_my_review_comments(
        project, sprint, user, db, pagination.limit, pagination.offset
    )


@router.get("/my_review_comments/{comment_id}", response_model=ReviewCommentRead)
def get_my_review_comment_router(
    comment_id: int,
    project: TakeTasksProject,
    sprint: CurrentSprint,
    user: CurrentUser,
    db: DbSession,
):

    return get_my_review_comment(comment_id, project, sprint, user, db)
