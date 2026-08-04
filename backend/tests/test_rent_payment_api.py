"""End-to-end HTTP tests for the RentPayment API routes.

Same conventions as the other *_api.py files: logged in as Administrator,
throwaway payment rows cleaned up so the seeded 30-payment demo dataset
stays exactly as seeded for every other test file. Attached to an
existing seeded tenancy (AGR-1005) rather than a fresh property/tenant/
tenancy chain - see test_rent_payment_service.py's module docstring.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.models.rent_payment import RentPayment
from app.models.tenancy import Tenancy
from tests.auth_helpers import auth_headers

client = TestClient(app)
HEADERS = auth_headers(client)
TODAY = date.today()


def _agr_1005_tenancy_id() -> int:
    db = SessionLocal()
    try:
        tenancy = db.execute(select(Tenancy).where(Tenancy.AgreementReference == "AGR-1005")).scalar_one()
        return tenancy.TenancyId
    finally:
        db.close()


def _hard_delete(payment_id: int) -> None:
    db = SessionLocal()
    try:
        payment = db.get(RentPayment, payment_id)
        if payment is not None:
            db.delete(payment)
            db.commit()
    finally:
        db.close()


def test_list_payments_returns_paginated_envelope() -> None:
    response = client.get("/api/rent-payments", params={"page": 1, "page_size": 5}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["total_items"] >= 30
    assert len(body["items"]) == 5


def test_overdue_endpoint_matches_report_2() -> None:
    response = client.get("/api/rent-payments/overdue", headers=HEADERS)

    assert response.status_code == 200
    # See test_rent_payment_repository.py::test_list_overdue_matches_report_2
    # for why this is 4, not 2 - two of these are stored as "Partially
    # Paid" but still overdue by date, and correctly appear here too.
    references = {item["PaymentReference"] for item in response.json()}
    assert references == {"PAY-00004", "PAY-00008", "PAY-00019", "PAY-00028"}


def test_due_this_month_endpoint_matches_report_1() -> None:
    response = client.get("/api/rent-payments/due", headers=HEADERS)

    assert response.status_code == 200
    assert len(response.json()) == 7


def test_get_payment_not_found_returns_standard_error_shape() -> None:
    response = client.get("/api/rent-payments/999999", headers=HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PAYMENT_NOT_FOUND"


def test_create_payment_with_invalid_data_returns_422() -> None:
    response = client.post("/api/rent-payments", json={"TenancyId": 1}, headers=HEADERS)  # missing required fields

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_full_rent_payment_lifecycle_via_api() -> None:
    tenancy_id = _agr_1005_tenancy_id()
    payment_id = None
    try:
        # Create
        create_response = client.post(
            "/api/rent-payments",
            json={
                "TenancyId": tenancy_id,
                "PaymentReference": "PAY-API-TEST-001",
                "DueDate": (TODAY + timedelta(days=10)).isoformat(),
                "AmountDue": "1050.00",
            },
            headers=HEADERS,
        )
        assert create_response.status_code == 201
        created = create_response.json()
        payment_id = created["RentPaymentId"]
        assert created["PaymentStatus"] == "Pending"
        assert float(created["AmountOutstanding"]) == 1050.00

        # Duplicate reference rejected
        dup_response = client.post(
            "/api/rent-payments",
            json={
                "TenancyId": tenancy_id,
                "PaymentReference": "PAY-API-TEST-001",
                "DueDate": (TODAY + timedelta(days=10)).isoformat(),
                "AmountDue": "500.00",
            },
            headers=HEADERS,
        )
        assert dup_response.status_code == 409
        assert dup_response.json()["error"]["code"] == "DUPLICATE_PAYMENT_REFERENCE"

        # Record a partial payment
        partial_response = client.post(
            f"/api/rent-payments/{payment_id}/record-payment",
            json={"AmountPaid": "400.00", "PaymentMethod": "Bank Transfer"},
            headers=HEADERS,
        )
        assert partial_response.status_code == 200
        assert partial_response.json()["PaymentStatus"] == "Partially Paid"
        assert float(partial_response.json()["AmountOutstanding"]) == 650.00

        # Update is now blocked (money has been recorded)
        update_response = client.put(
            f"/api/rent-payments/{payment_id}",
            json={
                "TenancyId": tenancy_id,
                "PaymentReference": "PAY-API-TEST-001",
                "DueDate": (TODAY + timedelta(days=10)).isoformat(),
                "AmountDue": "999.00",
            },
            headers=HEADERS,
        )
        assert update_response.status_code == 409
        assert update_response.json()["error"]["code"] == "PAYMENT_NOT_EDITABLE"

        # Record the remaining balance
        final_response = client.post(
            f"/api/rent-payments/{payment_id}/record-payment",
            json={"AmountPaid": "650.00", "PaymentMethod": "Bank Transfer"},
            headers=HEADERS,
        )
        assert final_response.status_code == 200
        assert final_response.json()["PaymentStatus"] == "Paid"
        assert float(final_response.json()["AmountOutstanding"]) == 0.00

        # Cancel (still allowed on a Paid record)
        cancel_response = client.post(f"/api/rent-payments/{payment_id}/cancel", json={}, headers=HEADERS)
        assert cancel_response.status_code == 200
        assert cancel_response.json()["PaymentStatus"] == "Cancelled"

        # Cancelling again is rejected
        cancel_again_response = client.post(f"/api/rent-payments/{payment_id}/cancel", json={}, headers=HEADERS)
        assert cancel_again_response.status_code == 409
        assert cancel_again_response.json()["error"]["code"] == "PAYMENT_ALREADY_CANCELLED"
    finally:
        if payment_id is not None:
            _hard_delete(payment_id)
