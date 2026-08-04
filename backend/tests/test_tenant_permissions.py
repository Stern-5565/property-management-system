"""Permission-boundary tests for the Tenant routes - same role matrix as
Landlords/Properties (see test_landlord_permissions.py)."""

from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import MAINTENANCE_EMPLOYEE_EMAIL, READ_ONLY_EMAIL, auth_headers

client = TestClient(app)


def test_list_tenants_without_a_token_is_rejected() -> None:
    response = client.get("/api/tenants")
    assert response.status_code == 401


def test_read_only_user_can_list_tenants() -> None:
    response = client.get("/api/tenants", headers=auth_headers(client, READ_ONLY_EMAIL))
    assert response.status_code == 200


def test_read_only_user_cannot_create_a_tenant() -> None:
    response = client.post(
        "/api/tenants",
        json={"FirstName": "Should", "LastName": "NotExist"},
        headers=auth_headers(client, READ_ONLY_EMAIL),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_maintenance_employee_cannot_view_tenants() -> None:
    response = client.get("/api/tenants", headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
