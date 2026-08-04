"""Database access for the Landlord module.

No business rules here - only queries. Duplicate-email checks, not-found
handling, and the "can this landlord be deleted" decision all live in
LandlordService, which is the only thing that should be calling this class.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.landlord import Landlord
from app.models.property import Property


class LandlordRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, landlord_id: int) -> Landlord | None:
        return self.db.get(Landlord, landlord_id)

    def get_by_email(self, email: str) -> Landlord | None:
        stmt = select(Landlord).where(Landlord.Email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        is_active: bool | None,
    ) -> tuple[Sequence[Landlord], int]:
        stmt = select(Landlord)
        conditions = []

        if is_active is not None:
            # Not .is_(is_active): SQL Server's IS operator only accepts
            # NULL (IS NULL / IS NOT NULL), not boolean literals - SQLAlchemy
            # happily compiles .is_(True) to invalid T-SQL ("IS 1") on the
            # mssql dialect. Plain equality is what BIT columns need.
            conditions.append(Landlord.IsActive == is_active)  # noqa: E712

        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(
                    Landlord.FirstName.ilike(pattern),
                    Landlord.LastName.ilike(pattern),
                    Landlord.CompanyName.ilike(pattern),
                    Landlord.Email.ilike(pattern),
                    Landlord.Phone.ilike(pattern),
                )
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        stmt = (
            stmt.order_by(Landlord.CompanyName, Landlord.LastName, Landlord.FirstName)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = self.db.execute(stmt).scalars().all()

        return items, total_items

    def has_active_properties(self, landlord_id: int) -> bool:
        stmt = (
            select(func.count())
            .select_from(Property)
            .where(Property.LandlordId == landlord_id, Property.IsActive == True)  # noqa: E712
        )
        return self.db.execute(stmt).scalar_one() > 0

    def add(self, landlord: Landlord) -> Landlord:
        self.db.add(landlord)
        self.db.flush()  # assigns LandlordId via IDENTITY without committing the transaction
        return landlord
