"""Permission-boundary tests for the Maintenance routes.

Unlike every earlier module, MaintenanceEmployee has real access here -
these tests cover both the route-level role gate (app/core/roles.py) and
the one thing a role gate alone can't express: that MaintenanceEmployee's
hands-on-the-job actions (change-status, notes, costs, complete) only
work on requests actually assigned to them - see
MaintenanceService._assert_can_update_work. MR-0003 (seeded, PM-0002,
unassigned, still "Reported") is used for that check precisely because
it's unassigned to anyone - the request is rejected by the permission
check before any write happens, so it's safe to use real seeded data
here without cleanup.
"""

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.models.maintenance_request import MaintenanceRequest
from tests.auth_helpers import MAINTENANCE_EMPLOYEE_EMAIL, READ_ONLY_EMAIL, auth_headers

client = TestClient(app)


def _mr_0003_id() -> int:
    db = SessionLocal()
    try:
        request = db.execute(select(MaintenanceRequest).where(MaintenanceRequest.RequestReference == "MR-0003")).scalar_one()
        return request.MaintenanceRequestId
    finally:
        db.close()


def test_list_requests_without_a_token_is_rejected() -> None:
    response = client.get("/api/maintenance-requests")
    assert response.status_code == 401


def test_read_only_user_can_list_requests() -> None:
    response = client.get("/api/maintenance-requests", headers=auth_headers(client, READ_ONLY_EMAIL))
    assert response.status_code == 200


def test_read_only_user_cannot_create_request() -> None:
    response = client.post(
        "/api/maintenance-requests",
        json={"PropertyId": 1, "RequestReference": "X", "Title": "X", "Category": "General", "Priority": "Low"},
        headers=auth_headers(client, READ_ONLY_EMAIL),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_read_only_user_cannot_change_status() -> None:
    response = client.post(
        f"/api/maintenance-requests/{_mr_0003_id()}/change-status",
        json={"MaintenanceStatus": "Assigned"},
        headers=auth_headers(client, READ_ONLY_EMAIL),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_maintenance_employee_can_list_requests() -> None:
    response = client.get("/api/maintenance-requests", headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL))
    assert response.status_code == 200


def test_maintenance_employee_cannot_view_workload() -> None:
    response = client.get("/api/maintenance-requests/workload", headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_maintenance_employee_cannot_create_request() -> None:
    response = client.post(
        "/api/maintenance-requests",
        json={"PropertyId": 1, "RequestReference": "X", "Title": "X", "Category": "General", "Priority": "Low"},
        headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_maintenance_employee_cannot_assign() -> None:
    response = client.post(
        f"/api/maintenance-requests/{_mr_0003_id()}/assign",
        json={"EmployeeId": 1},
        headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_maintenance_employee_cannot_change_priority() -> None:
    response = client.post(
        f"/api/maintenance-requests/{_mr_0003_id()}/change-priority",
        json={"Priority": "High"},
        headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_maintenance_employee_cannot_cancel() -> None:
    response = client.post(
        f"/api/maintenance-requests/{_mr_0003_id()}/cancel", json={}, headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL)
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_maintenance_employee_cannot_change_status_of_unassigned_request() -> None:
    """Passes the route's role gate (MaintenanceEmployee IS allowed to hit
    this endpoint) but is rejected by MaintenanceService because MR-0003
    isn't assigned to them - a data-level check no role tuple alone can
    express."""
    response = client.post(
        f"/api/maintenance-requests/{_mr_0003_id()}/change-status",
        json={"MaintenanceStatus": "Assigned"},
        headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "MAINTENANCE_NOT_ASSIGNED_TO_YOU"
