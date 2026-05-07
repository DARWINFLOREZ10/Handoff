# FlowForge Platform

FlowForge Platform is a production-oriented, multi-tenant workflow automation backend built with FastAPI, PostgreSQL, Redis, Celery, and JWT-based authentication.

## Core capabilities

- User authentication with email/password and Google OAuth
- Multi-tenant organizations with membership-based roles
- Workflow creation, execution, retries, cancellation, and history
- Background jobs for email delivery, webhooks, API calls, report generation, and scheduled cleanup
- Organization-aware rate limiting with plan-based policies
- Audit logging for critical security and operational events
- Reports for executions, success rate, duration, and usage
- API key management for service integrations

## Stack

- Python 3.12
- FastAPI
- PostgreSQL
- Redis
- Celery and Celery Beat
- SQLAlchemy 2.0
- Alembic
- JWT and OAuth
- Docker and Docker Compose
- GitHub Actions

## Local development

1. Create a virtual environment with Python 3.12.
2. Install dependencies:

```bash
pip install -e ".[dev]"
```

3. Copy the example environment file:

```bash
copy .env.example .env
```

4. Start the infrastructure:

```bash
docker compose up --build
```

5. Run the API locally:

```bash
uvicorn flowforge.main:app --reload
```

## Project structure

- `src/flowforge/core` contains settings, security helpers, and logging.
- `src/flowforge/db` contains the SQLAlchemy base, session, and domain models.
- `src/flowforge/api` contains dependencies and HTTP routers.
- `src/flowforge/workers` contains Celery application and task definitions.

## Deployment guidance

For the first production release, Render or Railway is the recommended target because they reduce operational overhead while preserving a clean path to PostgreSQL, Redis, and container-based deployment.

AWS or Azure can be introduced later when the platform needs more control over networking, observability, or compliance.
