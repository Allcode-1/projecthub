from app.core.errors import AppError
from app.models.project import Project
from app.models.review_comment import ReviewComment
from app.models.sprint import Sprint
from app.models.user import User
from app.repositories.review_comment import ReviewCommentRepository
from app.repositories.task import TaskRepository, TaskStatus
from sqlalchemy.orm import Session


def get_my_review_comments(
    project: Project,
    sprint: Sprint,
    user: User,
    db: Session,
    limit: int,
    offset: int,
) -> list[ReviewComment]:

    review_comment_repo = ReviewCommentRepository(db)

    return review_comment_repo.comments_for_rejected_tasks(
        project.id,
        sprint.id,
        user.id,
        limit,
        offset,
    )


def get_my_review_comment(
    comment_id: int, project: Project, sprint: Sprint, user: User, db: Session
):

    review_comment_repo = ReviewCommentRepository(db)
    task_repo = TaskRepository(db)

    review_comment = review_comment_repo.comment_by_id(comment_id)

    if review_comment is None:
        raise AppError(404, "Review comment not found")

    task = task_repo.task_by_id(project.id, sprint.id, review_comment.task_id)

    if task is None or task.worker_id != user.id or task.status != TaskStatus.REJECTED:
        raise AppError(404, "Review comment not found")

    return review_comment
