"""End-to-end HTTP tests for the Property API routes.

Same conventions as test_landlord_api.py: logged in as Administrator,
throwaway rows cleaned up in finally blocks so the seeded 10-property demo
dataset stays exactly as seeded for every other test file.
"""

from sqlalchemy import select
from fastapi.testclient import TestClient

from app.database.session import SessionLocal
from app.main import app
from app.models.landlord import Landlord
from app.models.property import Property
from tests.auth_helpers import auth_headers

client = TestClient(app)
HEADERS = auth_headers(client)


def _robert_jenkins_id() -> int:
    db = SessionLocal()
    try:
        landlord = db.execute(select(Landlord).where(Landlord.Email == "robert.jenkins@example.com")).scalar_one()
        return landlord.LandlordId
    finally:
        db.close()


def _create_payload(landlord_id: int, **overrides) -> dict:
    payload = {
        "LandlordId": landlord_id,
        "PropertyReference": "PM-API-001",
        "AddressLine1": "1 API Street",
        "City": "Testville",
        "Postcode": "TE1 1ST",
        "Country": "United Kingdom",
        "PropertyType": "Flat",
        "Bedrooms": 2,
        "Bathrooms": 1,
        "MonthlyRent": "1000.00",
    }
    payload.update(overrides)
    return payload


def _hard_delete(property_id: int) -> None:
    db = SessionLocal()
    try:
        property_ = db.get(Property, property_id)
        if property_ is not None:
            db.delete(property_)
            db.commit()
    finally:
        db.close()


def test_list_properties_returns_paginated_envelope() -> None:
    response = client.get("/api/properties", params={"page": 1, "page_size": 3}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 3
    assert body["total_items"] >= 10
    assert len(body["items"]) == 3


def test_list_properties_filters_by_status() -> None:
    response = client.get("/api/properties", params={"property_status": "Vacant"}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["total_items"] == 2
    assert all(item["PropertyStatus"] == "Vacant" for item in body["items"])


def test_list_properties_sort_by_monthly_rent() -> None:
    response = client.get(
        "/api/properties", params={"sort_by": "MonthlyRent", "sort_dir": "desc", "page_size": 100}, headers=HEADERS
    )

    assert response.status_code == 200
    rents = [float(item["MonthlyRent"]) for item in response.json()["items"]]
    assert rents == sorted(rents, reverse=True)


def test_get_property_not_found_returns_standard_error_shape() -> None:
    response = client.get("/api/properties/999999", headers=HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROPERTY_NOT_FOUND"


def test_create_property_with_invalid_data_returns_422() -> None:
    response = client.post(
        "/api/properties",
        json={"LandlordId": 1, "PropertyReference": "X"},  # missing required address/type/rent fields
        headers=HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_property_with_unknown_landlord_returns_404() -> None:
    response = client.post("/api/properties", json=_create_payload(999_999), headers=HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "LANDLORD_NOT_FOUND"


def test_delete_property_with_active_tenancy_is_blocked_via_api() -> None:
    db = SessionLocal()
    try:
        pm_0003 = db.execute(select(Property).where(Property.PropertyReference == "PM-0003")).scalar_one()
        property_id = pm_0003.PropertyId
    finally:
        db.close()

    response = client.delete(f"/api/properties/{property_id}", headers=HEADERS)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PROPERTY_HAS_ACTIVE_TENANCIES"


def test_full_property_lifecycle_via_api() -> None:
    landlord_id = _robert_jenkins_id()
    created_id = None
    try:
        # Create
        create_response = client.post("/api/properties", json=_create_payload(landlord_id), headers=HEADERS)
        assert create_response.status_code == 201
        created = create_response.json()
        created_id = created["PropertyId"]
        assert created["PropertyStatus"] == "Vacant"
        assert created["IsActive"] is True

        # Duplicate reference is rejected
        dup_response = client.post(
            "/api/properties", json=_create_payload(landlord_id, AddressLine1="2 Other St"), headers=HEADERS
        )
        assert dup_response.status_code == 409
        assert dup_response.json()["error"]["code"] == "DUPLICATE_PROPERTY_REFERENCE"

        # Get
        get_response = client.get(f"/api/properties/{created_id}", headers=HEADERS)
        assert get_response.status_code == 200
        assert get_response.json()["PropertyReference"] == "PM-API-001"

        # Update
        update_response = client.put(
            f"/api/properties/{created_id}",
            json=_create_payload(landlord_id, MonthlyRent="1200.00", Bedrooms=3),
            headers=HEADERS,
        )
        assert update_response.status_code == 200
        assert float(update_response.json()["MonthlyRent"]) == 1200.00
        assert update_response.json()["Bedrooms"] == 3

        # Status change
        status_response = client.patch(
            f"/api/properties/{created_id}/status", json={"PropertyStatus": "Under Maintenance"}, headers=HEADERS
        )
        assert status_response.status_code == 200
        assert status_response.json()["PropertyStatus"] == "Under Maintenance"

        # Delete (soft - no active tenancy, so it succeeds)
        delete_response = client.delete(f"/api/properties/{created_id}", headers=HEADERS)
        assert delete_response.status_code == 204

        final_get = client.get(f"/api/properties/{created_id}", headers=HEADERS)
        assert final_get.status_code == 200
        assert final_get.json()["IsActive"] is False
        assert final_get.json()["PropertyStatus"] == "Archived"
    finally:
        if created_id is not None:
            _hard_delete(created_id)
