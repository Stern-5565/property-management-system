"""Permission-boundary tests for the RentPayment routes - same role
matrix as every other module (see test_landlord_permissions.py)."""

from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import MAINTENANCE_EMPLOYEE_EMAIL, READ_ONLY_EMAIL, auth_headers

client = TestClient(app)


def test_list_payments_without_a_token_is_rejected() -> None:
    response = client.get("/api/rent-payments")
    assert response.status_code == 401


def test_read_only_user_can_list_payments() -> None:
    response = client.get("/api/rent-payments", headers=auth_headers(client, READ_ONLY_EMAIL))
    assert response.status_code == 200


def test_read_only_user_cannot_record_a_payment() -> None:
    response = client.post(
        "/api/rent-payments/1/record-payment",
        json={"AmountPaid": "100.00", "PaymentMethod": "Cash"},
        headers=auth_headers(client, READ_ONLY_EMAIL),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_maintenance_employee_cannot_view_payments() -> None:
    response = client.get("/api/rent-payments", headers=auth_headers(client, MAINTENANCE_EMPLOYEE_EMAIL))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
