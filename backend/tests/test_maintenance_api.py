"""End-to-end HTTP tests for the Maintenance API routes.

Same conventions as the other *_api.py files: logged in as Administrator,
throwaway request rows cleaned up so the seeded 20-request demo dataset
stays exactly as seeded for every other test file. Attached to an
existing seeded property (PM-0002) rather than a fresh property fixture -
see test_maintenance_service.py's module docstring.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.models.employee import Employee
from app.models.maintenance_note import MaintenanceNote
from app.models.maintenance_request import MaintenanceRequest
from app.models.property import Property
from tests.auth_helpers import auth_headers

client = TestClient(app)
HEADERS = auth_headers(client)
TODAY = date.today()


def _property_id() -> int:
    db = SessionLocal()
    try:
        property_ = db.execute(select(Property).where(Property.PropertyReference == "PM-0002")).scalar_one()
        return property_.PropertyId
    finally:
        db.close()


def _daniel_employee_id() -> int:
    db = SessionLocal()
    try:
        employee = db.execute(select(Employee).where(Employee.Email == "daniel.osei@propertymanager.example")).scalar_one()
        return employee.EmployeeId
    finally:
        db.close()


def _hard_delete(request_id: int) -> None:
    db = SessionLocal()
    try:
        for note in db.execute(select(MaintenanceNote).where(MaintenanceNote.MaintenanceRequestId == request_id)).scalars():
            db.delete(note)
        request = db.get(MaintenanceRequest, request_id)
        if request is not None:
            db.delete(request)
        db.commit()
    finally:
        db.close()


def test_list_requests_returns_paginated_envelope() -> None:
    response = client.get("/api/maintenance-requests", params={"page": 1, "page_size": 5}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["total_items"] >= 20
    assert len(body["items"]) == 5


def test_workload_endpoint_reflects_seeded_assignments() -> None:
    response = client.get("/api/maintenance-requests/workload", headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    daniel = next(row for row in body if row["EmployeeName"] == "Daniel Osei")
    assert daniel["OpenRequestCount"] == 6
    assert daniel["EmergencyOpenCount"] == 3


def test_get_request_not_found_returns_standard_error_shape() -> None:
    response = client.get("/api/maintenance-requests/999999", headers=HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MAINTENANCE_REQUEST_NOT_FOUND"


def test_create_request_with_invalid_data_returns_422() -> None:
    response = client.post("/api/maintenance-requests", json={"PropertyId": 1}, headers=HEADERS)  # missing required fields

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_full_maintenance_lifecycle_via_api() -> None:
    property_id = _property_id()
    employee_id = _daniel_employee_id()
    request_id = None
    try:
        # Create
        create_response = client.post(
            "/api/maintenance-requests",
            json={
                "PropertyId": property_id,
                "RequestReference": "MR-API-TEST-001",
                "Title": "Leaking pipe under sink",
                "Description": "Slow leak reported by tenant.",
                "Category": "Plumbing",
                "Priority": "Medium",
            },
            headers=HEADERS,
        )
        assert create_response.status_code == 201
        created = create_response.json()
        request_id = created["MaintenanceRequestId"]
        assert created["MaintenanceStatus"] == "Reported"
        assert created["IsEmergency"] is False

        # Duplicate reference rejected
        dup_response = client.post(
            "/api/maintenance-requests",
            json={
                "PropertyId": property_id,
                "RequestReference": "MR-API-TEST-001",
                "Title": "Duplicate",
                "Category": "Plumbing",
                "Priority": "Low",
            },
            headers=HEADERS,
        )
        assert dup_response.status_code == 409
        assert dup_response.json()["error"]["code"] == "DUPLICATE_REQUEST_REFERENCE"

        # Change priority to Emergency
        priority_response = client.post(
            f"/api/maintenance-requests/{request_id}/change-priority", json={"Priority": "Emergency"}, headers=HEADERS
        )
        assert priority_response.status_code == 200
        assert priority_response.json()["IsEmergency"] is True

        # Assign
        assign_response = client.post(
            f"/api/maintenance-requests/{request_id}/assign", json={"EmployeeId": employee_id}, headers=HEADERS
        )
        assert assign_response.status_code == 200
        assert assign_response.json()["MaintenanceStatus"] == "Assigned"
        assert assign_response.json()["AssignedEmployeeName"] == "Daniel Osei"

        # Change status
        status_response = client.post(
            f"/api/maintenance-requests/{request_id}/change-status", json={"MaintenanceStatus": "In Progress"}, headers=HEADERS
        )
        assert status_response.status_code == 200
        assert status_response.json()["MaintenanceStatus"] == "In Progress"

        # Add a note
        note_response = client.post(
            f"/api/maintenance-requests/{request_id}/notes", json={"NoteText": "Parts on order."}, headers=HEADERS
        )
        assert note_response.status_code == 200
        assert len(note_response.json()["Notes"]) == 1
        assert note_response.json()["Notes"][0]["NoteText"] == "Parts on order."

        # Enter estimated cost
        costs_response = client.post(
            f"/api/maintenance-requests/{request_id}/costs", json={"EstimatedCost": "180.00"}, headers=HEADERS
        )
        assert costs_response.status_code == 200
        assert float(costs_response.json()["EstimatedCost"]) == 180.00

        # Completing without resolution notes is rejected by validation
        incomplete_response = client.post(f"/api/maintenance-requests/{request_id}/complete", json={}, headers=HEADERS)
        assert incomplete_response.status_code == 422

        # Complete
        complete_response = client.post(
            f"/api/maintenance-requests/{request_id}/complete",
            json={"ResolutionNotes": "Replaced the pipe joint.", "ActualCost": "175.00"},
            headers=HEADERS,
        )
        assert complete_response.status_code == 200
        completed = complete_response.json()
        assert completed["MaintenanceStatus"] == "Completed"
        assert completed["CompletedDate"] == TODAY.isoformat()
        assert float(completed["ActualCost"]) == 175.00

        # Cancelling a completed request is rejected
        cancel_response = client.post(f"/api/maintenance-requests/{request_id}/cancel", json={}, headers=HEADERS)
        assert cancel_response.status_code == 409
        assert cancel_response.json()["error"]["code"] == "MAINTENANCE_ALREADY_COMPLETED"
    finally:
        if request_id is not None:
            _hard_delete(request_id)


def test_assign_inactive_employee_is_rejected() -> None:
    property_id = _property_id()
    db = SessionLocal()
    inactive_id = None
    request_id = None
    try:
        inactive = Employee(
            FirstName="Inactive", LastName="Api", Email="inactive.api.test@example.com", HireDate=TODAY, IsActive=False
        )
        db.add(inactive)
        db.commit()
        db.refresh(inactive)
        inactive_id = inactive.EmployeeId

        create_response = client.post(
            "/api/maintenance-requests",
            json={
                "PropertyId": property_id,
                "RequestReference": "MR-API-TEST-002",
                "Title": "Test request for inactive-employee assignment",
                "Category": "General",
                "Priority": "Low",
            },
            headers=HEADERS,
        )
        request_id = create_response.json()["MaintenanceRequestId"]

        assign_response = client.post(
            f"/api/maintenance-requests/{request_id}/assign", json={"EmployeeId": inactive_id}, headers=HEADERS
        )
        assert assign_response.status_code == 409
        assert assign_response.json()["error"]["code"] == "EMPLOYEE_INACTIVE"
    finally:
        if request_id is not None:
            _hard_delete(request_id)
        if inactive_id is not None:
            employee = db.get(Employee, inactive_id)
            if employee is not None:
                db.delete(employee)
                db.commit()
        db.close()
