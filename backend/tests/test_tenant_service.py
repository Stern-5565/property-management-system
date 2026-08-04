"""Tests for TenantService - business rules.

Uses a throwaway tenant (created and torn down per test) rather than
mutating any of the 12 seeded demo tenants - same reasoning as
test_landlord_service.py.
"""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.core.exceptions import AppError
from app.database.session import SessionLocal
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.services.tenant_service import TenantService


@pytest.fixture
def service():
    db = SessionLocal()
    try:
        yield TenantService(db)
    finally:
        db.close()


def _new_tenant_payload(**overrides) -> TenantCreate:
    defaults = {
        "FirstName": "Test",
        "LastName": "Fixture",
        "Email": "test.fixture.tenant@example.com",
    }
    defaults.update(overrides)
    return TenantCreate(**defaults)


def test_create_and_get_tenant(service: TenantService) -> None:
    created = service.create_tenant(_new_tenant_payload())
    try:
        fetched = service.get_tenant(created.TenantId)
        assert fetched.FirstName == "Test"
        assert fetched.IsActive is True
    finally:
        service.db.delete(created)
        service.db.commit()


def test_get_tenant_raises_not_found_for_missing_id(service: TenantService) -> None:
    with pytest.raises(AppError) as exc_info:
        service.get_tenant(999_999)
    assert exc_info.value.code == "TENANT_NOT_FOUND"
    assert exc_info.value.status_code == 404


def test_create_tenant_rejects_duplicate_email(service: TenantService) -> None:
    created = service.create_tenant(_new_tenant_payload())
    try:
        with pytest.raises(AppError) as exc_info:
            service.create_tenant(_new_tenant_payload(FirstName="Different"))
        assert exc_info.value.code == "DUPLICATE_EMAIL"
        assert exc_info.value.status_code == 409
    finally:
        service.db.delete(created)
        service.db.commit()


def test_create_tenant_rejects_future_date_of_birth() -> None:
    """Rejected at the schema layer (TenantCreate), before the service is
    even reached - see field_validator in schemas/tenant.py."""
    with pytest.raises(ValidationError, match="Date of birth cannot be in the future"):
        TenantCreate(**{**_new_tenant_payload().model_dump(), "DateOfBirth": date.today() + timedelta(days=1)})


def test_update_tenant_changes_fields(service: TenantService) -> None:
    created = service.create_tenant(_new_tenant_payload())
    try:
        updated = service.update_tenant(
            created.TenantId,
            TenantUpdate(FirstName="Updated", LastName="Fixture", Email="test.fixture.tenant@example.com"),
        )
        assert updated.FirstName == "Updated"
    finally:
        service.db.delete(created)
        service.db.commit()


def test_update_tenant_allows_keeping_its_own_email(service: TenantService) -> None:
    created = service.create_tenant(_new_tenant_payload())
    try:
        updated = service.update_tenant(created.TenantId, _new_tenant_payload())
        assert updated.Email == "test.fixture.tenant@example.com"
    finally:
        service.db.delete(created)
        service.db.commit()


def test_set_active_status_deactivates_and_reactivates(service: TenantService) -> None:
    created = service.create_tenant(_new_tenant_payload())
    try:
        deactivated = service.set_active_status(created.TenantId, False)
        assert deactivated.IsActive is False

        reactivated = service.set_active_status(created.TenantId, True)
        assert reactivated.IsActive is True
    finally:
        service.db.delete(created)
        service.db.commit()


def test_deactivate_tenant_with_no_tenancies_succeeds(service: TenantService) -> None:
    created = service.create_tenant(_new_tenant_payload())
    try:
        result = service.deactivate_tenant(created.TenantId)
        assert result.IsActive is False
    finally:
        service.db.delete(created)
        service.db.commit()


def test_deactivate_tenant_with_active_tenancy_is_blocked_and_leaves_it_unchanged(
    service: TenantService,
) -> None:
    john = service.db.execute(select(Tenant).where(Tenant.Email == "john.okafor@example.com")).scalar_one()

    with pytest.raises(AppError) as exc_info:
        service.deactivate_tenant(john.TenantId)

    assert exc_info.value.code == "TENANT_HAS_ACTIVE_TENANCY"
    assert exc_info.value.status_code == 409

    service.db.refresh(john)
    assert john.IsActive is True
