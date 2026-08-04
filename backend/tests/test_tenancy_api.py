"""End-to-end HTTP tests for the Tenancy API routes.

Same conventions as the other *_api.py files: logged in as Administrator,
throwaway rows cleaned up so the seeded 12-tenancy demo dataset stays
exactly as seeded for every other test file.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.models.landlord import Landlord
from app.models.property import Property
from app.models.tenancy import Tenancy
from app.models.tenant import Tenant
from tests.auth_helpers import auth_headers

client = TestClient(app)
HEADERS = auth_headers(client)
TODAY = date.today()


def _robert_jenkins_id() -> int:
    db = SessionLocal()
    try:
        landlord = db.execute(select(Landlord).where(Landlord.Email == "robert.jenkins@example.com")).scalar_one()
        return landlord.LandlordId
    finally:
        db.close()


def _create_property() -> dict:
    response = client.post(
        "/api/properties",
        json={
            "LandlordId": _robert_jenkins_id(),
            "PropertyReference": "PM-TENANCY-API-001",
            "AddressLine1": "1 Tenancy API St",
            "City": "Testville",
            "Postcode": "TE1 1ST",
            "Country": "United Kingdom",
            "PropertyType": "Flat",
            "Bedrooms": 2,
            "Bathrooms": 1,
            "MonthlyRent": "1000.00",
        },
        headers=HEADERS,
    )
    assert response.status_code == 201
    return response.json()


def _create_tenant() -> dict:
    response = client.post(
        "/api/tenants",
        json={"FirstName": "Api", "LastName": "TenancyFixture", "Email": "api.tenancyfixture@example.com"},
        headers=HEADERS,
    )
    assert response.status_code == 201
    return response.json()


def _cleanup(*, tenancy_id: int | None = None, property_id: int | None = None, tenant_id: int | None = None) -> None:
    db = SessionLocal()
    try:
        if tenancy_id is not None:
            tenancy = db.get(Tenancy, tenancy_id)
            if tenancy is not None:
                db.delete(tenancy)
                db.commit()
        if property_id is not None:
            property_ = db.get(Property, property_id)
            if property_ is not None:
                db.delete(property_)
                db.commit()
        if tenant_id is not None:
            tenant = db.get(Tenant, tenant_id)
            if tenant is not None:
                db.delete(tenant)
                db.commit()
    finally:
        db.close()


def test_get_tenancy_not_found_returns_standard_error_shape() -> None:
    response = client.get("/api/tenancies/999999", headers=HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TENANCY_NOT_FOUND"


def test_list_expiring_tenancies_matches_report_7() -> None:
    response = client.get("/api/tenancies/expiring", params={"days": 30}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["TenancyStatus"] == "Ending Soon"


def test_full_tenancy_lifecycle_via_api() -> None:
    prop = _create_property()
    tenant = _create_tenant()
    tenancy_id = None
    try:
        # Create draft. StartDate is in the past, not today: ending the
        # tenancy later in this test defaults to end_date=today, and
        # EndDate must be strictly AFTER StartDate (CK_Tenancies_DateOrder)
        # - see TenancyService.end_tenancy's TENANCY_INVALID_END_DATE guard.
        start_date = TODAY - timedelta(days=5)
        create_response = client.post(
            "/api/tenancies",
            json={
                "PropertyId": prop["PropertyId"],
                "TenantId": tenant["TenantId"],
                "StartDate": start_date.isoformat(),
                "EndDate": (TODAY + timedelta(days=180)).isoformat(),
                "MonthlyRent": "1000.00",
                "PaymentDueDay": 1,
            },
            headers=HEADERS,
        )
        assert create_response.status_code == 201
        created = create_response.json()
        tenancy_id = created["TenancyId"]
        assert created["TenancyStatus"] == "Draft"
        assert created["PropertyReference"] == "PM-TENANCY-API-001"
        assert created["TenantName"] == "Api TenancyFixture"

        # Activate
        activate_response = client.post(f"/api/tenancies/{tenancy_id}/activate", headers=HEADERS)
        assert activate_response.status_code == 200
        assert activate_response.json()["TenancyStatus"] == "Active"

        # Property is now Occupied
        property_get = client.get(f"/api/properties/{prop['PropertyId']}", headers=HEADERS)
        assert property_get.json()["PropertyStatus"] == "Occupied"

        # Update is now blocked (no longer Draft)
        update_response = client.put(
            f"/api/tenancies/{tenancy_id}",
            json={
                "PropertyId": prop["PropertyId"],
                "TenantId": tenant["TenantId"],
                "StartDate": TODAY.isoformat(),
                "MonthlyRent": "1100.00",
                "PaymentDueDay": 1,
            },
            headers=HEADERS,
        )
        assert update_response.status_code == 409
        assert update_response.json()["error"]["code"] == "TENANCY_NOT_EDITABLE"

        # End
        end_response = client.post(f"/api/tenancies/{tenancy_id}/end", json={}, headers=HEADERS)
        assert end_response.status_code == 200
        assert end_response.json()["TenancyStatus"] == "Ended"

        # Property is Vacant again
        property_get_after = client.get(f"/api/properties/{prop['PropertyId']}", headers=HEADERS)
        assert property_get_after.json()["PropertyStatus"] == "Vacant"
    finally:
        _cleanup(tenancy_id=tenancy_id, property_id=prop["PropertyId"], tenant_id=tenant["TenantId"])
