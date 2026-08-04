"""Business logic for the Dashboard module.

Handling empty databases and division-by-zero (scope doc Prompt 17):
every percentage in this module goes through safe_percentage, a pure
function (no I/O, easy to unit test in isolation - same pattern as
RentPaymentService.calculate_payment_status) that returns 0.0 instead of
raising ZeroDivisionError or propagating a NULL when the denominator is
zero - e.g. a brand new environment with zero properties still gets a
valid OccupancyPercentage of 0.0, not an error.

Every count/sum the repository can return for an empty table already
comes back as 0 (via SQL COALESCE / Python's `or 0`), so no additional
None-handling is needed above the percentage calculations here.

TenanciesEndingSoon and the "ending soon" window used throughout this
module default to the 30-day lookahead - the shortest of the three
windows (30/60/90) Report 7 supports, since a single dashboard KPI number
needs one concrete window, and 30 days is the most actionable one for a
"needs attention now" figure.
"""

from __future__ import annotations

import calendar

from sqlalchemy.orm import Session

from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    MaintenanceStatusBreakdownItem,
    MaintenanceSummaryResponse,
    MonthlyCollectionPoint,
    OccupancyResponse,
    PropertyStatusBreakdownItem,
    RecentActivityItem,
    RentSummaryResponse,
)

_TENANCIES_ENDING_SOON_DAYS = 30
_PRIORITY_RANK = {"Emergency": 0, "High": 1, "Medium": 2, "Low": 3}


def safe_percentage(numerator, denominator) -> float:
    """Returns 0.0 for a zero (or falsy) denominator instead of raising -
    see this module's docstring."""
    if not denominator:
        return 0.0
    return round(float(numerator) * 100.0 / float(denominator), 1)


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = DashboardRepository(db)

    def get_summary(self) -> DashboardSummaryResponse:
        total, occupied, vacant = self.repository.occupancy_summary()
        return DashboardSummaryResponse(
            TotalActiveProperties=total,
            OccupiedProperties=occupied,
            VacantProperties=vacant,
            OccupancyPercentage=safe_percentage(occupied, total),
            ActiveTenancies=self.repository.active_tenancies_count(),
            RentDueThisMonth=self.repository.rent_due_this_month(),
            RentCollectedThisMonth=self.repository.rent_collected_this_month(),
            OutstandingRent=self.repository.outstanding_rent(),
            OpenMaintenanceRequests=self.repository.open_maintenance_count(),
            EmergencyMaintenanceRequests=self.repository.emergency_maintenance_count(),
            TenanciesEndingSoon=self.repository.tenancies_ending_soon_count(days_ahead=_TENANCIES_ENDING_SOON_DAYS),
        )

    def get_rent_summary(self, *, months_back: int) -> RentSummaryResponse:
        due = self.repository.rent_due_this_month()
        collected = self.repository.rent_collected_this_month()
        monthly_rows = self.repository.monthly_rent_collection(months_back=months_back)
        return RentSummaryResponse(
            RentDueThisMonth=due,
            RentCollectedThisMonth=collected,
            OutstandingRent=self.repository.outstanding_rent(),
            CollectionRatePercent=safe_percentage(collected, due),
            MonthlyCollection=[
                MonthlyCollectionPoint(
                    Year=year,
                    Month=month,
                    MonthLabel=f"{calendar.month_name[month]} {year}",
                    PaymentCount=count,
                    TotalCollected=total,
                )
                for year, month, count, total in monthly_rows
            ],
        )

    def get_occupancy(self) -> OccupancyResponse:
        total, occupied, vacant = self.repository.occupancy_summary()
        breakdown = self.repository.occupancy_breakdown()
        return OccupancyResponse(
            TotalProperties=total,
            OccupiedCount=occupied,
            VacantCount=vacant,
            OccupancyRatePercent=safe_percentage(occupied, total),
            StatusBreakdown=[
                PropertyStatusBreakdownItem(
                    PropertyStatus=status, PropertyCount=count, PercentageOfPortfolio=safe_percentage(count, total)
                )
                for status, count in breakdown
            ],
        )

    def get_maintenance_summary(self) -> MaintenanceSummaryResponse:
        breakdown = self.repository.maintenance_status_breakdown()
        ranked = sorted(breakdown, key=lambda row: (_PRIORITY_RANK.get(row[1], 99), row[0]))
        return MaintenanceSummaryResponse(
            OpenRequests=self.repository.open_maintenance_count(),
            EmergencyRequests=self.repository.emergency_maintenance_count(),
            StatusBreakdown=[
                MaintenanceStatusBreakdownItem(MaintenanceStatus=status, Priority=priority, RequestCount=count)
                for status, priority, count in ranked
            ],
        )

    def get_recent_activity(self, *, limit: int) -> list[RecentActivityItem]:
        logs = self.repository.recent_activity(limit=limit)
        return [RecentActivityItem.from_log(log) for log in logs]
