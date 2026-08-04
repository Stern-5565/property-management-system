"""Tests for the Landlord Pydantic schemas.

These are pure schema/validation tests - no database involved - covering
the business rules that matter most: the company-or-full-name rule, email
format validation, rejection of system-controlled/unexpected fields, and
that a response schema can be built from a real ORM row.
"""

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.database.session import SessionLocal
from app.models import Landlord
from app.schemas.landlord import LandlordCreate, LandlordListItem, LandlordResponse, LandlordStatusUpdate


def test_create_with_company_name_only_is_valid() -> None:
    landlord = LandlordCreate(
        CompanyName="Acme Lettings Ltd",
        AddressLine1="1 High Street",
        City="London",
        Postcode="E1 6AN",
        Country="United Kingdom",
    )
    assert landlord.CompanyName == "Acme Lettings Ltd"
    assert landlord.FirstName is None


def test_create_with_first_and_last_name_only_is_valid() -> None:
    landlord = LandlordCreate(
        FirstName="Jane",
        LastName="Smith",
        AddressLine1="1 High Street",
        City="London",
        Postcode="E1 6AN",
        Country="United Kingdom",
    )
    assert landlord.FirstName == "Jane"
    assert landlord.CompanyName is None


def test_create_without_company_or_full_name_is_rejected() -> None:
    with pytest.raises(ValidationError, match="CompanyName, or both FirstName and LastName"):
        LandlordCreate(
            FirstName="Jane",  # LastName missing, no CompanyName either
            AddressLine1="1 High Street",
            City="London",
            Postcode="E1 6AN",
            Country="United Kingdom",
        )


def test_create_with_invalid_email_is_rejected() -> None:
    with pytest.raises(ValidationError):
        LandlordCreate(
            CompanyName="Acme Lettings Ltd",
            Email="not-an-email",
            AddressLine1="1 High Street",
            City="London",
            Postcode="E1 6AN",
            Country="United Kingdom",
        )


def test_create_with_blank_required_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        LandlordCreate(
            CompanyName="Acme Lettings Ltd",
            AddressLine1="   ",  # whitespace-only, stripped to empty
            City="London",
            Postcode="E1 6AN",
            Country="United Kingdom",
        )


def test_create_rejects_system_controlled_fields() -> None:
    """A client trying to set LandlordId or IsActive should get a 422, not
    have the field silently dropped - extra="forbid" makes that explicit."""
    with pytest.raises(ValidationError, match="LandlordId"):
        LandlordCreate(
            LandlordId=999,
            CompanyName="Acme Lettings Ltd",
            AddressLine1="1 High Street",
            City="London",
            Postcode="E1 6AN",
            Country="United Kingdom",
        )


def test_status_update_only_accepts_is_active() -> None:
    status_update = LandlordStatusUpdate(IsActive=False)
    assert status_update.IsActive is False

    with pytest.raises(ValidationError):
        LandlordStatusUpdate(IsActive=False, CompanyName="Sneaky Ltd")  # type: ignore[call-arg]


def test_response_schema_builds_from_real_orm_row_and_computes_display_name() -> None:
    with SessionLocal() as db:
        landlord = db.execute(
            select(Landlord).where(Landlord.CompanyName == "Green Oak Properties Ltd")
        ).scalar_one()

        response = LandlordResponse.model_validate(landlord)

        assert response.LandlordId == landlord.LandlordId
        assert response.DisplayName == "Green Oak Properties Ltd"
        assert response.IsActive is True


def test_response_schema_display_name_falls_back_to_full_name() -> None:
    with SessionLocal() as db:
        landlord = db.execute(
            select(Landlord).where(Landlord.FirstName == "Robert", Landlord.LastName == "Jenkins")
        ).scalar_one()

        response = LandlordResponse.model_validate(landlord)

        assert response.DisplayName == "Robert Jenkins"


def test_list_item_schema_builds_from_real_orm_row() -> None:
    with SessionLocal() as db:
        landlord = db.execute(
            select(Landlord).where(Landlord.CompanyName == "Henderson Estates Ltd")
        ).scalar_one()

        list_item = LandlordListItem.model_validate(landlord)

        assert list_item.DisplayName == "Henderson Estates Ltd"
        assert list_item.City == "Leeds"
