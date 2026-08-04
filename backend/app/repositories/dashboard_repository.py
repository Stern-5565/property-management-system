"""Database access for the Dashboard module.

Every method here returns pre-aggregated counts/sums, never full entity
lists - the scope doc's "avoid loading unnecessary full records" (Prompt
17) - with one deliberate exception: recent_activity, which is genuinely
a list of rows to display, not a number to aggregate, so it's capped with
`limit` and eager-loads only what it needs to render (User + Employee, to
avoid an N+1 query per row).

Each method mirrors the equivalent MVP SQL report in
database/07-report-queries.sql (noted per method) for the same date-range/
NULL-handling reasoning already documented there - this file doesn't
repeat that reasoning, only the counting/summing shape differs (a single
number or small breakdown instead of full result rows).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog
from app.models.maintenance_request import MaintenanceRequest
from app.models.property import Property
from app.models.rent_payment import RentPayment
from app.models.tenancy import Tenancy
from app.models.user import User
from app.repositories.maintenance_repository import OPEN_STATUSES as MAINTENANCE_OPEN_STATUSES

# Mirrors TenancyRepository's _LIVE_STATUSES concept, but this module only
# ever needs the single "currently in effect" status, not "in effect or
# booked to be" - Upcoming/Draft/Ending Soon are deliberately excluded from
# ActiveTenancies (they're either not yet in effect or already counted as
# Active until their status flag catches up).
_ACTIVE_TENANCY_STATUS = "Active"


class DashboardRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def occupancy_summary(self) -> tuple[int, int, int]:
        """(total, occupied, vacant) active properties - mirrors Report 5b."""
        stmt = select(
            func.count(),
            func.sum(case((Property.PropertyStatus == "Occupied", 1), else_=0)),
            func.sum(case((Property.PropertyStatus == "Vacant", 1), else_=0)),
        ).where(Property.IsActive == True)  # noqa: E712 - see landlord_repository.py
        total, occupied, vacant = self.db.execute(stmt).one()
        return total or 0, occupied or 0, vacant or 0

    def occupancy_breakdown(self) -> Sequence[tuple[str, int]]:
        """(PropertyStatus, count) for every status present - mirrors
        Report 5a, minus the percentage column (computed in Python by
        DashboardService.safe_percentage instead of a SQL window function,
        so the same zero-safe helper covers every percentage this module
        returns, not just this one)."""
        stmt = (
            select(Property.PropertyStatus, func.count())
            .where(Property.IsActive == True)  # noqa: E712
            .group_by(Property.PropertyStatus)
            .order_by(func.count().desc())
        )
        return self.db.execute(stmt).all()

    def active_tenancies_count(self) -> int:
        stmt = select(func.count()).select_from(Tenancy).where(Tenancy.TenancyStatus == _ACTIVE_TENANCY_STATUS)
        return self.db.execute(stmt).scalar_one()

    def tenancies_ending_soon_count(self, *, days_ahead: int) -> int:
        """Mirrors Report 7's filter exactly (status IN Active/Ending Soon,
        EndDate within the window), but returns just the count."""
        today = date.today()
        stmt = (
            select(func.count())
            .select_from(Tenancy)
            .where(
                Tenancy.TenancyStatus.in_(("Active", "Ending Soon")),
                Tenancy.EndDate.is_not(None),
                Tenancy.EndDate >= today,
                Tenancy.EndDate < today + timedelta(days=days_ahead),
            )
        )
        return self.db.execute(stmt).scalar_one()

    def rent_due_this_month(self) -> Decimal:
        """Mirrors Report 1's filter (excludes Cancelled, sargable date
        range on DueDate), summed rather than listed row by row."""
        month_start, next_month_start = _current_month_range()
        stmt = select(func.coalesce(func.sum(RentPayment.AmountDue), 0)).where(
            RentPayment.PaymentStatus != "Cancelled",
            RentPayment.DueDate >= month_start,
            RentPayment.DueDate < next_month_start,
        )
        return self.db.execute(stmt).scalar_one()

    def rent_collected_this_month(self) -> Decimal:
        """The current-month row of Report 3 (grouped by PaymentDate, not
        DueDate - money collected this month for rent that may have been
        due any time), summed directly rather than grouping and picking
        one row."""
        month_start, next_month_start = _current_month_range()
        stmt = select(func.coalesce(func.sum(RentPayment.AmountPaid), 0)).where(
            RentPayment.PaymentStatus.in_(("Paid", "Partially Paid")),
            RentPayment.PaymentDate.is_not(None),
            RentPayment.PaymentDate >= month_start,
            RentPayment.PaymentDate < next_month_start,
        )
        return self.db.execute(stmt).scalar_one()

    def outstanding_rent(self) -> Decimal:
        """Total unpaid balance across every non-cancelled payment
        obligation, regardless of due date - a broader "money still owed"
        figure than Report 2's "Overdue" (which requires the due date to
        have already passed). Pending obligations not yet due are still
        outstanding in the accounts-receivable sense the dashboard KPI is
        meant to answer."""
        stmt = select(func.coalesce(func.sum(RentPayment.AmountDue - RentPayment.AmountPaid), 0)).where(
            RentPayment.PaymentStatus != "Cancelled",
            RentPayment.AmountPaid < RentPayment.AmountDue,
        )
        return self.db.execute(stmt).scalar_one()

    def monthly_rent_collection(self, *, months_back: int) -> Sequence[tuple[int, int, int, Decimal]]:
        """(Year, Month, PaymentCount, TotalCollected) for the last
        `months_back` months (including the current one) - the same
        grouping as Report 3, but windowed rather than pulling the entire
        collection history, since this feeds a chart with a fixed number
        of bars. The human-readable month label Report 3 builds with
        DATENAME() is built in Python instead, by DashboardService - T-SQL
        requires DATENAME's datepart argument to be a literal keyword, not
        a bindable expression, which doesn't compose well through
        SQLAlchemy's func.*, and Python's calendar.month_name does the
        same job with no such restriction.
        """
        this_month_start, _ = _current_month_range()
        window_start = _shift_months(this_month_start, -(months_back - 1))
        year_col = func.year(RentPayment.PaymentDate)
        month_col = func.month(RentPayment.PaymentDate)
        stmt = (
            select(year_col, month_col, func.count(), func.coalesce(func.sum(RentPayment.AmountPaid), 0))
            .where(
                RentPayment.PaymentStatus.in_(("Paid", "Partially Paid")),
                RentPayment.PaymentDate.is_not(None),
                RentPayment.PaymentDate >= window_start,
            )
            .group_by(year_col, month_col)
            .order_by(year_col, month_col)
        )
        return self.db.execute(stmt).all()

    def open_maintenance_count(self) -> int:
        stmt = (
            select(func.count())
            .select_from(MaintenanceRequest)
            .where(MaintenanceRequest.MaintenanceStatus.in_(MAINTENANCE_OPEN_STATUSES))
        )
        return self.db.execute(stmt).scalar_one()

    def emergency_maintenance_count(self) -> int:
        stmt = (
            select(func.count())
            .select_from(MaintenanceRequest)
            .where(
                MaintenanceRequest.MaintenanceStatus.in_(MAINTENANCE_OPEN_STATUSES),
                MaintenanceRequest.Priority == "Emergency",
            )
        )
        return self.db.execute(stmt).scalar_one()

    def maintenance_status_breakdown(self) -> Sequence[tuple[str, str, int]]:
        """(MaintenanceStatus, Priority, count) for open requests - mirrors
        Report 8's grouping. Priority-rank ordering (Emergency first) is
        applied in Python by DashboardService, not a SQL CASE expression,
        since the result set is at most 5 statuses x 4 priorities = 20
        rows - trivial to sort in Python and easier to unit test than
        duplicating Report 8's CASE ordering in ORM code."""
        stmt = (
            select(MaintenanceRequest.MaintenanceStatus, MaintenanceRequest.Priority, func.count())
            .where(MaintenanceRequest.MaintenanceStatus.in_(MAINTENANCE_OPEN_STATUSES))
            .group_by(MaintenanceRequest.MaintenanceStatus, MaintenanceRequest.Priority)
        )
        return self.db.execute(stmt).all()

    def recent_activity(self, *, limit: int) -> Sequence[AuditLog]:
        stmt = (
            select(AuditLog)
            .options(joinedload(AuditLog.User).joinedload(User.Employee))
            .order_by(AuditLog.CreatedAt.desc(), AuditLog.AuditLogId.desc())
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()


def _current_month_range() -> tuple[date, date]:
    today = date.today()
    month_start = today.replace(day=1)
    next_month_start = _shift_months(month_start, 1)
    return month_start, next_month_start


def _shift_months(start: date, offset: int) -> date:
    """Adds `offset` whole calendar months to `start` (which must be the
    1st of its month), without pulling in a date-arithmetic library for
    what's just modular arithmetic on (year, month)."""
    zero_based_month = start.month - 1 + offset
    year = start.year + zero_based_month // 12
    month = zero_based_month % 12 + 1
    return date(year, month, 1)
