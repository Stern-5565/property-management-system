"""Database access for the Property module - no business rules here."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.tenancy import Tenancy

# Statuses that mean "this tenancy is live or about to be" - used to decide
# whether a property is safe to deactivate. Ended/Cancelled tenancies don't
# block deactivation; everything else does.
_ACTIVE_TENANCY_STATUSES = ("Draft", "Upcoming", "Active", "Ending Soon")

SortField = Literal["PropertyReference", "MonthlyRent", "City", "CreatedAt"]
SortDirection = Literal["asc", "desc"]

_SORT_COLUMNS = {
    "PropertyReference": Property.PropertyReference,
    "MonthlyRent": Property.MonthlyRent,
    "City": Property.City,
    "CreatedAt": Property.CreatedAt,
}


class PropertyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, property_id: int) -> Property | None:
        return self.db.get(Property, property_id)

    def get_by_reference(self, reference: str) -> Property | None:
        stmt = select(Property).where(Property.PropertyReference == reference)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
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
        stmt = select(Property)
        conditions = []

        if landlord_id is not None:
            conditions.append(Property.LandlordId == landlord_id)
        if city:
            conditions.append(Property.City == city)
        if property_type:
            conditions.append(Property.PropertyType == property_type)
        if property_status:
            conditions.append(Property.PropertyStatus == property_status)
        if is_active is not None:
            conditions.append(Property.IsActive == is_active)  # noqa: E712 - see landlord_repository.py

        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(
                    Property.PropertyReference.ilike(pattern),
                    Property.AddressLine1.ilike(pattern),
                    Property.AddressLine2.ilike(pattern),
                    Property.City.ilike(pattern),
                    Property.Postcode.ilike(pattern),
                )
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        sort_column = _SORT_COLUMNS[sort_by]
        order_clause = sort_column.desc() if sort_dir == "desc" else sort_column.asc()
        stmt = stmt.order_by(order_clause).offset((page - 1) * page_size).limit(page_size)

        items = self.db.execute(stmt).scalars().all()
        return items, total_items

    def has_active_tenancies(self, property_id: int) -> bool:
        stmt = (
            select(func.count())
            .select_from(Tenancy)
            .where(Tenancy.PropertyId == property_id, Tenancy.TenancyStatus.in_(_ACTIVE_TENANCY_STATUSES))
        )
        return self.db.execute(stmt).scalar_one() > 0

    def add(self, property_: Property) -> Property:
        self.db.add(property_)
        self.db.flush()  # assigns PropertyId via IDENTITY without committing
        return property_
