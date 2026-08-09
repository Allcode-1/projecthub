import argparse
import asyncio
from time import perf_counter
from uuid import uuid4

import httpx

DEFAULT_PASSWORD = "secret123"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return ordered[index]


async def _expect(response: httpx.Response, status_code: int) -> dict:
    if response.status_code != status_code:
        raise RuntimeError(
            f"{response.request.method} {response.request.url.path} expected "
            f"{status_code}, got {response.status_code}: {response.text}"
        )

    if response.content:
        return response.json()

    return {}


async def _register_and_login(client: httpx.AsyncClient, username: str) -> str:
    await _expect(
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
    return tokens["access_token"]


async def _create_project(client: httpx.AsyncClient, token: str) -> None:
    await _expect(
        await client.post(
            "/api/v1/projects/",
            json={"name": "Load project", "description": "Load smoke"},
            headers=_headers(token),
        ),
        201,
    )


async def _check_ready(client: httpx.AsyncClient) -> None:
    response = await client.get("/health/ready")
    if response.status_code != 200:
        raise RuntimeError(f"API is not ready: {response.status_code} {response.text}")


async def _timed_get_projects(
    client: httpx.AsyncClient, token: str
) -> tuple[int, float]:
    started_at = perf_counter()
    response = await client.get("/api/v1/projects/", headers=_headers(token))
    elapsed_ms = (perf_counter() - started_at) * 1000
    return response.status_code, elapsed_ms


async def run(
    base_url: str,
    requests: int,
    concurrency: int,
    timeout: float,
) -> None:
    run_id = uuid4().hex[:10]
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        await _check_ready(client)
        token = await _register_and_login(client, f"load-user-{run_id}")
        await _create_project(client, token)

        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_request() -> tuple[int, float]:
            async with semaphore:
                return await _timed_get_projects(client, token)

        results = await asyncio.gather(*[bounded_request() for _ in range(requests)])

    statuses = [status for status, _elapsed in results]
    durations = [elapsed for _status, elapsed in results]
    failures = [status for status in statuses if status != 200]

    if failures:
        raise RuntimeError(f"Expected only 200 responses, got statuses={statuses}")

    print(
        "load_smoke ok "
        f"requests={requests} concurrency={concurrency} "
        f"p50_ms={_percentile(durations, 0.50):.2f} "
        f"p95_ms={_percentile(durations, 0.95):.2f} "
        f"max_ms={max(durations):.2f}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ProjectHub read load smoke test.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    asyncio.run(run(args.base_url, args.requests, args.concurrency, args.timeout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
