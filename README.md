# ProjectHub

ProjectHub is a FastAPI backend API for Jira-like project management workflows.

This is a backend engineering portfolio project focused on authentication,
project-level RBAC, workflow consistency, PostgreSQL modeling, Redis,
Celery/RabbitMQ, observability, security checks, Docker Compose, and integration
testing.

## Domain Model

ProjectHub models a project workspace where users create projects as owners,
invite teammates, manage project-level roles, create sprints, create tasks, let
workers take tasks, and review completed work.

Declined tasks can receive review comments, giving workers a feedback loop
before resuming work.

Task workflow:

```text
TODO -> IN_PROGRESS -> REVIEW -> DONE
REVIEW -> REJECTED -> IN_PROGRESS
```

Sprint workflow:

```text
PLANNED -> ACTIVE -> CLOSED
```

## Current Status

ProjectHub is a production-friendly backend portfolio project, not a complete
production product.

Currently implemented:

- auth and refresh sessions;
- project CRUD and project membership;
- invites;
- project-level RBAC;
- sprint/task workflows;
- concurrency-safe task claiming;
- stricter sprint/task state rules;
- project member self-leave flow;
- Redis cache/rate limiting;
- limit/offset pagination for list endpoints;
- database pool, pre-ping, connect timeout, and statement timeout settings;
- Celery sprint lifecycle synchronization;
- structured JSON logging;
- liveness/readiness health checks;
- security and dependency audit commands;
- GitHub Actions CI workflow;
- Docker Compose smoke job in CI;
- PostgreSQL constraints/indexes;
- Alembic migrations;
- Docker Compose with healthchecks, one-shot Alembic migration service, and key secrets;
- load/concurrency smoke scripts;
- integration tests.

Still planned:

- full RBAC matrix tests;
- production deployment docs;
- better sprint closing report/results;
- unfinished task migration between sprints;
- expired refresh session cleanup job.

## What This Project Is Not

- Not a production-ready Jira clone.
- Not a fullstack product.
- Not a microservice system.
- Not a complete RBAC platform.
- Not a high-traffic/load-testing project.
