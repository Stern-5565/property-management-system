"""Tests for TenancyService - business rules. Covers the 8 scenarios the
scope doc explicitly asks for: valid creation, invalid date ordering,
overlapping tenancy, inactive property, inactive tenant, activation,
ending, and property status update - plus a few more (cancel, duplicate
agreement reference, edit-lock after activation).

Uses throwaway Property/Tenant/Tenancy rows, never the seeded demo data.
Cleanup order matters: any Tenancy rows a test creates must be deleted
BEFORE the throwaway_property/throwaway_tenant fixtures try to delete
their own rows, since Tenancies.PropertyId/TenantId are foreign keys with
NO ACTION on delete - a lingering Tenancy row would make the fixture
teardown itself fail. Each test therefore cleans up its own tenancies in
its own try/finally, before fixture teardown ever runs.
"""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.core.exceptions import AppError
from app.database.session import SessionLocal
from app.models.landlord import Landlord
from app.schemas.property import PropertyCreate
from app.schemas.tenancy import TenancyCreate, TenancyUpdate
from app.schemas.tenant import TenantCreate
from app.services.property_service import PropertyService
from app.services.tenancy_service import TenancyService
from app.services.tenant_service import TenantService

TODAY = date.today()


@pytest.fixture
def service():
    db = SessionLocal()
    try:
        yield TenancyService(db)
    finally:
        db.close()


@pytest.fixture
def throwaway_property(service: TenancyService):
    prop_service = PropertyService(service.db)
    landlord = service.db.execute(select(Landlord).where(Landlord.Email == "robert.jenkins@example.com")).scalar_one()
    prop = prop_service.create_property(
        PropertyCreate(
            LandlordId=landlord.LandlordId,
            PropertyReference="PM-TENANCY-SVC-001",
            AddressLine1="1 Tenancy Test St",
            City="Testville",
            Postcode="TE1 1ST",
            Country="United Kingdom",
            PropertyType="Flat",
            Bedrooms=2,
            Bathrooms=1,
            MonthlyRent="1000.00",
        )
    )
    try:
        yield prop
    finally:
        service.db.delete(prop)
        service.db.commit()


@pytest.fixture
def throwaway_tenant(service: TenancyService):
    tenant_service = TenantService(service.db)
    tenant = tenant_service.create_tenant(
        TenantCreate(FirstName="Test", LastName="TenancyFixture", Email="test.tenancyfixture@example.com")
    )
    try:
        yield tenant
    finally:
        service.db.delete(tenant)
        service.db.commit()


def _payload(property_id: int, tenant_id: int, **overrides) -> TenancyCreate:
    defaults = {
        "PropertyId": property_id,
        "TenantId": tenant_id,
        "StartDate": TODAY - timedelta(days=10),
        "EndDate": TODAY + timedelta(days=355),
        "MonthlyRent": "1000.00",
        "PaymentDueDay": 1,
    }
    defaults.update(overrides)
    return TenancyCreate(**defaults)


def _delete_tenancy(service: TenancyService, tenancy) -> None:
    service.db.delete(tenancy)
    service.db.commit()


# ---------- 1. Valid tenancy creation ----------


def test_create_draft_tenancy_succeeds(service: TenancyService, throwaway_property, throwaway_tenant, admin_user_id) -> None:
    tenancy = service.create_draft_tenancy(_payload(throwaway_property.PropertyId, throwaway_tenant.TenantId), user_id=admin_user_id)
    try:
        assert tenancy.TenancyStatus == "Draft"
        assert tenancy.PropertyId == throwaway_property.PropertyId
    finally:
        _delete_tenancy(service, tenancy)


# ---------- 2. Invalid date ordering ----------


def test_create_tenancy_rejects_end_date_before_start_date(throwaway_property, throwaway_tenant) -> None:
    """Rejected at the schema layer, before the service is even reached."""
    with pytest.raises(ValidationError, match="End date must be after the start date"):
        _payload(
            throwaway_property.PropertyId,
            throwaway_tenant.TenantId,
            StartDate=TODAY,
            EndDate=TODAY - timedelta(days=1),
        )


# ---------- 3. Overlapping tenancy ----------


def test_activate_rejects_overlapping_tenancy_on_same_property(
    service: TenancyService, throwaway_property, throwaway_tenant, admin_user_id
) -> None:
    tenant_service = TenantService(service.db)
    second_tenant = tenant_service.create_tenant(
        TenantCreate(FirstName="Second", LastName="TenancyFixture", Email="second.tenancyfixture@example.com")
    )

    first = service.create_draft_tenancy(
        _payload(throwaway_property.PropertyId, throwaway_tenant.TenantId, StartDate=TODAY - timedelta(days=5)),
        user_id=admin_user_id,
    )
    second = service.create_draft_tenancy(
        _payload(throwaway_property.PropertyId, second_tenant.TenantId, StartDate=TODAY, EndDate=TODAY + timedelta(days=100)),
        user_id=admin_user_id,
    )
    try:
        activated_first = service.activate_tenancy(first.TenancyId, user_id=admin_user_id)
        assert activated_first.TenancyStatus == "Active"

        with pytest.raises(AppError) as exc_info:
            service.activate_tenancy(second.TenancyId, user_id=admin_user_id)
        assert exc_info.value.code == "TENANCY_DATE_CONFLICT"
        assert exc_info.value.status_code == 409
        assert exc_info.value.details["conflicting_tenancy_id"] == first.TenancyId
    finally:
        _delete_tenancy(service, second)
        _delete_tenancy(service, first)
        service.db.delete(second_tenant)
        service.db.commit()


# ---------- 4. Inactive property ----------


def test_activate_rejects_inactive_property(
    service: TenancyService, throwaway_property, throwaway_tenant, admin_user_id
) -> None:
    tenancy = service.create_draft_tenancy(
        _payload(throwaway_property.PropertyId, throwaway_tenant.TenantId), user_id=admin_user_id
    )
    try:
        # NOT via PropertyService.deactivate_property(): that method
        # correctly REFUSES to deactivate a property that still has a
        # Draft tenancy referencing it (PropertyRepository.has_active_tenancies
        # treats Draft as a live status, same as Property/TenantRepository
        # everywhere else) - so the normal API can't even reach the
        # scenario this test needs. Setting the flag directly simulates
        # "somehow this property is inactive" (e.g. deactivated by another
        # process) so TenancyService's own defense-in-depth check is what's
        # actually under test here, not PropertyService's.
        throwaway_property.IsActive = False
        service.db.commit()

        with pytest.raises(AppError) as exc_info:
            service.activate_tenancy(tenancy.TenancyId, user_id=admin_user_id)
        assert exc_info.value.code == "PROPERTY_INACTIVE"
        assert exc_info.value.status_code == 409
    finally:
        _delete_tenancy(service, tenancy)
        throwaway_property.IsActive = True  # restore for fixture teardown clarity
        service.db.commit()


# ---------- 5. Inactive tenant ----------


def test_activate_rejects_inactive_tenant(
    service: TenancyService, throwaway_property, throwaway_tenant, admin_user_id
) -> None:
    tenant_service = TenantService(service.db)
    tenancy = service.create_draft_tenancy(
        _payload(throwaway_property.PropertyId, throwaway_tenant.TenantId), user_id=admin_user_id
    )
    try:
        tenant_service.set_active_status(throwaway_tenant.TenantId, False)

        with pytest.raises(AppError) as exc_info:
            service.activate_tenancy(tenancy.TenancyId, user_id=admin_user_id)
        assert exc_info.value.code == "TENANT_INACTIVE"
        assert exc_info.value.status_code == 409
    finally:
        _delete_tenancy(service, tenancy)
        tenant_service.set_active_status(throwaway_tenant.TenantId, True)  # restore for fixture teardown clarity


# ---------- 6. Tenancy activation (+ 8. property status update) ----------


def test_activate_tenancy_starting_today_sets_active_and_occupies_property(
    service: TenancyService, throwaway_property, throwaway_tenant, admin_user_id
) -> None:
    tenancy = service.create_draft_tenancy(
        _payload(throwaway_property.PropertyId, throwaway_tenant.TenantId, StartDate=TODAY), user_id=admin_user_id
    )
    try:
        activated = service.activate_tenancy(tenancy.TenancyId, user_id=admin_user_id)
        assert activated.TenancyStatus == "Active"
        assert activated.CheckInDate == TODAY

        service.property_repository.db.refresh(throwaway_property)
        assert throwaway_property.PropertyStatus == "Occupied"
    finally:
        _delete_tenancy(service, tenancy)


def test_activate_tenancy_starting_in_future_sets_upcoming_not_active(
    service: TenancyService, throwaway_property, throwaway_tenant, admin_user_id
) -> None:
    tenancy = service.create_draft_tenancy(
        _payload(throwaway_property.PropertyId, throwaway_tenant.TenantId, StartDate=TODAY + timedelta(days=30)),
        user_id=admin_user_id,
    )
    try:
        activated = service.activate_tenancy(tenancy.TenancyId, user_id=admin_user_id)
        assert activated.TenancyStatus == "Upcoming"

        # A future-dated tenancy shouldn't occupy the property yet.
        service.property_repository.db.refresh(throwaway_property)
        assert throwaway_property.PropertyStatus == "Vacant"
    finally:
        _delete_tenancy(service, tenancy)


def test_activate_tenancy_that_is_not_draft_is_rejected(
    service: TenancyService, throwaway_property, throwaway_tenant, admin_user_id
) -> None:
    tenancy = service.create_draft_tenancy(
        _payload(throwaway_property.PropertyId, throwaway_tenant.TenantId, StartDate=TODAY), user_id=admin_user_id
    )
    try:
        service.activate_tenancy(tenancy.TenancyId, user_id=admin_user_id)

        with pytest.raises(AppError) as exc_info:
            service.activate_tenancy(tenancy.TenancyId, user_id=admin_user_id)
        assert exc_info.value.code == "TENANCY_NOT_DRAFT"
    finally:
        _delete_tenancy(service, tenancy)


# ---------- 7. Tenancy ending (+ 8. property status update again) ----------


def test_end_tenancy_sets_ended_and_vacates_property(
    service: TenancyService, throwaway_property, throwaway_tenant, admin_user_id
) -> None:
    # StartDate must be BEFORE today, not today: ending "today" (end_date=None
    # defaults to date.today()) would otherwise set EndDate == StartDate,
    # violating CK_Tenancies_DateOrder's strict EndDate > StartDate - the
    # exact scenario TenancyService.end_tenancy's own guard now rejects
    # before it ever reaches the database (see test below).
    tenancy = service.create_draft_tenancy(
        _payload(throwaway_property.PropertyId, throwaway_tenant.TenantId, StartDate=TODAY - timedelta(days=5)),
        user_id=admin_user_id,
    )
    try:
        service.activate_tenancy(tenancy.TenancyId, user_id=admin_user_id)

        ended = service.end_tenancy(tenancy.TenancyId, end_date=None, user_id=admin_user_id)
        assert ended.TenancyStatus == "Ended"
        assert ended.EndDate == TODAY
        assert ended.CheckOutDate == TODAY

        service.property_repository.db.refresh(throwaway_property)
        assert throwaway_property.PropertyStatus == "Vacant"
    finally:
        _delete_tenancy(service, tenancy)


def test_end_tenancy_that_is_not_active_is_rejected(
    service: TenancyService, throwaway_property, throwaway_tenant, admin_user_id
) -> None:
    tenancy = service.create_draft_tenancy(
        _payload(throwaway_property.PropertyId, throwaway_tenant.TenantId), user_id=admin_user_id
    )
    try:
        with pytest.raises(AppError) as exc_info:
            service.end_tenancy(tenancy.TenancyId, end_date=None, user_id=admin_user_id)
        assert exc_info.value.code == "TENANCY_NOT_ACTIVE"
    finally:
        _delete_tenancy(service, tenancy)


# ---------- Cancel ----------


def test_cancel_active_tenancy_vacates_property(
    service: TenancyService, throwaway_property, throwaway_tenant, admin_user_id
) -> None:
    tenancy = service.create_draft_tenancy(
        _payload(throwaway_property.PropertyId, throwaway_tenant.TenantId, StartDate=TODAY), user_id=admin_user_id
    )
    try:
        service.activate_tenancy(tenancy.TenancyId, user_id=admin_user_id)

        cancelled = service.cancel_tenancy(tenancy.TenancyId, user_id=admin_user_id)
        assert cancelled.TenancyStatus == "Cancelled"

        service.property_repository.db.refresh(throwaway_property)
        assert throwaway_property.PropertyStatus == "Vacant"
    finally:
        _delete_tenancy(service, tenancy)


def test_cancel_already_ended_tenancy_is_rejected(
    service: TenancyService, throwaway_property, throwaway_tenant, admin_user_id
) -> None:
    tenancy = service.create_draft_tenancy(
        _payload(throwaway_property.PropertyId, throwaway_tenant.TenantId, StartDate=TODAY - timedelta(days=5)),
        user_id=admin_user_id,
    )
    try:
        service.activate_tenancy(tenancy.TenancyId, user_id=admin_user_id)
        service.end_tenancy(tenancy.TenancyId, end_date=None, user_id=admin_user_id)

        with pytest.raises(AppError) as exc_info:
            service.cancel_tenancy(tenancy.TenancyId, user_id=admin_user_id)
        assert exc_info.value.code == "TENANCY_ALREADY_FINAL"
    finally:
        _delete_tenancy(service, tenancy)


def test_end_tenancy_rejects_end_date_not_after_start_date(
    service: TenancyService, throwaway_property, throwaway_tenant, admin_user_id
) -> None:
    """A tenancy that starts today cannot be ended "today" too - EndDate
    must be strictly after StartDate (CK_Tenancies_DateOrder). Without this
    guard, the request would instead fail as a raw SQL constraint
    violation (a 500) at commit time - a real bug caught while writing
    test_end_tenancy_sets_ended_and_vacates_property above."""
    tenancy = service.create_draft_tenancy(
        _payload(throwaway_property.PropertyId, throwaway_tenant.TenantId, StartDate=TODAY), user_id=admin_user_id
    )
    try:
        service.activate_tenancy(tenancy.TenancyId, user_id=admin_user_id)

        with pytest.raises(AppError) as exc_info:
            service.end_tenancy(tenancy.TenancyId, end_date=TODAY, user_id=admin_user_id)
        assert exc_info.value.code == "TENANCY_INVALID_END_DATE"
        assert exc_info.value.status_code == 409
    finally:
        _delete_tenancy(service, tenancy)


# ---------- Update / edit lock ----------


def test_update_tenancy_is_rejected_once_no_longer_draft(
    service: TenancyService, throwaway_property, throwaway_tenant, admin_user_id
) -> None:
    tenancy = service.create_draft_tenancy(
        _payload(throwaway_property.PropertyId, throwaway_tenant.TenantId, StartDate=TODAY), user_id=admin_user_id
    )
    try:
        service.activate_tenancy(tenancy.TenancyId, user_id=admin_user_id)

        with pytest.raises(AppError) as exc_info:
            service.update_tenancy(
                tenancy.TenancyId,
                TenancyUpdate(**_payload(throwaway_property.PropertyId, throwaway_tenant.TenantId).model_dump()),
                user_id=admin_user_id,
            )
        assert exc_info.value.code == "TENANCY_NOT_EDITABLE"
    finally:
        _delete_tenancy(service, tenancy)


def test_create_tenancy_rejects_duplicate_agreement_reference(
    service: TenancyService, throwaway_property, throwaway_tenant, admin_user_id
) -> None:
    tenancy = service.create_draft_tenancy(
        _payload(throwaway_property.PropertyId, throwaway_tenant.TenantId, AgreementReference="AGR-TENANCY-SVC-001"),
        user_id=admin_user_id,
    )
    try:
        with pytest.raises(AppError) as exc_info:
            service.create_draft_tenancy(
                _payload(
                    throwaway_property.PropertyId,
                    throwaway_tenant.TenantId,
                    StartDate=TODAY + timedelta(days=400),
                    EndDate=TODAY + timedelta(days=700),
                    AgreementReference="AGR-TENANCY-SVC-001",
                ),
                user_id=admin_user_id,
            )
        assert exc_info.value.code == "DUPLICATE_AGREEMENT_REFERENCE"
    finally:
        _delete_tenancy(service, tenancy)
