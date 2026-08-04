# PropertyManager Backend

FastAPI backend for PropertyManager. SQL Server via SQLAlchemy + pyodbc, JWT authentication, Pytest for tests.

## Prerequisites

- Python 3.14+ (this project was built and tested against 3.14.6)
- SQL Server reachable locally (SQLEXPRESS or similar) with the database already created - see [../database](../database) scripts 01-06
- ODBC Driver 17 for SQL Server installed (Windows: check with `Get-OdbcDriver` in PowerShell)

## Setup

```bash
cd backend
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and adjust values for your local setup (defaults assume `localhost\SQLEXPRESS` with Windows/trusted authentication - no username or password needed for local dev):

```bash
copy .env.example .env
```

## Running the server

```bash
venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Interactive Swagger docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health - returns `{"status": "ok", "database": "connected"}` if the app can reach SQL Server, or a 503 with `{"status": "degraded", ...}` if it can't.

## Running tests

```bash
venv\Scripts\python.exe -m pytest -v
```

`tests/test_health.py` connects to the real local database (no mocking) - it exists specifically to prove the FastAPI -> SQLAlchemy -> pyodbc -> SQL Server chain actually works end to end. Most other tests do too (real database, no mocked layers); ones that write data clean up their own throwaway rows afterward so the seeded demo dataset stays exactly as seeded (see `test_landlord_service.py`'s module docstring for why this project uses explicit cleanup rather than transaction-rollback fixtures).

## Authentication

Demo login (works against the seeded demo data from `database/06-seed-demo-data.sql`):

| Email | Role |
|---|---|
| sarah.mitchell@propertymanager.example | Administrator |
| james.carter@propertymanager.example | PropertyManager |
| priya.patel@propertymanager.example | PropertyManager |
| daniel.osei@propertymanager.example | MaintenanceEmployee |
| emma.wilson@propertymanager.example | ReadOnly |

Password for all five: `Password123!` (demo-only - never reuse a shared password like this for real accounts).

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"Email\":\"sarah.mitchell@propertymanager.example\",\"Password\":\"Password123!\"}"
```

Returns `{"access_token": "...", "refresh_token": "...", "token_type": "bearer"}`. Use the access token on protected routes:

```bash
curl http://127.0.0.1:8000/api/landlords -H "Authorization: Bearer <access_token>"
```

In Swagger (`/docs`), click **Authorize** and paste just the access token (no `Bearer ` prefix needed there - Swagger adds it).

**Hashing vs. encryption:** passwords are hashed (bcrypt), never encrypted - hashing is one-way, so even a full database leak doesn't recover anyone's actual password. See the docstring at the top of `app/core/security.py` for the full explanation, including why bcrypt specifically (not a fast hash like SHA-256) is the right tool.

**Access vs. refresh tokens:** the access token (30 min default) is sent with every request; the refresh token (7 days default) is used only to get a new access token via `POST /api/auth/refresh`, so users aren't forced to log in again every 30 minutes. Full explanation in `app/core/security.py`.

**Where the frontend should store these:** access token in memory (a React context/store), never `localStorage` - anything JavaScript can read, an XSS payload can read too. The refresh token ideally becomes an httpOnly cookie once the frontend exists (this backend currently returns it as a plain JSON field; wiring up cookie delivery is frontend-milestone work).

**Known security limitations of this implementation** (see `app/services/auth_service.py`'s module docstring for the full reasoning):
- Refresh tokens are stateless JWTs with no server-side revocation list - logout is a client-side token discard, not a real server-side invalidation. A production system handling anything sensitive would add a refresh-token table to make logout and "revoke this device" actually effective.
- Failed login attempts are tracked (`Users.FailedLoginAttempts`) but not yet enforced - there's no account lockout after N failures. Called out explicitly in the project scope as a later addition ("login rate limiting later").
- Every authenticated request queries the database (to confirm the account is still active and load current roles) rather than trusting claims embedded in the token - intentional, so a deactivated account or a role change takes effect immediately rather than only at next login/token-refresh, but worth knowing if this ever needs to scale to very high request volume.

## How the application starts

1. `app/main.py` creates the FastAPI app, configures logging (`app/core/logging_config.py`), registers CORS middleware and the centralized exception handlers (`app/core/exceptions.py`), then includes the API routers.
2. Settings (`app/core/config.py`) are loaded once from `.env` via `pydantic-settings` and cached with `@lru_cache` - nothing reads environment variables directly outside this module.
3. `app/database/session.py` creates one SQLAlchemy `engine` for the process. Each request gets its own `Session` via the `get_db` FastAPI dependency, which is always closed after the request finishes (even if the request raised an exception) - see the `try/finally` in `get_db`.

## Dependency injection

FastAPI's `Depends(get_db)` pattern is used for the database session (see `app/api/routes/health.py`). When a route declares `db: Session = Depends(get_db)`, FastAPI calls `get_db()` before running the route, hands the route the yielded session, and runs the code after `yield` (closing the session) once the route returns - regardless of whether it succeeded or raised. This keeps connection handling out of every individual route.

## Error format

Every error response - whether raised deliberately, a validation failure, an HTTP error, or something unhandled - is normalized to:

```json
{"error": {"code": "SOME_CODE", "message": "Human readable message.", "details": {}}}
```

See `app/core/exceptions.py` and `documentation/project-scope.md` section 13.

## What's built so far

- Foundation: health check, DB connectivity, centralized error handling, logging, CORS.
- SQLAlchemy models for all 12 tables (7 business + Roles/Users/UserRoles/AuditLogs/MaintenanceNotes).
- Authentication: login, JWT access/refresh tokens, current-user endpoint, change-password, role-based route protection (`app/api/dependencies/auth.py`).
- Landlord module (repository/service/API), fully protected by role - the first complete vertical slice end to end, and the template every other module follows.

Remaining business modules (Properties, Tenants, Tenancies, Rent Payments, Maintenance, Employees, Dashboard, Reports) are added one at a time in later milestones, following the same repository -> service -> API pattern established here.
