# Development Log

This file records completed and verified work only. Planned work belongs in
`PENDING_DEVELOPMENT.md`.

## 2026-11-07 — Stage 1: Repository Analysis (Planning)

- Repository root was empty (0 files, no `.git`). Greenfield project.
- Environment: Windows, PowerShell 5.1, Python 3.11.9, pip 24.0, git 2.51.1.
- Docker was installed but excluded by project owner instruction.
- PostgreSQL client `psql` was not available.
- Installed globally before project setup: `streamlit`, `pytest`, `pandas`,
  `numpy`, `uvicorn`.
- No `GEMINI_API_KEY`, PayPal credentials, or `DATABASE_URL` were set.
- Network reachability confirmed for PyPI, Gemini, and PayPal sandbox endpoints.
- Timezone: India Standard Time.
- Decision: SQLite default, PostgreSQL optional via `DATABASE_URL`.
- Decision: AI and payments behind adapter interfaces with deterministic mocks.
- Decision: deterministic claims engine is the sole financial authorizer.
- No application code was written during this stage.

## 2026-11-07 — Stage 2: Architecture and Plan Approved

- Presented repository analysis, stack, database design, API design, module
  breakdown, milestones, risks, and initial documentation drafts.
- Owner approved development and instructed: no Docker, no git operations.
- Owner later instructed that dependency installation is deferred to the owner
  upon completion of development. No further installs were run after that.

## 2026-11-07 — Milestone M0: Foundation (COMPLETED)

### Implemented

- Project scaffold and package layout.
- Environment-driven settings with Pydantic Settings.
  - Validates app environment, provider selection, and required credentials.
  - Rejects default demo API keys in `APP_ENV=production`.
- Structured JSON logging with a request ID context variable.
- Consistent error envelope: `error.code`, `error.message`, `error.details`,
  `error.request_id`.
  - Handlers for application errors, validation errors, integrity conflicts,
    and unhandled exceptions.
- SQLAlchemy 2.0 engine and session.
  - SQLite WAL mode and foreign-key enforcement.
  - PostgreSQL-compatible configuration through `DATABASE_URL`.
- Declarative base with constraint naming conventions.
- API-key authentication and role enforcement.
  - SHA-256 hashed keys with display prefix only.
  - Roles: `admin`, `operator`, `reviewer`, `read_only`.
  - Seeded from environment or `.env`.
- Append-only, hash-chained audit log.
  - `GENESIS` anchor, `prev_hash`, SHA-256 digest, request ID.
- Idempotency key model and service.
  - Replay returns stored response metadata.
  - Same key with a different request hash returns HTTP 409.
  - In-progress replay returns HTTP 409.
- Health and readiness endpoints.
- Request ID middleware with `X-Request-ID` propagation.
- Admin-only audit read API.
- Alembic environment and initial migration.
- Seed entry point (`python -m app.seed`).

### Files created

- Configuration and repository metadata:
  - `requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini`
- Application:
  - `app/__init__.py`, `app/main.py`, `app/seed.py`
  - `app/core/__init__.py`, `app/core/config.py`, `app/core/logging.py`,
    `app/core/errors.py`, `app/core/security.py`
  - `app/db/__init__.py`, `app/db/base.py`, `app/db/session.py`,
    `app/db/init_db.py`
  - `app/models/__init__.py`, `app/models/api_key.py`, `app/models/audit.py`,
    `app/models/idempotency.py`
  - `app/schemas/__init__.py`, `app/schemas/auth.py`, `app/schemas/audit.py`
  - `app/api/__init__.py`, `app/api/v1/__init__.py`, `app/api/v1/router.py`,
    `app/api/v1/auth.py`, `app/api/v1/audit.py`
  - `app/services/__init__.py`, `app/services/bootstrap.py`,
    `app/services/audit.py`, `app/services/idempotency.py`
- Tests:
  - `tests/conftest.py`, `tests/test_health.py`, `tests/test_auth.py`,
    `tests/test_audit.py`, `tests/test_idempotency.py`
- Migrations:
  - `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`,
    `alembic/versions/0001_initial.py`
- Documentation:
  - `README.md`, `ARCHITECTURE.md`, `TESTING.md`, `DEVELOPMENT_LOG.md`,
    `PENDING_DEVELOPMENT.md`

### Implemented APIs

| Method | Path | Role | Verified |
|---|---|---|---|
| GET | `/health` | public | Yes |
| GET | `/ready` | public | Yes |
| GET | `/api/v1/auth/me` | any valid key | Yes |
| GET | `/api/v1/audit` | admin | Yes |

### Database objects implemented

- `api_keys`
- `audit_logs`
- `idempotency_keys`

### Tests executed and actual results

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

```
............                                                             [100%]
12 passed, 1 warning in 0.73s
```

Warning: `StarletteDeprecationWarning` from FastAPI `TestClient` about `httpx`.
No functional impact.

Additional verification:

- `python -m alembic upgrade head` -> applied `0001_initial`, `alembic current`
  reported `0001_initial (head)`.
- `python -m app.seed` -> database initialized and API keys seeded.
- Live Uvicorn smoke test on port 8011:
  - `/health` -> `{"status":"ok","app":"PCMSC","version":"0.1.0","env":"development"}`
  - `/ready` -> `{"status":"ready"}`
  - `/api/v1/auth/me` with admin key -> `{"id":1,"name":"admin","role":"admin"}`

### Bugs fixed

- None observed in application behavior during M0 verification.
- Note: FastAPI 0.162 / Starlette 1.10 keep included routers nested, so naive
  `APIRoute` introspection on the top-level app shows only root routes. Actual
  routing was verified through `TestClient` and a live Uvicorn server.

### Current working state

- Milestone M0 is complete and verified.
- Application boots, initializes the database, seeds roles, and serves the
  documented endpoints.
- No domain functionality exists yet (no shipments, policies, telemetry,
  evidence, fraud, claims, settlement, payment, or dashboard).
- Awaiting approval to start Milestone M1.
