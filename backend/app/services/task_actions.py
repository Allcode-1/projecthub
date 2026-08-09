from app.core.errors import AppError
from app.models.project import Project
from app.models.sprint import Sprint, SprintStatus
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.repositories.project import ProjectRepository
from app.repositories.review_comment import ReviewCommentRepository
from app.repositories.task import TaskRepository
from app.schemas.review_comments import ReviewCommentCreate
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.project_membership import can_manage_sprints
from sqlalchemy.orm import Session


def _ensure_sprint_open(sprint: Sprint) -> None:
    if sprint.status == SprintStatus.CLOSED:
        raise AppError(409, "Sprint is closed")


def _ensure_task_editable(task: Task) -> None:
    if task.status != TaskStatus.TODO:
        raise AppError(409, "Only todo tasks can be edited")


def add_task(
    payload: TaskCreate, project: Project, sprint: Sprint, user: User, db: Session
) -> Task:

    _ensure_sprint_open(sprint)

    task_repo = TaskRepository(db)
    project_repo = ProjectRepository(db)

    if payload.worker_id is not None:
        worker = project_repo.project_worker_by_id(project.id, payload.worker_id)
        if worker is None:
            raise AppError(404, "Worker not found")

    task = task_repo.create(
        project_id=project.id,
        sprint_id=sprint.id,
        creator_id=user.id,
        worker_id=payload.worker_id,
        title=payload.title,
        description=payload.description,
    )

    task.status = TaskStatus.TODO

    db.commit()
    db.refresh(task)

    return task


def update_task(
    payload: TaskUpdate,
    project: Project,
    sprint: Sprint,
    task: Task,
    user: User,
    db: Session,
) -> Task:

    if not can_manage_sprints(db, user, project):
        raise AppError(403, "Not enough rights")

    _ensure_sprint_open(sprint)

    task_repo = TaskRepository(db)
    locked_task = task_repo.lock_task_by_id(project.id, sprint.id, task.id)
    if locked_task is None:
        raise AppError(404, "Task not found")

    _ensure_task_editable(locked_task)

    updated_fields = payload.model_dump(exclude_unset=True)

    worker_id = updated_fields.get("worker_id")
    if worker_id is not None:
        project_repo = ProjectRepository(db)
        worker = project_repo.project_worker_by_id(project.id, worker_id)
        if worker is None:
            raise AppError(404, "Worker not found")

    for field, value in updated_fields.items():
        setattr(locked_task, field, value)

    db.commit()
    db.refresh(locked_task)

    return locked_task


def delete_task(
    project: Project, sprint: Sprint, task: Task, user: User, db: Session
) -> None:

    if not can_manage_sprints(db, user, project):
        raise AppError(403, "Not enough rights")

    _ensure_sprint_open(sprint)

    task_repo = TaskRepository(db)
    locked_task = task_repo.lock_task_by_id(project.id, sprint.id, task.id)
    if locked_task is None:
        raise AppError(404, "Task not found")

    _ensure_task_editable(locked_task)

    db.delete(locked_task)
    db.commit()


def take_task_to_work(sprint: Sprint, task: Task, user: User, db: Session) -> Task:

    _ensure_sprint_open(sprint)

    if task.status != TaskStatus.TODO:
        raise AppError(409, "Task is not available")

    if task.worker_id is not None and task.worker_id != user.id:
        raise AppError(409, "Task is assigned to another worker")

    task_repo = TaskRepository(db)
    updated_task = task_repo.claim_task_for_user(
        task.project_id, task.sprint_id, task.id, user.id
    )

    if updated_task is None:
        raise AppError(409, "Task is not available")

    db.commit()
    db.refresh(updated_task)

    return updated_task


def send_task_to_review(sprint: Sprint, task: Task, user: User, db: Session) -> Task:

    _ensure_sprint_open(sprint)

    if task.worker_id != user.id or task.status != TaskStatus.IN_PROGRESS:
        raise AppError(409, "Can't send task to review")

    task_repo = TaskRepository(db)
    updated_task = task_repo.send_assigned_task_to_review(
        task.project_id, task.sprint_id, task.id, user.id
    )

    if updated_task is None:
        raise AppError(409, "Can't send task to review")

    db.commit()
    db.refresh(updated_task)

    return updated_task


def accept_task_review(sprint: Sprint, task: Task, user: User, db: Session) -> Task:

    _ensure_sprint_open(sprint)

    if task.worker_id == user.id or task.status != TaskStatus.REVIEW:
        raise AppError(409, "Task need to be on review")

    task_repo = TaskRepository(db)
    updated_task = task_repo.accept_reviewed_task(
        task.project_id, task.sprint_id, task.id, user.id
    )

    if updated_task is None:
        raise AppError(409, "Task need to be on review")

    db.commit()
    db.refresh(updated_task)

    return updated_task


def decline_task_review(
    payload: ReviewCommentCreate | None,
    sprint: Sprint,
    task: Task,
    user: User,
    db: Session,
) -> Task:

    _ensure_sprint_open(sprint)

    if task.worker_id == user.id or task.status != TaskStatus.REVIEW:
        raise AppError(409, "Task need to be on review")

    task_repo = TaskRepository(db)
    updated_task = task_repo.decline_reviewed_task(
        task.project_id, task.sprint_id, task.id, user.id
    )

    if updated_task is None:
        raise AppError(409, "Task need to be on review")

    if payload is not None and payload.comment is not None:
        review_comment_repo = ReviewCommentRepository(db)
        review_comment_repo.create(
            task_id=task.id,
            comment=payload.comment,
            author_id=user.id,
        )

    db.commit()
    db.refresh(updated_task)

    return updated_task


def renew_task(sprint: Sprint, task: Task, user: User, db: Session) -> Task:

    _ensure_sprint_open(sprint)

    if task.worker_id != user.id or task.status != TaskStatus.REJECTED:
        raise AppError(409, "Can't renew task")

    task_repo = TaskRepository(db)
    updated_task = task_repo.renew_rejected_task(
        task.project_id, task.sprint_id, task.id, user.id
    )

    if updated_task is None:
        raise AppError(409, "Can't renew task")

    db.commit()
    db.refresh(updated_task)

    return updated_task
