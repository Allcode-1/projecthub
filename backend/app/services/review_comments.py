from app.models.project import Project
from app.models.review_comment import ReviewComment
from app.models.sprint import Sprint
from app.models.user import User
from app.repositories.review_comment import ReviewCommentRepository
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
