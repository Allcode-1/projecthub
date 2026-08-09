from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review_comment import ReviewComment
from app.models.task import Task, TaskStatus


def _apply_pagination(statement, limit: int | None, offset: int):
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return statement


class ReviewCommentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        task_id: int,
        comment: str,
        author_id: int,
    ) -> ReviewComment:
        review_comment = ReviewComment(
            task_id=task_id,
            comment=comment,
            author_id=author_id,
        )

        self.db.add(review_comment)
        return review_comment

    def comment_by_id(self, comment_id: int) -> ReviewComment | None:

        return self.db.scalar(
            select(ReviewComment).where(ReviewComment.id == comment_id)
        )

    def comments_by_task_ids(
        self,
        task_ids: list[int],
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ReviewComment]:

        if not task_ids:
            return []

        statement = (
            select(ReviewComment)
            .join(Task, ReviewComment.task_id == Task.id)
            .where(ReviewComment.task_id.in_(task_ids))
            .order_by(ReviewComment.id)
        )

        return list(self.db.scalars(_apply_pagination(statement, limit, offset)).all())

    def comments_for_rejected_tasks(
        self,
        project_id: int,
        sprint_id: int,
        worker_id: int,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ReviewComment]:
        statement = (
            select(ReviewComment)
            .join(Task, ReviewComment.task_id == Task.id)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.worker_id == worker_id,
                Task.status == TaskStatus.REJECTED,
            )
            .order_by(ReviewComment.id)
        )

        return list(self.db.scalars(_apply_pagination(statement, limit, offset)).all())
