# Architecture

## Overview

ProjectHub is a synchronous FastAPI backend for Jira-like project management
workflows: projects, members, invites, sprints, tasks, task reviews, and
review comments.

PostgreSQL is the source of truth. Redis supports cache-aside reads and login
rate limiting. RabbitMQ, Celery worker, and Celery Beat run scheduled sprint
lifecycle synchronization. Operational concerns are covered by structured
logging, health/readiness checks, Docker Compose, and GitHub Actions quality
gates.

```text
Client
  |
  v
FastAPI router
  |
  +-> Dependencies: authentication, RBAC, resource loading
  |
  v
Service: business rules and transaction boundary
  |
  v
Repository: SQLAlchemy queries and conditional updates
  |
  v
PostgreSQL

Query service -> Redis cache -> Repository fallback
Celery Beat -> RabbitMQ -> Celery worker -> PostgreSQL/Redis invalidation
```

## Main Components

| Component | Location | Responsibility |
|---|---|---|
| API routers | `app/api/v1/` | HTTP contract, dependencies, response models |
| Auth routes | `app/auth/` | Registration, login, refresh rotation, logout |
| Dependencies | `app/dependencies/` | Authentication, RBAC, nested resource consistency |
| Services | `app/services/` | Business actions, workflow state, transactions |
| Repositories | `app/repositories/` | SQLAlchemy reads, locks, conditional updates |
| Models | `app/models/` | SQLAlchemy tables, enums, constraints, indexes |
| Schemas | `app/schemas/` | Pydantic request and response contracts |
| Cache | `app/cache/` | Redis keys, serialization, TTL, invalidation helpers |
| Jobs | `app/jobs/` | Celery app and sprint lifecycle task |
| Core | `app/core/` | Settings, errors, health checks, structured logging |
| Database | `app/db/` | Engine, sessions, declarative base |
| Migrations | `alembic/` | Database schema history |
| Tests | `tests/` | Integration, negative, cache, lifecycle, smoke coverage |

## Domain Structure

```text
Project
  |
  +-- has members/invites
  |
  +-- contains -----------> Sprint
                             |
                             +-- contains -> Task
                                             |
                                             +-- has -> ReviewComment
```

Important ownership rules:

- A project has one owner through `projects.owner_id`.
- Non-owner access is stored in `project_members` with `viewer`, `worker`, or
  `admin` role.
- A sprint belongs to one project.
- A task belongs to one project and one sprint.
- A review comment belongs to one task.
- A task worker must belong to the same project when assigned through the API.
- A project owner cannot leave their own project through member self-leave.

## Request Flow

### Command request

Example: decline a task with an optional review comment.

1. The router authenticates the user.
2. Dependencies load project, sprint, and task records.
3. RBAC dependencies require owner/admin project management access.
4. Nested dependencies verify that `project_id`, `sprint_id`, and `task_id`
   describe the same object hierarchy.
5. The service validates sprint and task workflow state.
6. The service uses a conditional update so the database verifies the expected
   current task state.
7. The service optionally creates a review comment.
8. The task state change and comment insert are committed in one transaction.

### Cached query

Project and sprint list queries use cache-aside behavior:

1. Accept bounded `limit` and `offset` pagination parameters.
2. Try to read the requested page from Redis.
2. Validate cached JSON with Pydantic.
3. On a miss or invalid value, read from PostgreSQL.
4. Store the serialized response in Redis with TTL and jitter.
5. Invalidate all cached pages for the affected user or project after writes.
6. On Redis failures, log the error and fall back to PostgreSQL.

Cache invalidation is performed after mutations that change project or sprint
list visibility.

### Background lifecycle

Celery Beat periodically publishes a sprint lifecycle sync task to RabbitMQ.
A Celery worker consumes the message and:

1. activates planned sprints whose start time has arrived;
2. closes planned/active sprints whose end time has passed;
3. invalidates sprint-list cache keys for affected projects.

### Health/readiness

The API exposes:

```text
GET /health
GET /health/live
GET /health/ready
```

Liveness confirms the API process is running. Readiness checks runtime
dependencies:

- PostgreSQL is required.
- Redis is required by default.
- RabbitMQ is reported and optional by default for the API process.

## Authorization Boundaries

Authorization is split into two levels:

- Dependencies check project-level access such as view, task work, or
  management.
- Services check object-level and workflow rules such as task assignment,
  owner-only project changes, original invite sender, and current state.

Resource dependencies keep nested identifiers consistent:

```text
project_id -> sprint.project_id -> task.sprint_id/project_id
```

Detailed permissions are documented in [RBAC.md](RBAC.md).

## Transactions And Concurrency

Business services own transaction boundaries and call `commit()` after
successful state changes.

Examples:

- Registration catches unique username/email conflicts and returns `409`.
- Refresh-token rotation revokes an active refresh session through conditional
  `UPDATE ... RETURNING`, so one refresh token can be used only once.
- Logout uses the same active-session revocation pattern.
- Accepting an invite locks the invite row, changes its status, creates project
  membership, and commits atomically.
- Task claiming uses conditional `UPDATE ... WHERE status = TODO ... RETURNING`
  so concurrent claim attempts produce exactly one winner.
- Task edit/delete locks the row with `FOR UPDATE` and allows only `TODO`
  tasks in open sprints.
- Sprint state transitions are service-validated: planned -> active -> closed.

PostgreSQL remains authoritative even when Redis or RabbitMQ is unavailable.

## Database Hardening

Schema-level guardrails complement service-level validation:

- `projects.name` and `tasks.title` have minimum-length check constraints.
- `sprints` enforce valid date ordering and required timestamps for active and
  closed states.
- `project_members` has a unique `(project_id, user_id)` constraint.
- `project_invites` has a partial unique index for one pending invite per
  `(project_id, send_to)`.
- Task workflow queries have indexes by project, sprint, worker, and status.
- Sprint lifecycle jobs use indexes by project/status and lifecycle timestamps.
- Refresh sessions are indexed by user and expiration time.
- Foreign-key delete behavior preserves history where appropriate with
  `SET NULL`, cascades owned children, and restricts project owner deletion.

Runtime database access uses explicit SQLAlchemy pool settings, connection
pre-ping, pool recycle, connect timeout, and PostgreSQL statement timeout.
These settings are configured through `DATABASE__...` environment variables.

Alembic migrations are the source of schema history, and CI runs both
`alembic upgrade head` and `alembic check`.

## Endpoint Limits

List endpoints use bounded `limit`/`offset` pagination. Auth endpoints are
rate limited by IP, with login also rate limited by username. Authenticated
state-changing endpoints are rate limited by both user id and client IP.
Rate-limit responses include `Retry-After`.

## Observability

HTTP requests are logged as structured JSON with request id, method, path,
client IP, status code, and duration. Every response includes `X-Request-ID`.
If the caller sends this header, the middleware keeps it; otherwise it
generates a new id.

Celery tasks log lifecycle events for task start, finish, and failure without
logging task arguments.

Log level is controlled with:

```env
LOG_LEVEL=INFO
```

## Runtime Packaging

The Docker image:

- installs locked production dependencies with `uv`;
- runs the API through `uvicorn`;
- uses a non-root application user;
- exposes a container healthcheck against `/health/live`.

Docker Compose includes PostgreSQL, Redis, RabbitMQ, API, a one-shot Alembic
migration service, Celery worker, and Celery Beat. API, worker, and beat wait
for the migration service to complete successfully and read JWT key files from
Docker secrets mounted from `./certs`.

## Testing And CI

The main pytest suite covers auth, refresh rotation, projects, invites,
membership, sprints, task workflow, review comments, cache invalidation, and
sprint lifecycle jobs. Redis is isolated in tests with an in-memory fake.

Smoke scripts under `tests/smoke/` run against a live API:

- concurrency smoke: task claim race, refresh-token reuse race, invite accept
  race;
- load smoke: concurrent authenticated reads against the project list endpoint.

GitHub Actions runs:

- lockfile check;
- Ruff;
- Mypy;
- Bandit;
- `pip-audit`;
- Alembic upgrade and migration diff check;
- pytest;
- Docker image build;
- Docker Compose startup with live concurrency/load smoke checks.

## Current Production Gaps

ProjectHub is production-friendly as a backend portfolio project, but it is not
a fully operated production system yet.

Remaining production work:

- deployment documentation for VPS/cloud runtime, reverse proxy, TLS, and DNS;
- secret rotation policy and separate environment-specific secrets;
- metrics/tracing beyond structured logs;
- backup/restore runbooks for PostgreSQL and persistent Redis/RabbitMQ data;
- full RBAC matrix tests for every command endpoint;
- heavier load tests against a production-like PostgreSQL instance;
- refresh-session cleanup job for expired sessions;
- security review of auth, RBAC, CORS, headers, and abuse scenarios.
