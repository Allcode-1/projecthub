import argparse
import asyncio
from dataclasses import dataclass
from uuid import uuid4

import httpx

DEFAULT_PASSWORD = "secret123"


@dataclass(frozen=True)
class UserSession:
    id: int
    username: str
    access_token: str
    refresh_token: str


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _expect(response: httpx.Response, status_code: int) -> dict:
    if response.status_code != status_code:
        raise RuntimeError(
            f"{response.request.method} {response.request.url.path} expected "
            f"{status_code}, got {response.status_code}: {response.text}"
        )

    if response.content:
        return response.json()

    return {}


async def _register_and_login(client: httpx.AsyncClient, username: str) -> UserSession:
    user = await _expect(
        await client.post(
            "/auth/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": DEFAULT_PASSWORD,
            },
        ),
        201,
    )
    tokens = await _expect(
        await client.post(
            "/auth/login",
            data={"username": username, "password": DEFAULT_PASSWORD},
        ),
        200,
    )

    return UserSession(
        id=user["id"],
        username=username,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )


async def _create_project(client: httpx.AsyncClient, owner: UserSession) -> dict:
    return await _expect(
        await client.post(
            "/api/v1/projects/",
            json={"name": "Smoke project", "description": "Concurrency smoke"},
            headers=_headers(owner.access_token),
        ),
        201,
    )


async def _create_sprint(
    client: httpx.AsyncClient, owner: UserSession, project_id: int
) -> dict:
    return await _expect(
        await client.post(
            f"/api/v1/projects/{project_id}/sprints/",
            json={"name": "Smoke sprint", "description": "Concurrency smoke"},
            headers=_headers(owner.access_token),
        ),
        201,
    )


async def _create_task(
    client: httpx.AsyncClient,
    owner: UserSession,
    project_id: int,
    sprint_id: int,
) -> dict:
    return await _expect(
        await client.post(
            f"/api/v1/projects/{project_id}/sprints/{sprint_id}/tasks/",
            json={"title": "Smoke task", "description": "Claim race"},
            headers=_headers(owner.access_token),
        ),
        201,
    )


async def _invite_and_accept(
    client: httpx.AsyncClient,
    owner: UserSession,
    member: UserSession,
    project_id: int,
    access_level: str = "worker",
) -> dict:
    invite = await _expect(
        await client.post(
            f"/api/v1/projects/{project_id}/invites/users/{member.id}",
            json={"access_level": access_level},
            headers=_headers(owner.access_token),
        ),
        201,
    )
    return await _expect(
        await client.patch(
            f"/api/v1/invites/accept/{invite['id']}",
            headers=_headers(member.access_token),
        ),
        200,
    )


def _assert_one_success(
    statuses: list[int], success_code: int, failure_code: int
) -> None:
    success_count = statuses.count(success_code)
    failure_count = statuses.count(failure_code)

    if success_count != 1 or failure_count != len(statuses) - 1:
        raise RuntimeError(
            f"Expected exactly one {success_code} and the rest {failure_code}; "
            f"got statuses={statuses}"
        )


async def _check_ready(client: httpx.AsyncClient) -> None:
    response = await client.get("/health/ready")
    if response.status_code != 200:
        raise RuntimeError(f"API is not ready: {response.status_code} {response.text}")


async def _task_claim_race(
    client: httpx.AsyncClient, run_id: str, contenders: int
) -> None:
    owner = await _register_and_login(client, f"claim-owner-{run_id}")
    workers = [
        await _register_and_login(client, f"claim-worker-{run_id}-{index}")
        for index in range(contenders)
    ]
    project = await _create_project(client, owner)

    for worker in workers:
        await _invite_and_accept(client, owner, worker, project["id"])

    sprint = await _create_sprint(client, owner, project["id"])
    task = await _create_task(client, owner, project["id"], sprint["id"])

    responses = await asyncio.gather(
        *[
            client.patch(
                f"/api/v1/projects/{project['id']}/sprints/{sprint['id']}/tasks/"
                f"{task['id']}/take_task",
                headers=_headers(worker.access_token),
            )
            for worker in workers
        ]
    )
    statuses = [response.status_code for response in responses]
    _assert_one_success(statuses, 200, 409)
    print(f"task_claim_race ok statuses={statuses}")


async def _refresh_rotation_race(
    client: httpx.AsyncClient, run_id: str, contenders: int
) -> None:
    user = await _register_and_login(client, f"refresh-user-{run_id}")

    responses = await asyncio.gather(
        *[
            client.post(
                "/auth/refresh",
                json={"refresh_token": user.refresh_token},
            )
            for _ in range(contenders)
        ]
    )
    statuses = [response.status_code for response in responses]
    _assert_one_success(statuses, 200, 401)
    print(f"refresh_rotation_race ok statuses={statuses}")


async def _invite_accept_race(
    client: httpx.AsyncClient, run_id: str, contenders: int
) -> None:
    owner = await _register_and_login(client, f"invite-owner-{run_id}")
    recipient = await _register_and_login(client, f"invite-recipient-{run_id}")
    project = await _create_project(client, owner)
    invite = await _expect(
        await client.post(
            f"/api/v1/projects/{project['id']}/invites/users/{recipient.id}",
            json={"access_level": "worker"},
            headers=_headers(owner.access_token),
        ),
        201,
    )

    responses = await asyncio.gather(
        *[
            client.patch(
                f"/api/v1/invites/accept/{invite['id']}",
                headers=_headers(recipient.access_token),
            )
            for _ in range(contenders)
        ]
    )
    statuses = [response.status_code for response in responses]
    _assert_one_success(statuses, 200, 409)
    print(f"invite_accept_race ok statuses={statuses}")


async def run(base_url: str, contenders: int, timeout: float) -> None:
    run_id = uuid4().hex[:10]
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        await _check_ready(client)
        await _task_claim_race(client, run_id, contenders)
        await _refresh_rotation_race(client, run_id, contenders)
        await _invite_accept_race(client, run_id, contenders)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ProjectHub concurrency smoke tests."
    )
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--contenders", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    asyncio.run(run(args.base_url, args.contenders, args.timeout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
