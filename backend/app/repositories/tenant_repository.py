"""Database access for the Tenant module - no business rules here."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.tenancy import Tenancy
from app.models.tenant import Tenant

# Same "not yet finished" statuses as PropertyRepository - a Draft,
# Upcoming, Active or Ending Soon tenancy is a real commitment for this
# tenant, so it blocks deactivation; Ended/Cancelled don't.
_ACTIVE_TENANCY_STATUSES = ("Draft", "Upcoming", "Active", "Ending Soon")


class TenantRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, tenant_id: int) -> Tenant | None:
        return self.db.get(Tenant, tenant_id)

    def get_by_email(self, email: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.Email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        is_active: bool | None,
    ) -> tuple[Sequence[Tenant], int]:
        stmt = select(Tenant)
        conditions = []

        if is_active is not None:
            conditions.append(Tenant.IsActive == is_active)  # noqa: E712 - see landlord_repository.py

        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(
                    Tenant.FirstName.ilike(pattern),
                    Tenant.LastName.ilike(pattern),
                    Tenant.Email.ilike(pattern),
                    Tenant.Phone.ilike(pattern),
                )
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        stmt = (
            stmt.order_by(Tenant.LastName, Tenant.FirstName)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = self.db.execute(stmt).scalars().all()
        return items, total_items

    def has_active_tenancies(self, tenant_id: int) -> bool:
        stmt = (
            select(func.count())
            .select_from(Tenancy)
            .where(Tenancy.TenantId == tenant_id, Tenancy.TenancyStatus.in_(_ACTIVE_TENANCY_STATUSES))
        )
        return self.db.execute(stmt).scalar_one() > 0

    def add(self, tenant: Tenant) -> Tenant:
        self.db.add(tenant)
        self.db.flush()  # assigns TenantId via IDENTITY without committing
        return tenant
