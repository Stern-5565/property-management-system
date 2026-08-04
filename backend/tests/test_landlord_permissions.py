"""Permission-boundary tests for the Landlord routes.

Covers the actual role matrix from documentation/project-scope.md, section
4: Administrator and PropertyManager can manage landlords, ReadOnly can
view only, MaintenanceEmployee has no access at all, and no token means no
access regardless of role.
"""

from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import MAINTENANCE_EMPLOYEE_EMAIL, PROPERTY_MANAGER_EMAIL, READ_ONLY_EMAIL, auth_headers

client = TestClient(app)


def test_list_landlords_without_a_token_is_rejected() -> None:
    response = client.get("/api/landlords")

    assert response.status_code == 401


def test_list_landlords_with_garbage_token_is_rejected() -> None:
    response = client.get("/api/landlords", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_read_only_user_can_list_landlords() -> None:
    response = client.get("/api/landlords", headers=auth_headers(client, READ_ONLY_EMAIL))

    assert response.status_code == 200


def test_read_only_user_cannot_create_a_landlord() -> None:
    response = client.post(
        "/api/landlords",
        json={
            "CompanyName": "Should Not Be Created Ltd",
            "AddressLine1": "1 Nope Street",
            "City": "Nowhere",
            "Postcode": "NO1 1NO",
            "Country": "United Kingdom",
        },
        headers=auth_headers(client, READ_ONLY_EMAIL),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_property_manager_can_create_a_landlord() -> None:
    from app.database.session import SessionLocal
    from app.models.landlord import Landlord

    response = client.post(
        "/api/landlords",
        json={
            "CompanyName": "PM Permission Test Ltd",
            "Email": "pm.permission.test@example.com",
            "AddressLine1": "1 PM Street",
            "City": "Testville",
            "Postcode": "TE1 1ST",
            "Country": "United Kingdom",
        },
        headers=auth_headers(client, PROPERTY_MANAGER_EMAIL),
    )

    assert response.status_code == 201
    created_id = response.json()["LandlordId"]

    db = SessionLocal()
    try:
        landlord = db.get(Landlord, created_id)
        if landlord is not None:
            db.delete(landlord)
            db.commit()
    finally:
        db.close()


def test_maintenance_employee_cannot_view_landlords() -> None:
    response = client.get("/api/landlords", headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
