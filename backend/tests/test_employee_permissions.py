"""Permission-boundary tests for the Employee routes.

Unlike Landlord/Property/Tenant (Administrator AND PropertyManager
manage, ReadOnly views), Employees is narrower: only Administrator can
manage, and only Administrator/PropertyManager can even view - see
app/core/roles.py's comment block for the full reasoning.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.database.session import SessionLocal
from app.main import app
from app.models.employee import Employee
from tests.auth_helpers import MAINTENANCE_EMPLOYEE_EMAIL, PROPERTY_MANAGER_EMAIL, READ_ONLY_EMAIL, auth_headers

client = TestClient(app)
TODAY = date.today()


def test_list_employees_without_a_token_is_rejected() -> None:
    response = client.get("/api/employees")
    assert response.status_code == 401


def test_read_only_user_cannot_view_employees() -> None:
    response = client.get("/api/employees", headers=auth_headers(client, READ_ONLY_EMAIL))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_maintenance_employee_cannot_view_employees() -> None:
    response = client.get("/api/employees", headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_property_manager_can_view_employees() -> None:
    response = client.get("/api/employees", headers=auth_headers(client, PROPERTY_MANAGER_EMAIL))
    assert response.status_code == 200


def test_property_manager_cannot_create_an_employee() -> None:
    response = client.post(
        "/api/employees",
        json={
            "FirstName": "Should",
            "LastName": "NotBeCreated",
            "Email": "should.not.be.created@example.com",
            "HireDate": (TODAY - timedelta(days=1)).isoformat(),
        },
        headers=auth_headers(client, PROPERTY_MANAGER_EMAIL),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_administrator_can_create_an_employee() -> None:
    response = client.post(
        "/api/employees",
        json={
            "FirstName": "Admin",
            "LastName": "PermissionTest",
            "Email": "admin.permission.test@example.com",
            "HireDate": (TODAY - timedelta(days=1)).isoformat(),
        },
        headers=auth_headers(client),  # defaults to Administrator
    )
    assert response.status_code == 201
    created_id = response.json()["EmployeeId"]

    db = SessionLocal()
    try:
        employee = db.get(Employee, created_id)
        if employee is not None:
            db.delete(employee)
            db.commit()
    finally:
        db.close()
