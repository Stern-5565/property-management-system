"""Permission-boundary tests for the Dashboard routes.

Same view shape as Maintenance: Administrator/PropertyManager/ReadOnly
can view, MaintenanceEmployee cannot (the dashboard mixes in financial
figures) - see app/core/roles.py's CAN_VIEW_DASHBOARD comment. All
dashboard routes share one role gate (set on the router itself in
app/api/routes/dashboard.py), so a single representative endpoint
(/summary) is enough to prove the gate is wired up; the router-level
dependency guarantees the other four behave identically.
"""

from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import MAINTENANCE_EMPLOYEE_EMAIL, PROPERTY_MANAGER_EMAIL, READ_ONLY_EMAIL, auth_headers

client = TestClient(app)


def test_summary_without_a_token_is_rejected() -> None:
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 401


def test_read_only_user_can_view_summary() -> None:
    response = client.get("/api/dashboard/summary", headers=auth_headers(client, READ_ONLY_EMAIL))
    assert response.status_code == 200


def test_property_manager_can_view_summary() -> None:
    response = client.get("/api/dashboard/summary", headers=auth_headers(client, PROPERTY_MANAGER_EMAIL))
    assert response.status_code == 200


def test_maintenance_employee_cannot_view_summary() -> None:
    response = client.get("/api/dashboard/summary", headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_maintenance_employee_cannot_view_recent_activity() -> None:
    response = client.get("/api/dashboard/recent-activity", headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
