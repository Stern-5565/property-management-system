"""First backend test: confirms the app starts and the database is reachable.

This hits the real local SQL Server rather than mocking it - at this stage
the whole point of the test is to prove the database connection actually
works, so a mock would tell us nothing useful.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok_when_database_is_reachable() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
