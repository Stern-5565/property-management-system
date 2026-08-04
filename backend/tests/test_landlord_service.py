"""Tests for LandlordService - business rules.

Write tests here create a throwaway landlord and delete it again in a
finally block, rather than relying on transaction-rollback fixtures: this
project intentionally keeps the testing pattern simple (a real
transaction-per-test setup would need to intercept session.commit() via
SQLAlchemy events to fake a rollback-able nested transaction, which is more
machinery than a learning-focused test suite needs). Explicit cleanup is a
few extra lines but easy to read and reason about, and - importantly - it
means the seeded demo dataset that OTHER tests assert exact counts against
(test_models.py, test_landlord_repository.py, ...) is never left changed.
"""

import pytest
from sqlalchemy import select

from app.core.exceptions import AppError
from app.database.session import SessionLocal
from app.models.landlord import Landlord
from app.schemas.landlord import LandlordCreate, LandlordUpdate
from app.services.landlord_service import LandlordService


@pytest.fixture
def service():
    db = SessionLocal()
    try:
        yield LandlordService(db)
    finally:
        db.close()


def _new_landlord_payload(**overrides) -> LandlordCreate:
    defaults = {
        "CompanyName": "Test Fixture Landlord Ltd",
        "Email": "test.fixture.landlord@example.com",
        "AddressLine1": "1 Test Street",
        "City": "Testville",
        "Postcode": "TE1 1ST",
        "Country": "United Kingdom",
    }
    defaults.update(overrides)
    return LandlordCreate(**defaults)


def test_create_and_get_landlord(service: LandlordService) -> None:
    created = service.create_landlord(_new_landlord_payload())
    try:
        fetched = service.get_landlord(created.LandlordId)
        assert fetched.CompanyName == "Test Fixture Landlord Ltd"
        assert fetched.IsActive is True
    finally:
        service.db.delete(created)
        service.db.commit()


def test_get_landlord_raises_not_found_for_missing_id(service: LandlordService) -> None:
    with pytest.raises(AppError) as exc_info:
        service.get_landlord(999_999)
    assert exc_info.value.code == "LANDLORD_NOT_FOUND"
    assert exc_info.value.status_code == 404


def test_create_landlord_rejects_duplicate_email(service: LandlordService) -> None:
    created = service.create_landlord(_new_landlord_payload())
    try:
        with pytest.raises(AppError) as exc_info:
            service.create_landlord(_new_landlord_payload(CompanyName="Different Name Ltd"))
        assert exc_info.value.code == "DUPLICATE_EMAIL"
        assert exc_info.value.status_code == 409
    finally:
        service.db.delete(created)
        service.db.commit()


def test_update_landlord_changes_fields_and_bumps_updated_at(service: LandlordService) -> None:
    created = service.create_landlord(_new_landlord_payload())
    original_updated_at = created.UpdatedAt
    try:
        update_data = LandlordUpdate(
            CompanyName="Renamed Fixture Ltd",
            AddressLine1="2 Test Street",
            City="Testville",
            Postcode="TE1 1ST",
            Country="United Kingdom",
        )
        updated = service.update_landlord(created.LandlordId, update_data)
        assert updated.CompanyName == "Renamed Fixture Ltd"
        assert updated.AddressLine1 == "2 Test Street"
        assert updated.UpdatedAt >= original_updated_at
    finally:
        service.db.delete(created)
        service.db.commit()


def test_update_landlord_allows_keeping_its_own_email(service: LandlordService) -> None:
    """Re-saving a landlord's own unchanged email must NOT be flagged as a
    duplicate of itself."""
    created = service.create_landlord(_new_landlord_payload())
    try:
        update_data = LandlordUpdate(
            CompanyName="Test Fixture Landlord Ltd",
            Email="test.fixture.landlord@example.com",
            AddressLine1="1 Test Street",
            City="Testville",
            Postcode="TE1 1ST",
            Country="United Kingdom",
        )
        updated = service.update_landlord(created.LandlordId, update_data)
        assert updated.Email == "test.fixture.landlord@example.com"
    finally:
        service.db.delete(created)
        service.db.commit()


def test_update_landlord_rejects_email_already_used_by_another_landlord(service: LandlordService) -> None:
    created = service.create_landlord(_new_landlord_payload())
    try:
        with pytest.raises(AppError) as exc_info:
            service.update_landlord(
                created.LandlordId,
                LandlordUpdate(
                    CompanyName="Test Fixture Landlord Ltd",
                    Email="robert.jenkins@example.com",  # belongs to a seeded landlord
                    AddressLine1="1 Test Street",
                    City="Testville",
                    Postcode="TE1 1ST",
                    Country="United Kingdom",
                ),
            )
        assert exc_info.value.code == "DUPLICATE_EMAIL"
    finally:
        service.db.delete(created)
        service.db.commit()


def test_set_active_status_deactivates_and_reactivates(service: LandlordService) -> None:
    created = service.create_landlord(_new_landlord_payload())
    try:
        deactivated = service.set_active_status(created.LandlordId, False)
        assert deactivated.IsActive is False

        reactivated = service.set_active_status(created.LandlordId, True)
        assert reactivated.IsActive is True
    finally:
        service.db.delete(created)
        service.db.commit()


def test_deactivate_landlord_with_no_properties_succeeds(service: LandlordService) -> None:
    created = service.create_landlord(_new_landlord_payload())
    try:
        result = service.deactivate_landlord(created.LandlordId)
        assert result.IsActive is False
    finally:
        service.db.delete(created)
        service.db.commit()


def test_deactivate_landlord_with_active_properties_is_blocked_and_leaves_it_unchanged(
    service: LandlordService,
) -> None:
    green_oak = service.db.execute(
        select(Landlord).where(Landlord.CompanyName == "Green Oak Properties Ltd")
    ).scalar_one()

    with pytest.raises(AppError) as exc_info:
        service.deactivate_landlord(green_oak.LandlordId)

    assert exc_info.value.code == "LANDLORD_HAS_ACTIVE_PROPERTIES"
    assert exc_info.value.status_code == 409

    # Confirm the rejected attempt didn't change the seeded landlord -
    # other tests depend on this data staying exactly as seeded.
    service.db.refresh(green_oak)
    assert green_oak.IsActive is True
