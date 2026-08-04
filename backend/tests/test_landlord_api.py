"""End-to-end HTTP tests for the Landlord API routes.

These exercise the full request flow for real: FastAPI route -> auth
dependency -> service -> repository -> SQL Server -> response, via
FastAPI's TestClient (no mocking of any layer). Like test_landlord_service.py,
write tests clean up their own throwaway rows so the seeded demo dataset
stays exactly as seeded for every other test file.

Logged in as the Administrator demo user throughout - permission-boundary
tests (which role can/can't do what, and what happens with no token at all)
live separately in test_landlord_permissions.py.
"""

from fastapi.testclient import TestClient

from app.database.session import SessionLocal
from app.main import app
from app.models.landlord import Landlord
from tests.auth_helpers import auth_headers

client = TestClient(app)
HEADERS = auth_headers(client)


def _create_payload(**overrides) -> dict:
    payload = {
        "CompanyName": "API Test Landlord Ltd",
        "Email": "api.test.landlord@example.com",
        "AddressLine1": "1 API Street",
        "City": "Testville",
        "Postcode": "TE1 1ST",
        "Country": "United Kingdom",
    }
    payload.update(overrides)
    return payload


def _hard_delete(landlord_id: int) -> None:
    db = SessionLocal()
    try:
        landlord = db.get(Landlord, landlord_id)
        if landlord is not None:
            db.delete(landlord)
            db.commit()
    finally:
        db.close()


def test_list_landlords_returns_paginated_envelope() -> None:
    response = client.get("/api/landlords", params={"page": 1, "page_size": 2}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total_items"] >= 5
    assert len(body["items"]) == 2


def test_list_landlords_search_filters_results() -> None:
    response = client.get("/api/landlords", params={"search": "Green Oak"}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["total_items"] == 1
    assert body["items"][0]["CompanyName"] == "Green Oak Properties Ltd"
    assert body["items"][0]["DisplayName"] == "Green Oak Properties Ltd"


def test_get_landlord_not_found_returns_standard_error_shape() -> None:
    response = client.get("/api/landlords/999999", headers=HEADERS)

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "LANDLORD_NOT_FOUND"
    assert "details" in body["error"]


def test_create_landlord_with_invalid_data_returns_422() -> None:
    response = client.post(
        "/api/landlords",
        json={"AddressLine1": "1 Test St", "City": "X", "Postcode": "X", "Country": "X"},  # no name or company
        headers=HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_delete_landlord_with_active_properties_is_blocked_via_api() -> None:
    db = SessionLocal()
    try:
        from sqlalchemy import select

        green_oak = db.execute(select(Landlord).where(Landlord.CompanyName == "Green Oak Properties Ltd")).scalar_one()
        landlord_id = green_oak.LandlordId
    finally:
        db.close()

    response = client.delete(f"/api/landlords/{landlord_id}", headers=HEADERS)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LANDLORD_HAS_ACTIVE_PROPERTIES"


def test_full_landlord_lifecycle_via_api() -> None:
    created_id = None
    try:
        # Create
        create_response = client.post("/api/landlords", json=_create_payload(), headers=HEADERS)
        assert create_response.status_code == 201
        created = create_response.json()
        created_id = created["LandlordId"]
        assert created["DisplayName"] == "API Test Landlord Ltd"
        assert created["IsActive"] is True

        # Duplicate email is rejected
        dup_response = client.post(
            "/api/landlords", json=_create_payload(CompanyName="Another Name Ltd"), headers=HEADERS
        )
        assert dup_response.status_code == 409
        assert dup_response.json()["error"]["code"] == "DUPLICATE_EMAIL"

        # Get
        get_response = client.get(f"/api/landlords/{created_id}", headers=HEADERS)
        assert get_response.status_code == 200
        assert get_response.json()["CompanyName"] == "API Test Landlord Ltd"

        # Update
        update_response = client.put(
            f"/api/landlords/{created_id}",
            json=_create_payload(CompanyName="API Test Landlord Renamed Ltd"),
            headers=HEADERS,
        )
        assert update_response.status_code == 200
        assert update_response.json()["CompanyName"] == "API Test Landlord Renamed Ltd"

        # Deactivate via the status endpoint
        status_response = client.patch(
            f"/api/landlords/{created_id}/status", json={"IsActive": False}, headers=HEADERS
        )
        assert status_response.status_code == 200
        assert status_response.json()["IsActive"] is False

        # Reactivate
        reactivate_response = client.patch(
            f"/api/landlords/{created_id}/status", json={"IsActive": True}, headers=HEADERS
        )
        assert reactivate_response.status_code == 200
        assert reactivate_response.json()["IsActive"] is True

        # Delete (soft - no active properties, so it succeeds)
        delete_response = client.delete(f"/api/landlords/{created_id}", headers=HEADERS)
        assert delete_response.status_code == 204
        assert delete_response.content == b""

        # The record still exists, just inactive - this was a soft delete.
        final_get = client.get(f"/api/landlords/{created_id}", headers=HEADERS)
        assert final_get.status_code == 200
        assert final_get.json()["IsActive"] is False
    finally:
        if created_id is not None:
            _hard_delete(created_id)
