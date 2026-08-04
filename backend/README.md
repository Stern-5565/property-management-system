# PropertyManager Backend

FastAPI backend for PropertyManager. SQL Server via SQLAlchemy + pyodbc, JWT authentication (added in a later milestone), Pytest for tests.

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

`tests/test_health.py` connects to the real local database (no mocking) - it exists specifically to prove the FastAPI -> SQLAlchemy -> pyodbc -> SQL Server chain actually works end to end.

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

## Known limitation at this stage

There are no business models, schemas, or CRUD routes yet - this is deliberately just the foundation (health check + DB connectivity + error handling + logging + CORS). Business modules are added one at a time in later milestones.
