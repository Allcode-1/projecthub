# ProjectHub

## Engineering Focus

- RS256 JWT authentication with refresh-session rotation.
- Project-level RBAC: owner, admin, worker, viewer.
- Invite-based project membership and member self-leave flow.
- Sprint lifecycle: planned -> active -> closed.
- Task workflow: TODO -> IN_PROGRESS -> REVIEW -> DONE / REJECTED.
- Concurrency-safe task claiming and refresh-token reuse protection.
- Row-locking around invite accept/decline flows.
- Service-layer transaction boundaries.
- PostgreSQL constraints and indexes for workflow queries.
- Redis cache-aside for project and sprint lists.
- Redis-backed login rate limiting.
- Limit/offset pagination for list endpoints.
- Redis-backed mutation rate limiting for authenticated write actions.
- Celery Beat + RabbitMQ sprint lifecycle synchronization.
- Structured JSON logs for HTTP requests and Celery tasks.
- Liveness/readiness health endpoints.
- Security and dependency audit tooling.
- GitHub Actions CI quality gates and Docker Compose smoke checks.
- Docker Compose healthchecks, migration startup flow, and JWT key secrets.
- Load and concurrency smoke scripts for a running API.
- Pytest integration coverage, Ruff, Mypy, Alembic sync checks.

## Backend Design

Business logic lives in services, repositories isolate SQLAlchemy access, and
dependencies handle authentication, authorization, and nested resource loading.

The backend treats PostgreSQL as the source of truth. Redis and RabbitMQ support
specific operational concerns: cached reads, login rate limiting, and scheduled
sprint lifecycle synchronization.

Important command flows are protected with database-level consistency patterns:

- task claiming uses conditional `UPDATE ... WHERE current_state ... RETURNING`;
- refresh-token rotation revokes active sessions through conditional update;
- invite accept/decline uses row locks;
- invalid workflow transitions return application-level `409` errors.

## Engineering Decisions

**Why RS256 instead of HS256?**
RS256 keeps signing and verification responsibilities separate through a private
and public key pair. It is heavier than a shared secret, but it models a more
realistic token setup where only the auth service needs the private key.

**Why services and repositories?**
Workflow rules such as task review, invite acceptance, sprint transitions, and
project leaving belong in services because they combine validation, state
changes, and transactions. Repositories stay focused on SQLAlchemy queries.

**Why conditional updates for task claiming?**
Two users can try to take the same task at the same time. A Python-level check
is not enough. The claim operation is guarded by the database so only one update
can match the expected state.

**Why cache-aside?**
Project and sprint lists are read-heavy and easy to rebuild from PostgreSQL.
Cache-aside keeps PostgreSQL authoritative while Redis improves common read
paths.

## Authentication

The authentication flow includes registration, login, bcrypt password hashing,
RS256 access/refresh JWTs, refresh sessions in PostgreSQL, refresh-token
rotation, logout/revoke, and a current-user endpoint.

Login is protected by Redis-backed rate limiting using both client IP and
username keys.

## Authorization / RBAC

ProjectHub uses project-level roles:

- `owner`: owns the project and controls project-level settings.
- `admin`: manages invites, sprints, tasks, and task reviews.
- `worker`: takes tasks, works on assigned tasks, and reads decline comments.
- `viewer`: has read-only access to project data.

Project-level permissions are checked in dependencies. Object-level rules are
enforced in services. Nested resource consistency is also validated:

```text
project_id -> sprint_id -> task_id
```

More details are documented in [RBAC](docs/RBAC.md).

## Observability

HTTP requests are logged as structured JSON with:

- request id;
- method and path;
- status code;
- duration in milliseconds;
- client IP.

Every response includes an `X-Request-ID` header. If a caller sends
`X-Request-ID`, the API keeps it; otherwise the middleware generates one.

Celery tasks also emit structured lifecycle logs for task start, finish, and
failure without logging task arguments.

Configure log level with:

```env
LOG_LEVEL=INFO
```

## Health Checks

The API exposes:

```text
GET /health
GET /health/live
GET /health/ready
```

`/health/live` confirms that the application process is alive.

`/health/ready` checks runtime dependencies:

- PostgreSQL: required;
- Redis: required by default;
- RabbitMQ: reported, optional by default for the API process.

Readiness behavior can be adjusted with:

```env
READINESS_REQUIRE_REDIS=true
READINESS_REQUIRE_RABBITMQ=false
HEALTHCHECK_TIMEOUT_SECONDS=1.0
```

## Redis

Redis is used for:

- cache-aside reads for project and sprint lists;
- login rate limiting by IP and username;
- authenticated mutation rate limiting by user and IP.

Cached values are JSON-serialized, validated with Pydantic on read, stored with
TTL + jitter, and invalidated after key mutations. Paginated list pages use
page-aware cache keys and pattern invalidation for all cached pages belonging to
the changed project or user. Cached query failures fall back to PostgreSQL.

## Pagination And Limits

List endpoints accept bounded pagination parameters:

```text
?limit=50&offset=0
```

Defaults and caps are configurable:

```env
PAGINATION__DEFAULT_LIMIT=50
PAGINATION__MAX_LIMIT=100
```

Auth and write-heavy endpoints are rate limited through Redis. Login uses
separate IP and username buckets. Authenticated mutations use user and IP
buckets. `429` responses include `Retry-After`.

## Celery / Background Jobs

The Docker Compose stack includes RabbitMQ, a Celery worker, and Celery Beat.
Celery Beat schedules a sprint lifecycle synchronization job that periodically:

- activates planned sprints whose start time has arrived;
- closes planned/active sprints whose end time has passed;
- invalidates affected sprint-list cache keys.

## Security And Dependency Audit

Static code security scan:

```bash
uv run bandit -q -r app -ll
```

Known dependency vulnerability audit:

```bash
uv run pip-audit
```

These checks are not a replacement for manual auth/RBAC review, but they catch
known vulnerable packages and common unsafe Python patterns.

## CI And Quality Gates

The GitHub Actions workflow in `.github/workflows/ci.yml` runs the backend
quality gates against PostgreSQL, Redis, and RabbitMQ service containers.

CI checks:

```bash
uv lock --check
uv run ruff check .
uv run mypy app tests
uv run bandit -q -r app -ll
uv run pip-audit
uv run alembic upgrade head
uv run alembic check
uv run pytest -q
docker build -t project-hub:ci .
```

The CI job also generates a temporary RS256 key pair and creates separate
PostgreSQL databases for application migration checks and destructive tests.

A separate Compose smoke job builds and starts the Docker Compose stack, waits
for `/health/ready`, then runs the live concurrency and read-load smoke scripts
against `http://localhost:8000`.

## Testing

Run the main test suite:

```bash
uv run pytest -q
```

Run quality checks:

```bash
uv run ruff check .
uv run mypy app tests
uv run alembic check
uv lock --check
```

The test suite covers core API flows: auth, refresh rotation, projects, invites,
membership, sprints, task workflow actions, review comments, cache invalidation,
and sprint lifecycle jobs. Redis is isolated in tests with an in-memory fake.

## Load And Concurrency Smoke Tests

Smoke scripts live under `tests/smoke/` and run against a real running API. They
are separate from the normal pytest suite because they mutate live data and
depend on PostgreSQL, Redis, RabbitMQ, and the API process being up.

Run concurrency smoke checks:

```bash
uv run python tests/smoke/concurrency_smoke.py --base-url http://localhost:8000
```

This checks:

- many workers racing to claim the same task;
- many refresh requests racing to reuse one refresh token;
- many invite accept requests racing on the same invite.

Expected behavior is exactly one successful request and the rest controlled
`409` or `401` responses.

Run a small read-load smoke check:

```bash
uv run python tests/smoke/load_smoke.py \
  --base-url http://localhost:8000 \
  --requests 100 \
  --concurrency 20
```

This creates a user/project and sends concurrent authenticated reads to the
project list endpoint, then prints p50/p95/max latency.

## Docker Compose

The repository includes Docker Compose services for the API, PostgreSQL, Redis,
RabbitMQ, a one-shot Alembic migration, Celery worker, and Celery Beat.

Generate JWT keys in `certs/`, then start the stack from the repository root:

```bash
mkdir -p certs
openssl genrsa -out certs/private.pem 2048
openssl rsa -in certs/private.pem -pubout -out certs/public.pem
chmod 644 certs/private.pem certs/public.pem
docker compose up -d --build
```

Compose includes healthchecks for PostgreSQL, Redis, RabbitMQ, and the API. A
one-shot `migrate` service runs `alembic upgrade head` after PostgreSQL becomes
healthy. The API, worker, and beat services wait for that command to finish
successfully before they start. If the database is already at the latest
Alembic revision, the migration exits without changing data.

The API image runs as a non-root user. JWT keys stay outside the image and are
mounted into API/worker/beat containers as Docker secrets. On Linux, the key
files must be readable by the non-root container user; the `chmod` command above
keeps the local Compose setup simple for development and CI.

Check the API:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

Interactive API docs:

```text
http://localhost:8000/docs
```

## Local Development

Create a `.env` file for non-Docker runs:

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/project_hub
TEST_DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/project_hub_test
REDIS_URL=redis://localhost:6390/0
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
LOG_LEVEL=INFO
READINESS_REQUIRE_REDIS=true
READINESS_REQUIRE_RABBITMQ=false
AUTH_JWT__PRIVATE_KEY_PATH=certs/private.pem
AUTH_JWT__PUBLIC_KEY_PATH=certs/public.pem
DATABASE__POOL_SIZE=5
DATABASE__MAX_OVERFLOW=10
DATABASE__POOL_TIMEOUT_SECONDS=30
DATABASE__POOL_RECYCLE_SECONDS=1800
DATABASE__POOL_PRE_PING=true
DATABASE__CONNECT_TIMEOUT_SECONDS=5
DATABASE__STATEMENT_TIMEOUT_MS=30000
SENDER_EMAIL=your-email@example.com
SMTP_PASSWORD=your-smtp-password
SMTP_HOSTNAME=smtp.gmail.com
SMTP_PORT=587
```

Install dependencies:

```bash
uv sync
```

Run migrations:

```bash
uv run alembic upgrade head
```

Start the API:

```bash
uv run uvicorn app.main:app --reload
```

## API Overview

The API covers these main areas:

- Auth: register, login, refresh, logout, current user.
- Projects: create, read, update, delete, list accessible projects.
- Project members: list members and leave joined project.
- Invites: invite users, accept/decline invites, list received invites.
- Sprints: create, update, start, close, list project sprints.
- Tasks: create, assign, filter by status, take to work, send to review,
  accept, decline, resume rejected tasks.
- Review comments: read decline comments visible to the assigned worker.

See the interactive OpenAPI documentation for the complete endpoint list:

```text
http://localhost:8000/docs
```
