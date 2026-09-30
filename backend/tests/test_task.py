from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.project import Project
from app.models.review_comment import ReviewComment
from app.models.sprint import Sprint
from app.models.task import Task
from app.models.user import User
from app.repositories.task import TaskRepository
from tests.helpers import (
    auth_headers,
    create_project,
    create_sprint,
    create_task,
    invite_and_accept_member,
    register_and_login,
)


def setup_project_with_worker(client):
    _, owner_tokens = register_and_login(client, username="owner")
    worker, worker_tokens = register_and_login(client, username="worker")
    project = create_project(client, owner_tokens["access_token"])
    invite_and_accept_member(
        client,
        owner_tokens["access_token"],
        worker_tokens["access_token"],
        project["id"],
        worker["id"],
        access_level="worker",
    )
    sprint = create_sprint(client, owner_tokens["access_token"], project["id"])
    return owner_tokens, worker, worker_tokens, project, sprint


def test_owner_can_create_task_assigned_to_project_worker(client):
    owner_tokens, worker, _, project, sprint = setup_project_with_worker(client)

    task = create_task(
        client,
        owner_tokens["access_token"],
        project["id"],
        sprint["id"],
        worker_id=worker["id"],
    )

    assert task["worker_id"] == worker["id"]
    assert task["status"] == "todo"


def test_owner_cannot_assign_task_to_user_outside_project(client):
    _, owner_tokens = register_and_login(client, username="owner")
    outsider, _ = register_and_login(client, username="outsider")
    project = create_project(client, owner_tokens["access_token"])
    sprint = create_sprint(client, owner_tokens["access_token"], project["id"])

    response = client.post(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/",
        json={
            "title": "Build API",
            "description": "Build useful API",
            "worker_id": outsider["id"],
        },
        headers=auth_headers(owner_tokens["access_token"]),
    )

    assert response.status_code == 404


def test_worker_can_take_task_send_to_review_and_owner_can_accept(client):
    owner_tokens, worker, worker_tokens, project, sprint = setup_project_with_worker(
        client
    )
    task = create_task(
        client,
        owner_tokens["access_token"],
        project["id"],
        sprint["id"],
    )

    take_response = client.patch(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
        f"{task['id']}/take_task",
        headers=auth_headers(worker_tokens["access_token"]),
    )
    review_response = client.patch(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
        f"{task['id']}/to_review",
        headers=auth_headers(worker_tokens["access_token"]),
    )
    accept_response = client.patch(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
        f"{task['id']}/accept",
        headers=auth_headers(owner_tokens["access_token"]),
    )

    assert take_response.status_code == 200
    assert take_response.json()["worker_id"] == worker["id"]
    assert take_response.json()["status"] == "in_progress"
    assert review_response.status_code == 200
    assert review_response.json()["status"] == "review"
    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == "done"


def test_assigned_worker_can_take_task(client):
    owner_tokens, worker, worker_tokens, project, sprint = setup_project_with_worker(
        client
    )
    task = create_task(
        client,
        owner_tokens["access_token"],
        project["id"],
        sprint["id"],
        worker_id=worker["id"],
    )

    response = client.patch(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
        f"{task['id']}/take_task",
        headers=auth_headers(worker_tokens["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_task_status_routes_return_task_lists(client):
    owner_tokens, _, _, project, sprint = setup_project_with_worker(client)
    task = create_task(
        client,
        owner_tokens["access_token"],
        project["id"],
        sprint["id"],
    )

    todo_response = client.get(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/todo",
        headers=auth_headers(owner_tokens["access_token"]),
    )
    done_response = client.get(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/done",
        headers=auth_headers(owner_tokens["access_token"]),
    )

    assert todo_response.status_code == 200
    assert todo_response.json()[0]["id"] == task["id"]
    assert done_response.status_code == 200
    assert done_response.json() == []


def test_task_list_supports_limit_and_offset(client):
    owner_tokens, _, _, project, sprint = setup_project_with_worker(client)
    first = create_task(
        client,
        owner_tokens["access_token"],
        project["id"],
        sprint["id"],
        title="Build API one",
    )
    second = create_task(
        client,
        owner_tokens["access_token"],
        project["id"],
        sprint["id"],
        title="Build API two",
    )
    third = create_task(
        client,
        owner_tokens["access_token"],
        project["id"],
        sprint["id"],
        title="Build API three",
    )

    response = client.get(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
        "?limit=1&offset=1",
        headers=auth_headers(owner_tokens["access_token"]),
    )

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [second["id"]]
    assert first["id"] < second["id"] < third["id"]


def test_user_task_lists(client):
    owner_tokens, worker, worker_tokens, project, sprint = setup_project_with_worker(
        client
    )
    task = create_task(
        client,
        owner_tokens["access_token"],
        project["id"],
        sprint["id"],
        worker_id=worker["id"],
    )

    mine_response = client.get(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/mine",
        headers=auth_headers(owner_tokens["access_token"]),
    )
    workspace_response = client.get(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/my_workspace",
        headers=auth_headers(worker_tokens["access_token"]),
    )
    worker_mine_response = client.get(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/mine",
        headers=auth_headers(worker_tokens["access_token"]),
    )

    assert mine_response.status_code == 200
    assert mine_response.json()[0]["id"] == task["id"]
    assert workspace_response.status_code == 200
    assert workspace_response.json()[0]["id"] == task["id"]
    assert worker_mine_response.status_code == 403


def test_project_admin_can_update_and_delete_task(client):
    _, owner_tokens = register_and_login(client, username="owner")
    admin, admin_tokens = register_and_login(client, username="admin")
    project = create_project(client, owner_tokens["access_token"])
    invite_and_accept_member(
        client,
        owner_tokens["access_token"],
        admin_tokens["access_token"],
        project["id"],
        admin["id"],
        access_level="admin",
    )
    sprint = create_sprint(client, owner_tokens["access_token"], project["id"])
    task = create_task(
        client,
        owner_tokens["access_token"],
        project["id"],
        sprint["id"],
    )

    update_response = client.patch(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/{task['id']}",
        json={"title": "Updated task"},
        headers=auth_headers(admin_tokens["access_token"]),
    )
    delete_response = client.delete(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/{task['id']}",
        headers=auth_headers(admin_tokens["access_token"]),
    )

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated task"
    assert delete_response.status_code == 204


def test_decline_task_creates_optional_review_comment(client, db_session):
    owner_tokens, worker, worker_tokens, project, sprint = setup_project_with_worker(
        client
    )
    commented_task_id = None

    for comment in ("Fix error handling", None):
        task = create_task(
            client,
            owner_tokens["access_token"],
            project["id"],
            sprint["id"],
            worker_id=worker["id"],
        )
        client.patch(
            f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
            f"{task['id']}/take_task",
            headers=auth_headers(worker_tokens["access_token"]),
        )
        client.patch(
            f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
            f"{task['id']}/to_review",
            headers=auth_headers(worker_tokens["access_token"]),
        )

        request_kwargs = {}
        if comment is not None:
            request_kwargs["json"] = {"comment": comment}
            commented_task_id = task["id"]

        decline_response = client.patch(
            f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
            f"{task['id']}/decline",
            headers=auth_headers(owner_tokens["access_token"]),
            **request_kwargs,
        )

        assert decline_response.status_code == 200
        assert decline_response.json()["status"] == "rejected"

    comments = list(db_session.scalars(select(ReviewComment)).all())

    assert len(comments) == 1
    assert comments[0].task_id == commented_task_id
    assert comments[0].comment == "Fix error handling"

    list_response = client.get(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
        "my_review_comments",
        headers=auth_headers(worker_tokens["access_token"]),
    )
    detail_response = client.get(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
        f"my_review_comments/{comments[0].id}",
        headers=auth_headers(worker_tokens["access_token"]),
    )
    owner_detail_response = client.get(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
        f"my_review_comments/{comments[0].id}",
        headers=auth_headers(owner_tokens["access_token"]),
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == comments[0].id
    assert detail_response.status_code == 200
    assert detail_response.json()["comment"] == "Fix error handling"
    assert owner_detail_response.status_code == 404


def test_viewer_cannot_take_task(client):
    _, owner_tokens = register_and_login(client, username="owner")
    viewer, viewer_tokens = register_and_login(client, username="viewer")
    project = create_project(client, owner_tokens["access_token"])
    invite_and_accept_member(
        client,
        owner_tokens["access_token"],
        viewer_tokens["access_token"],
        project["id"],
        viewer["id"],
        access_level="viewer",
    )
    sprint = create_sprint(client, owner_tokens["access_token"], project["id"])
    task = create_task(
        client, owner_tokens["access_token"], project["id"], sprint["id"]
    )

    response = client.patch(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
        f"{task['id']}/take_task",
        headers=auth_headers(viewer_tokens["access_token"]),
    )

    assert response.status_code == 403


def test_second_worker_cannot_claim_already_claimed_task(client):
    owner_tokens, worker, worker_tokens, project, sprint = setup_project_with_worker(
        client
    )
    other_worker, other_worker_tokens = register_and_login(client, username="worker2")
    invite_and_accept_member(
        client,
        owner_tokens["access_token"],
        other_worker_tokens["access_token"],
        project["id"],
        other_worker["id"],
        access_level="worker",
    )
    task = create_task(
        client,
        owner_tokens["access_token"],
        project["id"],
        sprint["id"],
    )

    first_response = client.patch(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
        f"{task['id']}/take_task",
        headers=auth_headers(worker_tokens["access_token"]),
    )
    second_response = client.patch(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
        f"{task['id']}/take_task",
        headers=auth_headers(other_worker_tokens["access_token"]),
    )

    assert worker["id"] != other_worker["id"]
    assert first_response.status_code == 200
    assert second_response.status_code == 409


def test_non_todo_task_cannot_be_updated_or_deleted(client):
    owner_tokens, _, worker_tokens, project, sprint = setup_project_with_worker(client)
    task = create_task(
        client,
        owner_tokens["access_token"],
        project["id"],
        sprint["id"],
    )
    client.patch(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
        f"{task['id']}/take_task",
        headers=auth_headers(worker_tokens["access_token"]),
    )

    update_response = client.patch(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/{task['id']}",
        json={"title": "Late edit"},
        headers=auth_headers(owner_tokens["access_token"]),
    )
    delete_response = client.delete(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/{task['id']}",
        headers=auth_headers(owner_tokens["access_token"]),
    )

    assert update_response.status_code == 409
    assert delete_response.status_code == 409


def test_closed_sprint_blocks_task_mutations(client):
    owner_tokens, _, _, project, sprint = setup_project_with_worker(client)
    start_response = client.patch(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/start",
        headers=auth_headers(owner_tokens["access_token"]),
    )
    close_response = client.patch(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/close",
        headers=auth_headers(owner_tokens["access_token"]),
    )
    create_response = client.post(
        f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/",
        json={"title": "Blocked task", "description": "Closed sprint task"},
        headers=auth_headers(owner_tokens["access_token"]),
    )

    assert start_response.status_code == 200
    assert close_response.status_code == 200
    assert create_response.status_code == 409


def test_task_claim_is_compare_and_set(db_session):
    owner = User(
        username="claim-owner",
        email="claim-owner@example.com",
        hashed_password="not-used",
    )
    first_worker = User(
        username="claim-worker-1",
        email="claim-worker-1@example.com",
        hashed_password="not-used",
    )
    second_worker = User(
        username="claim-worker-2",
        email="claim-worker-2@example.com",
        hashed_password="not-used",
    )
    db_session.add_all([owner, first_worker, second_worker])
    db_session.flush()

    project = Project(owner_id=owner.id, name="Claim project", description=None)
    db_session.add(project)
    db_session.flush()

    now = datetime.now(UTC)
    sprint = Sprint(
        project_id=project.id,
        creator_id=owner.id,
        name="Claim sprint",
        starts_at=now,
        ends_at=now + timedelta(days=14),
    )
    db_session.add(sprint)
    db_session.flush()

    task = Task(
        project_id=project.id,
        sprint_id=sprint.id,
        creator_id=owner.id,
        title="Claim task",
        description=None,
    )
    db_session.add(task)
    db_session.flush()

    task_repo = TaskRepository(db_session)

    first_claim = task_repo.claim_task_for_user(
        project.id, sprint.id, task.id, first_worker.id
    )
    second_claim = task_repo.claim_task_for_user(
        project.id, sprint.id, task.id, second_worker.id
    )

    assert first_claim is not None
    assert first_claim.worker_id == first_worker.id
    assert second_claim is None
