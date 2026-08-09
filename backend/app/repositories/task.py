from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus


def _apply_pagination(statement, limit: int | None, offset: int):
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return statement


class TaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        project_id: int,
        sprint_id: int,
        creator_id: int,
        worker_id: int | None,
        title: str,
        description: str | None,
    ) -> Task:

        task = Task(
            project_id=project_id,
            sprint_id=sprint_id,
            creator_id=creator_id,
            worker_id=worker_id,
            title=title,
            description=description,
        )

        self.db.add(task)
        return task

    def task_by_id(self, project_id: int, sprint_id: int, task_id: int) -> Task | None:

        return self.db.scalar(
            select(Task).where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.id == task_id,
            )
        )

    def lock_task_by_id(
        self, project_id: int, sprint_id: int, task_id: int
    ) -> Task | None:
        return self.db.scalar(
            select(Task)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.id == task_id,
            )
            .with_for_update()
        )

    def claim_task_for_user(
        self, project_id: int, sprint_id: int, task_id: int, user_id: int
    ) -> Task | None:
        updated_id = self.db.scalar(
            update(Task)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.id == task_id,
                Task.status == TaskStatus.TODO,
                or_(Task.worker_id.is_(None), Task.worker_id == user_id),
            )
            .values(worker_id=user_id, status=TaskStatus.IN_PROGRESS)
            .returning(Task.id)
        )

        if updated_id is None:
            return None

        return self.db.get(Task, updated_id, populate_existing=True)

    def send_assigned_task_to_review(
        self, project_id: int, sprint_id: int, task_id: int, user_id: int
    ) -> Task | None:
        updated_id = self.db.scalar(
            update(Task)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.id == task_id,
                Task.worker_id == user_id,
                Task.status == TaskStatus.IN_PROGRESS,
            )
            .values(status=TaskStatus.REVIEW)
            .returning(Task.id)
        )

        if updated_id is None:
            return None

        return self.db.get(Task, updated_id, populate_existing=True)

    def accept_reviewed_task(
        self, project_id: int, sprint_id: int, task_id: int, reviewer_id: int
    ) -> Task | None:
        updated_id = self.db.scalar(
            update(Task)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.id == task_id,
                Task.worker_id.is_not(None),
                Task.worker_id != reviewer_id,
                Task.status == TaskStatus.REVIEW,
            )
            .values(status=TaskStatus.DONE)
            .returning(Task.id)
        )

        if updated_id is None:
            return None

        return self.db.get(Task, updated_id, populate_existing=True)

    def decline_reviewed_task(
        self, project_id: int, sprint_id: int, task_id: int, reviewer_id: int
    ) -> Task | None:
        updated_id = self.db.scalar(
            update(Task)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.id == task_id,
                Task.worker_id.is_not(None),
                Task.worker_id != reviewer_id,
                Task.status == TaskStatus.REVIEW,
            )
            .values(status=TaskStatus.REJECTED)
            .returning(Task.id)
        )

        if updated_id is None:
            return None

        return self.db.get(Task, updated_id, populate_existing=True)

    def renew_rejected_task(
        self, project_id: int, sprint_id: int, task_id: int, user_id: int
    ) -> Task | None:
        updated_id = self.db.scalar(
            update(Task)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.id == task_id,
                Task.worker_id == user_id,
                Task.status == TaskStatus.REJECTED,
            )
            .values(status=TaskStatus.IN_PROGRESS)
            .returning(Task.id)
        )

        if updated_id is None:
            return None

        return self.db.get(Task, updated_id, populate_existing=True)

    def all_tasks_of_sprint(
        self,
        project_id: int,
        sprint_id: int,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Task]:
        statement = (
            select(Task)
            .where(Task.project_id == project_id, Task.sprint_id == sprint_id)
            .order_by(Task.id)
        )

        return list(self.db.scalars(_apply_pagination(statement, limit, offset)).all())

    def tasks_todo(
        self,
        project_id: int,
        sprint_id: int,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Task]:
        statement = (
            select(Task)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.status == TaskStatus.TODO,
            )
            .order_by(Task.id)
        )

        return list(self.db.scalars(_apply_pagination(statement, limit, offset)).all())

    def tasks_in_progress(
        self,
        project_id: int,
        sprint_id: int,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Task]:
        statement = (
            select(Task)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.status == TaskStatus.IN_PROGRESS,
            )
            .order_by(Task.id)
        )

        return list(self.db.scalars(_apply_pagination(statement, limit, offset)).all())

    def tasks_on_review(
        self,
        project_id: int,
        sprint_id: int,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Task]:
        statement = (
            select(Task)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.status == TaskStatus.REVIEW,
            )
            .order_by(Task.id)
        )

        return list(self.db.scalars(_apply_pagination(statement, limit, offset)).all())

    def tasks_rejected(
        self,
        project_id: int,
        sprint_id: int,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Task]:
        statement = (
            select(Task)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.status == TaskStatus.REJECTED,
            )
            .order_by(Task.id)
        )

        return list(self.db.scalars(_apply_pagination(statement, limit, offset)).all())

    def tasks_done(
        self,
        project_id: int,
        sprint_id: int,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Task]:
        statement = (
            select(Task)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.status == TaskStatus.DONE,
            )
            .order_by(Task.id)
        )

        return list(self.db.scalars(_apply_pagination(statement, limit, offset)).all())

    def tasks_created_by_user(
        self,
        project_id: int,
        sprint_id: int,
        creator_id: int,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Task]:
        statement = (
            select(Task)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.creator_id == creator_id,
            )
            .order_by(Task.id)
        )

        return list(self.db.scalars(_apply_pagination(statement, limit, offset)).all())

    def tasks_assigned_to_user(
        self,
        project_id: int,
        sprint_id: int,
        worker_id: int,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Task]:
        statement = (
            select(Task)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.worker_id == worker_id,
            )
            .order_by(Task.id)
        )

        return list(self.db.scalars(_apply_pagination(statement, limit, offset)).all())

    def rejected_tasks_assigned_to_user(
        self,
        project_id: int,
        sprint_id: int,
        worker_id: int,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Task]:
        statement = (
            select(Task)
            .where(
                Task.project_id == project_id,
                Task.sprint_id == sprint_id,
                Task.worker_id == worker_id,
                Task.status == TaskStatus.REJECTED,
            )
            .order_by(Task.id)
        )

        return list(self.db.scalars(_apply_pagination(statement, limit, offset)).all())
