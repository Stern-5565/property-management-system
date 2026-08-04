"""Tests for PropertyService - business rules.

Uses a throwaway property (created and torn down per test) rather than
mutating any of the 10 seeded demo properties - same reasoning as
test_landlord_service.py.
"""

import pytest
from sqlalchemy import select

from app.core.exceptions import AppError
from app.database.session import SessionLocal
from app.models.landlord import Landlord
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyUpdate
from app.services.property_service import PropertyService


@pytest.fixture
def service():
    db = SessionLocal()
    try:
        yield PropertyService(db)
    finally:
        db.close()


@pytest.fixture
def robert_jenkins_id(service: PropertyService) -> int:
    landlord = service.db.execute(select(Landlord).where(Landlord.Email == "robert.jenkins@example.com")).scalar_one()
    return landlord.LandlordId


def _new_property_payload(landlord_id: int, **overrides) -> PropertyCreate:
    defaults = {
        "LandlordId": landlord_id,
        "PropertyReference": "PM-TEST-001",
        "AddressLine1": "1 Fixture Street",
        "City": "Testville",
        "Postcode": "TE1 1ST",
        "Country": "United Kingdom",
        "PropertyType": "Flat",
        "Bedrooms": 2,
        "Bathrooms": 1,
        "MonthlyRent": "1000.00",
    }
    defaults.update(overrides)
    return PropertyCreate(**defaults)


def test_create_property_starts_vacant_and_active(service: PropertyService, robert_jenkins_id: int) -> None:
    created = service.create_property(_new_property_payload(robert_jenkins_id))
    try:
        assert created.PropertyStatus == "Vacant"
        assert created.IsActive is True
        assert created.LandlordId == robert_jenkins_id
    finally:
        service.db.delete(created)
        service.db.commit()


def test_create_property_rejects_unknown_landlord(service: PropertyService) -> None:
    with pytest.raises(AppError) as exc_info:
        service.create_property(_new_property_payload(999_999))
    assert exc_info.value.code == "LANDLORD_NOT_FOUND"
    assert exc_info.value.status_code == 404


def test_create_property_rejects_duplicate_reference(service: PropertyService, robert_jenkins_id: int) -> None:
    created = service.create_property(_new_property_payload(robert_jenkins_id))
    try:
        with pytest.raises(AppError) as exc_info:
            service.create_property(_new_property_payload(robert_jenkins_id, AddressLine1="2 Different Street"))
        assert exc_info.value.code == "DUPLICATE_PROPERTY_REFERENCE"
        assert exc_info.value.status_code == 409
    finally:
        service.db.delete(created)
        service.db.commit()


def test_get_property_raises_not_found_for_missing_id(service: PropertyService) -> None:
    with pytest.raises(AppError) as exc_info:
        service.get_property(999_999)
    assert exc_info.value.code == "PROPERTY_NOT_FOUND"
    assert exc_info.value.status_code == 404


def test_update_property_changes_fields(service: PropertyService, robert_jenkins_id: int) -> None:
    created = service.create_property(_new_property_payload(robert_jenkins_id))
    try:
        updated = service.update_property(
            created.PropertyId,
            PropertyUpdate(
                **{
                    **_new_property_payload(robert_jenkins_id).model_dump(),
                    "MonthlyRent": "1250.00",
                    "Bedrooms": 3,
                }
            ),
        )
        assert updated.MonthlyRent == 1250
        assert updated.Bedrooms == 3
    finally:
        service.db.delete(created)
        service.db.commit()


def test_update_property_allows_keeping_its_own_reference(service: PropertyService, robert_jenkins_id: int) -> None:
    created = service.create_property(_new_property_payload(robert_jenkins_id))
    try:
        updated = service.update_property(created.PropertyId, _new_property_payload(robert_jenkins_id))
        assert updated.PropertyReference == "PM-TEST-001"
    finally:
        service.db.delete(created)
        service.db.commit()


def test_set_property_status_updates_status(service: PropertyService, robert_jenkins_id: int) -> None:
    created = service.create_property(_new_property_payload(robert_jenkins_id))
    try:
        updated = service.set_property_status(created.PropertyId, "Under Maintenance")
        assert updated.PropertyStatus == "Under Maintenance"
    finally:
        service.db.delete(created)
        service.db.commit()


def test_deactivate_property_with_no_tenancies_succeeds(service: PropertyService, robert_jenkins_id: int) -> None:
    created = service.create_property(_new_property_payload(robert_jenkins_id))
    try:
        result = service.deactivate_property(created.PropertyId)
        assert result.IsActive is False
        assert result.PropertyStatus == "Archived"
    finally:
        service.db.delete(created)
        service.db.commit()


def test_deactivate_property_with_active_tenancy_is_blocked_and_leaves_it_unchanged(
    service: PropertyService,
) -> None:
    pm_0003 = service.db.execute(select(Property).where(Property.PropertyReference == "PM-0003")).scalar_one()

    with pytest.raises(AppError) as exc_info:
        service.deactivate_property(pm_0003.PropertyId)

    assert exc_info.value.code == "PROPERTY_HAS_ACTIVE_TENANCIES"
    assert exc_info.value.status_code == 409

    service.db.refresh(pm_0003)
    assert pm_0003.IsActive is True
    assert pm_0003.PropertyStatus == "Occupied"
