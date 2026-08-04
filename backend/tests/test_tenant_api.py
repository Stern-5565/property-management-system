"""End-to-end HTTP tests for the Tenant API routes.

Same conventions as test_landlord_api.py: logged in as Administrator,
throwaway rows cleaned up so the seeded 12-tenant demo dataset stays
exactly as seeded for every other test file.
"""

from sqlalchemy import select
from fastapi.testclient import TestClient

from app.database.session import SessionLocal
from app.main import app
from app.models.tenant import Tenant
from tests.auth_helpers import auth_headers

client = TestClient(app)
HEADERS = auth_headers(client)


def _create_payload(**overrides) -> dict:
    payload = {
        "FirstName": "Api",
        "LastName": "Fixture",
        "Email": "api.test.tenant@example.com",
    }
    payload.update(overrides)
    return payload


def _hard_delete(tenant_id: int) -> None:
    db = SessionLocal()
    try:
        tenant = db.get(Tenant, tenant_id)
        if tenant is not None:
            db.delete(tenant)
            db.commit()
    finally:
        db.close()


def test_list_tenants_returns_paginated_envelope() -> None:
    response = client.get("/api/tenants", params={"page": 1, "page_size": 5}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["total_items"] >= 12
    assert len(body["items"]) == 5


def test_list_tenants_search_filters_results() -> None:
    response = client.get("/api/tenants", params={"search": "Isabelle"}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["total_items"] == 1
    assert body["items"][0]["LastName"] == "Moore"


def test_get_tenant_not_found_returns_standard_error_shape() -> None:
    response = client.get("/api/tenants/999999", headers=HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TENANT_NOT_FOUND"


def test_create_tenant_with_invalid_data_returns_422() -> None:
    response = client.post("/api/tenants", json={"FirstName": "Only"}, headers=HEADERS)  # LastName missing

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_tenant_with_future_date_of_birth_returns_422() -> None:
    response = client.post(
        "/api/tenants",
        json=_create_payload(DateOfBirth="2999-01-01"),
        headers=HEADERS,
    )

    assert response.status_code == 422


def test_delete_tenant_with_active_tenancy_is_blocked_via_api() -> None:
    db = SessionLocal()
    try:
        john = db.execute(select(Tenant).where(Tenant.Email == "john.okafor@example.com")).scalar_one()
        tenant_id = john.TenantId
    finally:
        db.close()

    response = client.delete(f"/api/tenants/{tenant_id}", headers=HEADERS)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TENANT_HAS_ACTIVE_TENANCY"


def test_full_tenant_lifecycle_via_api() -> None:
    created_id = None
    try:
        create_response = client.post("/api/tenants", json=_create_payload(), headers=HEADERS)
        assert create_response.status_code == 201
        created = create_response.json()
        created_id = created["TenantId"]
        assert created["IsActive"] is True

        dup_response = client.post("/api/tenants", json=_create_payload(FirstName="Other"), headers=HEADERS)
        assert dup_response.status_code == 409
        assert dup_response.json()["error"]["code"] == "DUPLICATE_EMAIL"

        get_response = client.get(f"/api/tenants/{created_id}", headers=HEADERS)
        assert get_response.status_code == 200
        assert get_response.json()["FirstName"] == "Api"

        update_response = client.put(
            f"/api/tenants/{created_id}", json=_create_payload(FirstName="Renamed"), headers=HEADERS
        )
        assert update_response.status_code == 200
        assert update_response.json()["FirstName"] == "Renamed"

        status_response = client.patch(
            f"/api/tenants/{created_id}/status", json={"IsActive": False}, headers=HEADERS
        )
        assert status_response.status_code == 200
        assert status_response.json()["IsActive"] is False

        delete_response = client.delete(f"/api/tenants/{created_id}", headers=HEADERS)
        assert delete_response.status_code == 204

        final_get = client.get(f"/api/tenants/{created_id}", headers=HEADERS)
        assert final_get.json()["IsActive"] is False
    finally:
        if created_id is not None:
            _hard_delete(created_id)
