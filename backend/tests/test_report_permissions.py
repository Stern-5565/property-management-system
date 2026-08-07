"""Permission-boundary tests for the Reports routes.

All 10 reports share one role gate (CAN_VIEW_REPORTS, set once on the
router itself in app/api/routes/reports.py - Administrator/PropertyManager/
ReadOnly can view, MaintenanceEmployee cannot, same shape as Dashboard).
A single representative endpoint (/occupancy) is enough to prove the gate
is wired up; the router-level dependency guarantees the other nine behave
identically - same reasoning as test_dashboard_permissions.py, which uses
the same "test one, trust the shared gate" approach for its 5 routes.
"""

from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import MAINTENANCE_EMPLOYEE_EMAIL, PROPERTY_MANAGER_EMAIL, READ_ONLY_EMAIL, auth_headers

client = TestClient(app)


def test_occupancy_without_a_token_is_rejected() -> None:
    response = client.get("/api/reports/occupancy")
    assert response.status_code == 401


def test_read_only_user_can_view_occupancy_report() -> None:
    response = client.get("/api/reports/occupancy", headers=auth_headers(client, READ_ONLY_EMAIL))
    assert response.status_code == 200


def test_property_manager_can_view_occupancy_report() -> None:
    response = client.get("/api/reports/occupancy", headers=auth_headers(client, PROPERTY_MANAGER_EMAIL))
    assert response.status_code == 200


def test_maintenance_employee_cannot_view_occupancy_report() -> None:
    response = client.get("/api/reports/occupancy", headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_maintenance_employee_cannot_view_overdue_rent_report() -> None:
    # A second, financial report - confirms the gate isn't accidentally
    # narrower/wider for a report that carries money figures.
    response = client.get("/api/reports/overdue-rent", headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_unknown_report_key_returns_404() -> None:
    response = client.get("/api/reports/not-a-real-report", headers=auth_headers(client))
    assert response.status_code == 404
