"""Business rules for the Property module.

How PropertyStatus stays consistent with tenancy status - and what this
module does and doesn't do about it:

PropertyStatus (Vacant / Occupied / Under Maintenance / Unavailable /
Archived) is set two ways here: manually via PATCH /api/properties/{id}/status
(staff judgment call - e.g. flagging a property "Under Maintenance"), or
automatically to "Archived" when the property is deactivated. This module
does NOT automatically flip a property to "Occupied" when a tenancy starts,
or back to "Vacant" when one ends - that synchronization inherently belongs
to tenancy lifecycle transitions (activating/ending a tenancy), which don't
exist as a module yet. It will be implemented in TenancyService (a later
milestone) as part of the SAME database transaction that changes the
tenancy's own status - see documentation/database-design.md's note on the
service layer owning the tenancy-property consistency rule. Building it
here, ahead of the Tenancy module existing, would mean guessing at an
interface that module hasn't defined yet.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.property import Property
from app.repositories.landlord_repository import LandlordRepository
from app.repositories.property_repository import PropertyRepository, SortDirection, SortField
from app.schemas.property import PropertyCreate, PropertyUpdate
from app.utilities.datetime_utils import utc_now


class PropertyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = PropertyRepository(db)
        self.landlord_repository = LandlordRepository(db)

    def list_properties(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        landlord_id: int | None,
        city: str | None,
        property_type: str | None,
        property_status: str | None,
        is_active: bool | None,
        sort_by: SortField,
        sort_dir: SortDirection,
    ) -> tuple[Sequence[Property], int]:
        return self.repository.list(
            page=page,
            page_size=page_size,
            search=search,
            landlord_id=landlord_id,
            city=city,
            property_type=property_type,
            property_status=property_status,
            is_active=is_active,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

    def get_property(self, property_id: int) -> Property:
        property_ = self.repository.get_by_id(property_id)
        if property_ is None:
            raise AppError("PROPERTY_NOT_FOUND", f"No property found with id {property_id}.", status_code=404)
        return property_

    def create_property(self, data: PropertyCreate) -> Property:
        self._ensure_landlord_exists(data.LandlordId)
        self._ensure_reference_not_taken(data.PropertyReference, exclude_property_id=None)

        property_ = Property(**data.model_dump(), PropertyStatus="Vacant", IsActive=True)
        self.repository.add(property_)
        self.db.commit()
        self.db.refresh(property_)
        return property_

    def update_property(self, property_id: int, data: PropertyUpdate) -> Property:
        property_ = self.get_property(property_id)
        self._ensure_landlord_exists(data.LandlordId)
        self._ensure_reference_not_taken(data.PropertyReference, exclude_property_id=property_id)

        for field, value in data.model_dump().items():
            setattr(property_, field, value)
        property_.UpdatedAt = utc_now()

        self.db.commit()
        self.db.refresh(property_)
        return property_

    def set_property_status(self, property_id: int, new_status: str) -> Property:
        property_ = self.get_property(property_id)
        property_.PropertyStatus = new_status
        property_.UpdatedAt = utc_now()

        self.db.commit()
        self.db.refresh(property_)
        return property_

    def deactivate_property(self, property_id: int) -> Property:
        """Handles DELETE /api/properties/{id}. Same soft-delete-only
        philosophy as LandlordService.deactivate_landlord - see that
        method's docstring. Also sets PropertyStatus to Archived, matching
        how the seeded demo data represents a deactivated property (PM-0010
        is both IsActive=0 and PropertyStatus='Archived' together, not one
        without the other).
        """
        property_ = self.get_property(property_id)

        if self.repository.has_active_tenancies(property_id):
            raise AppError(
                "PROPERTY_HAS_ACTIVE_TENANCIES",
                "This property has an active, upcoming, or draft tenancy and cannot be deleted. "
                "End or cancel the tenancy first.",
                status_code=409,
            )

        property_.IsActive = False
        property_.PropertyStatus = "Archived"
        property_.UpdatedAt = utc_now()
        self.db.commit()
        self.db.refresh(property_)
        return property_

    def _ensure_landlord_exists(self, landlord_id: int) -> None:
        if self.landlord_repository.get_by_id(landlord_id) is None:
            raise AppError("LANDLORD_NOT_FOUND", f"No landlord found with id {landlord_id}.", status_code=404)

    def _ensure_reference_not_taken(self, reference: str, *, exclude_property_id: int | None) -> None:
        existing = self.repository.get_by_reference(reference)
        if existing is not None and existing.PropertyId != exclude_property_id:
            raise AppError(
                "DUPLICATE_PROPERTY_REFERENCE",
                f"A property with reference '{reference}' already exists.",
                status_code=409,
            )
