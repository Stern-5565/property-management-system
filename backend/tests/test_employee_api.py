"""End-to-end HTTP tests for the Employee API routes.

Same conventions as test_landlord_api.py: logged in as Administrator,
throwaway rows cleaned up so the seeded 5-employee demo dataset stays
exactly as seeded for every other test file.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.database.session import SessionLocal
from app.main import app
from app.models.employee import Employee
from tests.auth_helpers import auth_headers

client = TestClient(app)
HEADERS = auth_headers(client)
TODAY = date.today()


def _create_payload(**overrides) -> dict:
    payload = {
        "FirstName": "Api",
        "LastName": "Test",
        "Email": "api.test.employee@example.com",
        "HireDate": (TODAY - timedelta(days=10)).isoformat(),
    }
    payload.update(overrides)
    return payload


def _hard_delete(employee_id: int) -> None:
    db = SessionLocal()
    try:
        employee = db.get(Employee, employee_id)
        if employee is not None:
            db.delete(employee)
            db.commit()
    finally:
        db.close()


def test_list_employees_returns_paginated_envelope() -> None:
    response = client.get("/api/employees", params={"page": 1, "page_size": 2}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total_items"] >= 5
    assert len(body["items"]) == 2


def test_list_employees_search_filters_results() -> None:
    response = client.get("/api/employees", params={"search": "Finance"}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["total_items"] == 1
    assert body["items"][0]["LastName"] == "Wilson"


def test_get_employee_not_found_returns_standard_error_shape() -> None:
    response = client.get("/api/employees/999999", headers=HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EMPLOYEE_NOT_FOUND"


def test_create_employee_with_invalid_data_returns_422() -> None:
    response = client.post("/api/employees", json={"FirstName": "X"}, headers=HEADERS)  # missing required fields

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_employee_with_future_hire_date_returns_422() -> None:
    response = client.post(
        "/api/employees", json=_create_payload(HireDate=(TODAY + timedelta(days=1)).isoformat()), headers=HEADERS
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_delete_employee_with_open_maintenance_assignments_is_blocked_via_api() -> None:
    db = SessionLocal()
    try:
        from sqlalchemy import select

        daniel = db.execute(select(Employee).where(Employee.Email == "daniel.osei@propertymanager.example")).scalar_one()
        employee_id = daniel.EmployeeId
    finally:
        db.close()

    response = client.delete(f"/api/employees/{employee_id}", headers=HEADERS)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMPLOYEE_HAS_OPEN_MAINTENANCE_ASSIGNMENTS"


def test_full_employee_lifecycle_via_api() -> None:
    created_id = None
    try:
        # Create
        create_response = client.post("/api/employees", json=_create_payload(), headers=HEADERS)
        assert create_response.status_code == 201
        created = create_response.json()
        created_id = created["EmployeeId"]
        assert created["IsActive"] is True

        # Duplicate email is rejected
        dup_response = client.post("/api/employees", json=_create_payload(LastName="Different"), headers=HEADERS)
        assert dup_response.status_code == 409
        assert dup_response.json()["error"]["code"] == "DUPLICATE_EMAIL"

        # Get
        get_response = client.get(f"/api/employees/{created_id}", headers=HEADERS)
        assert get_response.status_code == 200
        assert get_response.json()["Email"] == "api.test.employee@example.com"

        # Update
        update_response = client.put(
            f"/api/employees/{created_id}", json=_create_payload(JobTitle="Renamed Title"), headers=HEADERS
        )
        assert update_response.status_code == 200
        assert update_response.json()["JobTitle"] == "Renamed Title"

        # Deactivate via the status endpoint
        status_response = client.patch(f"/api/employees/{created_id}/status", json={"IsActive": False}, headers=HEADERS)
        assert status_response.status_code == 200
        assert status_response.json()["IsActive"] is False

        # Reactivate
        reactivate_response = client.patch(f"/api/employees/{created_id}/status", json={"IsActive": True}, headers=HEADERS)
        assert reactivate_response.status_code == 200
        assert reactivate_response.json()["IsActive"] is True

        # Delete (soft - no open maintenance assignments, so it succeeds)
        delete_response = client.delete(f"/api/employees/{created_id}", headers=HEADERS)
        assert delete_response.status_code == 204
        assert delete_response.content == b""

        # The record still exists, just inactive - this was a soft delete.
        final_get = client.get(f"/api/employees/{created_id}", headers=HEADERS)
        assert final_get.status_code == 200
        assert final_get.json()["IsActive"] is False
    finally:
        if created_id is not None:
            _hard_delete(created_id)
