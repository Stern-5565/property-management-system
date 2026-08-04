"""Permission-boundary tests for the Tenancy routes - same role matrix as
Landlords/Properties/Tenants (see test_landlord_permissions.py)."""

from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import MAINTENANCE_EMPLOYEE_EMAIL, READ_ONLY_EMAIL, auth_headers

client = TestClient(app)


def test_list_tenancies_without_a_token_is_rejected() -> None:
    response = client.get("/api/tenancies")
    assert response.status_code == 401


def test_read_only_user_can_list_tenancies() -> None:
    response = client.get("/api/tenancies", headers=auth_headers(client, READ_ONLY_EMAIL))
    assert response.status_code == 200


def test_read_only_user_cannot_create_a_tenancy() -> None:
    response = client.post(
        "/api/tenancies",
        json={
            "PropertyId": 1,
            "TenantId": 1,
            "StartDate": "2026-01-01",
            "MonthlyRent": "1000.00",
            "PaymentDueDay": 1,
        },
        headers=auth_headers(client, READ_ONLY_EMAIL),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_maintenance_employee_cannot_view_tenancies() -> None:
    response = client.get("/api/tenancies", headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
