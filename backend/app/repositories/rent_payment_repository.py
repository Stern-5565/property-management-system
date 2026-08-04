"""Database access for the RentPayment module - no business rules here.

Filtering by property or tenant requires joining through Tenancy, since
RentPayments only has a direct FK to Tenancies, not to Properties or
Tenants.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.rent_payment import RentPayment
from app.models.tenancy import Tenancy


class RentPaymentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, payment_id: int) -> RentPayment | None:
        return self.db.get(RentPayment, payment_id)

    def get_by_reference(self, reference: str) -> RentPayment | None:
        stmt = select(RentPayment).where(RentPayment.PaymentReference == reference)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        *,
        page: int,
        page_size: int,
        tenancy_id: int | None,
        property_id: int | None,
        tenant_id: int | None,
        payment_status: str | None,
        due_date_from: date | None,
        due_date_to: date | None,
    ) -> tuple[Sequence[RentPayment], int]:
        stmt = select(RentPayment).join(Tenancy, RentPayment.TenancyId == Tenancy.TenancyId)
        conditions = []

        if tenancy_id is not None:
            conditions.append(RentPayment.TenancyId == tenancy_id)
        if property_id is not None:
            conditions.append(Tenancy.PropertyId == property_id)
        if tenant_id is not None:
            conditions.append(Tenancy.TenantId == tenant_id)
        if payment_status is not None:
            # Filters on the STORED status column, which can lag reality
            # for a Pending row that has silently become Overdue purely by
            # the calendar moving on (no scheduled sweep job recomputes it -
            # see RentPaymentService's module docstring). For a guaranteed-
            # accurate overdue list, use list_overdue() below instead.
            conditions.append(RentPayment.PaymentStatus == payment_status)
        if due_date_from is not None:
            conditions.append(RentPayment.DueDate >= due_date_from)
        if due_date_to is not None:
            conditions.append(RentPayment.DueDate < due_date_to)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        stmt = stmt.order_by(RentPayment.DueDate.desc()).offset((page - 1) * page_size).limit(page_size)
        items = self.db.execute(stmt).scalars().all()
        return items, total_items

    def list_overdue(self) -> Sequence[RentPayment]:
        """Mirrors database/07-report-queries.sql, Report 2 exactly:
        recalculated live from DueDate/AmountPaid/AmountDue rather than
        trusting the stored PaymentStatus column, for the same reason
        Report 2 does - see that report's comment block."""
        today = date.today()
        stmt = (
            select(RentPayment)
            .where(
                RentPayment.PaymentStatus != "Cancelled",
                RentPayment.DueDate < today,
                RentPayment.AmountPaid < RentPayment.AmountDue,
            )
            .order_by(RentPayment.DueDate)
        )
        return self.db.execute(stmt).scalars().all()

    def list_due_this_month(self) -> Sequence[RentPayment]:
        """Mirrors database/07-report-queries.sql, Report 1 exactly: a
        sargable date-range comparison rather than wrapping DueDate in
        YEAR()/MONTH() (which would prevent an index seek)."""
        today = date.today()
        month_start = today.replace(day=1)
        next_month_start = (month_start + timedelta(days=32)).replace(day=1)
        stmt = (
            select(RentPayment)
            .where(
                RentPayment.PaymentStatus != "Cancelled",
                RentPayment.DueDate >= month_start,
                RentPayment.DueDate < next_month_start,
            )
            .order_by(RentPayment.DueDate)
        )
        return self.db.execute(stmt).scalars().all()

    def add(self, payment: RentPayment) -> RentPayment:
        self.db.add(payment)
        self.db.flush()  # assigns RentPaymentId via IDENTITY without committing
        return payment
