"""Permission-boundary tests for the Property routes - same role matrix as
Landlords (see test_landlord_permissions.py)."""

from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import MAINTENANCE_EMPLOYEE_EMAIL, READ_ONLY_EMAIL, auth_headers

client = TestClient(app)


def test_list_properties_without_a_token_is_rejected() -> None:
    response = client.get("/api/properties")
    assert response.status_code == 401


def test_read_only_user_can_list_properties() -> None:
    response = client.get("/api/properties", headers=auth_headers(client, READ_ONLY_EMAIL))
    assert response.status_code == 200


def test_read_only_user_cannot_create_a_property() -> None:
    response = client.post(
        "/api/properties",
        json={
            "LandlordId": 1,
            "PropertyReference": "PM-SHOULD-NOT-EXIST",
            "AddressLine1": "1 Nope Street",
            "City": "Nowhere",
            "Postcode": "NO1 1NO",
            "Country": "United Kingdom",
            "PropertyType": "Flat",
            "Bedrooms": 1,
            "Bathrooms": 1,
            "MonthlyRent": "500.00",
        },
        headers=auth_headers(client, READ_ONLY_EMAIL),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_maintenance_employee_cannot_view_properties() -> None:
    response = client.get("/api/properties", headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
