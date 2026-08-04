"""Database access for the Tenancy module - no business rules here."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.tenancy import Tenancy

# "Live" statuses: a tenancy that is either currently in effect or booked
# to be. Used both for overlap checking and for "is this property already
# spoken for" checks in TenancyService.
_LIVE_STATUSES = ("Active", "Upcoming", "Ending Soon")

# A sentinel standing in for "no end date" (an open-ended/periodic
# tenancy) so overlap comparisons can use plain <=/>= instead of needing
# separate NULL-handling branches. Far enough in the future to never be a
# real tenancy's end date.
_FAR_FUTURE = date(9999, 12, 31)


class TenancyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, tenancy_id: int) -> Tenancy | None:
        return self.db.get(Tenancy, tenancy_id)

    def get_by_agreement_reference(self, reference: str) -> Tenancy | None:
        stmt = select(Tenancy).where(Tenancy.AgreementReference == reference)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        *,
        page: int,
        page_size: int,
        property_id: int | None,
        tenant_id: int | None,
        tenancy_status: str | None,
    ) -> tuple[Sequence[Tenancy], int]:
        stmt = select(Tenancy)
        conditions = []

        if property_id is not None:
            conditions.append(Tenancy.PropertyId == property_id)
        if tenant_id is not None:
            conditions.append(Tenancy.TenantId == tenant_id)
        if tenancy_status is not None:
            conditions.append(Tenancy.TenancyStatus == tenancy_status)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        stmt = stmt.order_by(Tenancy.StartDate.desc()).offset((page - 1) * page_size).limit(page_size)
        items = self.db.execute(stmt).scalars().all()
        return items, total_items

    def list_expiring(self, *, days: int) -> Sequence[Tenancy]:
        today = date.today()
        cutoff = today + timedelta(days=days)
        stmt = (
            select(Tenancy)
            .where(
                Tenancy.TenancyStatus.in_(("Active", "Ending Soon")),
                Tenancy.EndDate.is_not(None),
                Tenancy.EndDate >= today,
                Tenancy.EndDate < cutoff,
            )
            .order_by(Tenancy.EndDate)
        )
        return self.db.execute(stmt).scalars().all()

    def find_overlapping_tenancy(
        self,
        *,
        property_id: int,
        exclude_tenancy_id: int,
        start_date: date,
        end_date: date | None,
    ) -> Tenancy | None:
        """Finds another live tenancy on the same property whose date range
        overlaps [start_date, end_date]. Two ranges overlap when each one's
        start is on-or-before the other's end - using _FAR_FUTURE in place
        of a NULL end date makes an open-ended tenancy compare correctly
        without a separate NULL branch.
        """
        candidate_end = end_date or _FAR_FUTURE
        stmt = select(Tenancy).where(
            Tenancy.PropertyId == property_id,
            Tenancy.TenancyId != exclude_tenancy_id,
            Tenancy.TenancyStatus.in_(_LIVE_STATUSES),
            Tenancy.StartDate <= candidate_end,
            func.coalesce(Tenancy.EndDate, _FAR_FUTURE) >= start_date,
        )
        return self.db.execute(stmt).scalars().first()

    def has_other_live_tenancy(self, *, property_id: int, exclude_tenancy_id: int) -> bool:
        stmt = (
            select(func.count())
            .select_from(Tenancy)
            .where(
                Tenancy.PropertyId == property_id,
                Tenancy.TenancyId != exclude_tenancy_id,
                Tenancy.TenancyStatus.in_(_LIVE_STATUSES),
            )
        )
        return self.db.execute(stmt).scalar_one() > 0

    def add(self, tenancy: Tenancy) -> Tenancy:
        self.db.add(tenancy)
        self.db.flush()  # assigns TenancyId via IDENTITY without committing
        return tenancy
