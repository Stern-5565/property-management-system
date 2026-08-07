"""Business logic for the Reports module (Prompt 25).

Each `get_<report>` method: resolves default filter values (several
reports default to "this month" or "year to date", mirroring
database/07-report-queries.sql's own DECLARE defaults), calls the
matching ReportRepository method, and wraps the result in the shared
`ReportResponse` envelope (title/description/columns/rows/totals) - the
"reusable reporting pattern" Prompt 25 asks for lives here and in
`app/schemas/reports.py`, not in 10 divergent response shapes.

Permission enforcement itself lives on the router (one
`CAN_VIEW_REPORTS` gate for the whole `/api/reports` prefix, same
"set once on the APIRouter" pattern as `app/api/routes/dashboard.py`) -
this service has no role-awareness of its own, same division of
responsibility as DashboardService.

Totals only appear where summing a column is actually meaningful (never
a TenantName or a PropertyStatus) - `_sum` is a tiny helper for that,
used instead of running a second SUM query, since every report's row set
is already small enough to sum in Python (matches this module's own
established "small result set, aggregate in Python" precedent - see
DashboardService.safe_percentage and this module's own
ReportRepository.occupancy).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.report_repository import ReportRepository
from app.schemas.reports import ReportColumn, ReportResponse
from app.utilities.datetime_utils import utc_now


def _sum(rows: list[dict], key: str) -> Decimal:
    return sum((row[key] for row in rows), Decimal("0.00"))


def _current_month_range() -> tuple[date, date]:
    today = date.today()
    month_start = today.replace(day=1)
    next_month = month_start.month % 12 + 1
    next_year = month_start.year + (1 if month_start.month == 12 else 0)
    return month_start, date(next_year, next_month, 1)


def _year_to_date_range() -> tuple[date, date]:
    today = date.today()
    return date(today.year, 1, 1), today + timedelta(days=1)


class ReportService:
    def __init__(self, db: Session) -> None:
        self.repository = ReportRepository(db)

    def get_rent_due_this_month(self, *, property_id: int | None) -> ReportResponse:
        rows = self.repository.rent_due_this_month(property_id=property_id)
        columns = [
            ReportColumn(key="PropertyReference", header="Property", type="string"),
            ReportColumn(key="PropertyAddress", header="Address", type="string"),
            ReportColumn(key="TenantName", header="Tenant", type="string"),
            ReportColumn(key="DueDate", header="Due Date", type="date"),
            ReportColumn(key="AmountDue", header="Amount Due", type="currency"),
            ReportColumn(key="AmountPaid", header="Amount Paid", type="currency"),
            ReportColumn(key="AmountOutstanding", header="Outstanding", type="currency"),
            ReportColumn(key="PaymentStatus", header="Status", type="string"),
        ]
        totals = {
            "AmountDue": _sum(rows, "AmountDue"),
            "AmountPaid": _sum(rows, "AmountPaid"),
            "AmountOutstanding": _sum(rows, "AmountOutstanding"),
        }
        return ReportResponse(
            ReportKey="rent-due-this-month",
            Title="Rent Due This Month",
            Description="Every non-cancelled rent obligation due in the current calendar month, regardless of whether it has been paid yet.",
            Columns=columns,
            Rows=rows,
            Totals=totals,
            GeneratedAt=utc_now(),
        )

    def get_overdue_rent(self, *, property_id: int | None, landlord_id: int | None) -> ReportResponse:
        rows = self.repository.overdue_rent(property_id=property_id, landlord_id=landlord_id)
        columns = [
            ReportColumn(key="PropertyReference", header="Property", type="string"),
            ReportColumn(key="TenantName", header="Tenant", type="string"),
            ReportColumn(key="LandlordName", header="Landlord", type="string"),
            ReportColumn(key="DueDate", header="Due Date", type="date"),
            ReportColumn(key="DaysOverdue", header="Days Overdue", type="integer"),
            ReportColumn(key="AmountDue", header="Amount Due", type="currency"),
            ReportColumn(key="AmountPaid", header="Amount Paid", type="currency"),
            ReportColumn(key="AmountOutstanding", header="Outstanding", type="currency"),
        ]
        totals = {"AmountOutstanding": _sum(rows, "AmountOutstanding")}
        return ReportResponse(
            ReportKey="overdue-rent",
            Title="Overdue Rent",
            Description="Rent payments whose due date has passed and are not yet fully paid, calculated live rather than trusting the stored status.",
            Columns=columns,
            Rows=rows,
            Totals=totals,
            GeneratedAt=utc_now(),
        )

    def get_monthly_rent_collected(self, *, period_start: date | None, period_end: date | None) -> ReportResponse:
        rows = self.repository.monthly_rent_collected(period_start=period_start, period_end=period_end)
        columns = [
            ReportColumn(key="MonthLabel", header="Month", type="string"),
            ReportColumn(key="PaymentCount", header="Payments", type="integer"),
            ReportColumn(key="TotalCollected", header="Total Collected", type="currency"),
        ]
        totals = {"PaymentCount": sum(row["PaymentCount"] for row in rows), "TotalCollected": _sum(rows, "TotalCollected")}
        return ReportResponse(
            ReportKey="monthly-rent-collected",
            Title="Monthly Rent Collected",
            Description="Cash actually collected, grouped by the month it was paid (not the month it was due).",
            Columns=columns,
            Rows=rows,
            Totals=totals,
            GeneratedAt=utc_now(),
        )

    def get_rent_by_landlord(
        self, *, period_start: date | None, period_end: date | None, landlord_id: int | None
    ) -> ReportResponse:
        if period_start is None or period_end is None:
            period_start, period_end = _current_month_range()
        rows = self.repository.rent_by_landlord(period_start=period_start, period_end=period_end, landlord_id=landlord_id)
        columns = [
            ReportColumn(key="LandlordName", header="Landlord", type="string"),
            ReportColumn(key="PropertyCount", header="Properties", type="integer"),
            ReportColumn(key="TotalCollected", header="Total Collected", type="currency"),
        ]
        totals = {"TotalCollected": _sum(rows, "TotalCollected")}
        return ReportResponse(
            ReportKey="rent-by-landlord",
            Title="Rent Collected by Landlord",
            Description="How much has been collected on each active landlord's behalf during the selected period.",
            Columns=columns,
            Rows=rows,
            Totals=totals,
            GeneratedAt=utc_now(),
        )

    def get_occupancy(self) -> ReportResponse:
        rows, totals = self.repository.occupancy()
        columns = [
            ReportColumn(key="PropertyStatus", header="Status", type="string"),
            ReportColumn(key="PropertyCount", header="Properties", type="integer"),
            ReportColumn(key="PercentageOfPortfolio", header="% of Portfolio", type="percent"),
        ]
        return ReportResponse(
            ReportKey="occupancy",
            Title="Occupancy Report",
            Description="Active portfolio broken down by property status, plus the headline occupancy rate.",
            Columns=columns,
            Rows=rows,
            Totals=totals,
            GeneratedAt=utc_now(),
        )

    def get_vacant_properties(self, *, landlord_id: int | None) -> ReportResponse:
        rows = self.repository.vacant_properties(landlord_id=landlord_id)
        columns = [
            ReportColumn(key="PropertyReference", header="Property", type="string"),
            ReportColumn(key="Address", header="Address", type="string"),
            ReportColumn(key="PropertyType", header="Type", type="string"),
            ReportColumn(key="Bedrooms", header="Beds", type="integer"),
            ReportColumn(key="Bathrooms", header="Baths", type="integer"),
            ReportColumn(key="MonthlyRent", header="Monthly Rent", type="currency"),
            ReportColumn(key="LandlordName", header="Landlord", type="string"),
            ReportColumn(key="LandlordPhone", header="Landlord Phone", type="string"),
            ReportColumn(key="LandlordEmail", header="Landlord Email", type="string"),
            ReportColumn(key="DaysVacant", header="Days Vacant", type="integer"),
        ]
        totals = {"MonthlyRent": _sum(rows, "MonthlyRent")}
        return ReportResponse(
            ReportKey="vacant-properties",
            Title="Vacant Properties",
            Description="Active properties currently vacant, with how long each has been empty, so re-letting can be prioritised.",
            Columns=columns,
            Rows=rows,
            Totals=totals,
            GeneratedAt=utc_now(),
        )

    def get_tenancies_ending_soon(self, *, days_ahead: int, property_id: int | None) -> ReportResponse:
        rows = self.repository.tenancies_ending_soon(days_ahead=days_ahead, property_id=property_id)
        columns = [
            ReportColumn(key="AgreementReference", header="Agreement", type="string"),
            ReportColumn(key="PropertyReference", header="Property", type="string"),
            ReportColumn(key="PropertyAddress", header="Address", type="string"),
            ReportColumn(key="TenantName", header="Tenant", type="string"),
            ReportColumn(key="EndDate", header="End Date", type="date"),
            ReportColumn(key="DaysUntilEnd", header="Days Until End", type="integer"),
            ReportColumn(key="TenancyStatus", header="Status", type="string"),
        ]
        return ReportResponse(
            ReportKey="tenancies-ending-soon",
            Title="Tenancies Ending Soon",
            Description=f"Active or Ending Soon tenancies with an end date in the next {days_ahead} days.",
            Columns=columns,
            Rows=rows,
            Totals=None,
            GeneratedAt=utc_now(),
        )

    def get_maintenance_by_status(self) -> ReportResponse:
        rows = self.repository.maintenance_by_status()
        columns = [
            ReportColumn(key="MaintenanceStatus", header="Status", type="string"),
            ReportColumn(key="Priority", header="Priority", type="string"),
            ReportColumn(key="RequestCount", header="Requests", type="integer"),
        ]
        totals = {"RequestCount": sum(row["RequestCount"] for row in rows)}
        return ReportResponse(
            ReportKey="maintenance-by-status",
            Title="Open Maintenance by Status and Priority",
            Description="Every maintenance request not yet Completed or Cancelled, broken down by status and priority.",
            Columns=columns,
            Rows=rows,
            Totals=totals,
            GeneratedAt=utc_now(),
        )

    def get_maintenance_costs_by_property(self, *, landlord_id: int | None) -> ReportResponse:
        rows = self.repository.maintenance_costs_by_property(landlord_id=landlord_id)
        columns = [
            ReportColumn(key="PropertyReference", header="Property", type="string"),
            ReportColumn(key="PropertyAddress", header="Address", type="string"),
            ReportColumn(key="LandlordName", header="Landlord", type="string"),
            ReportColumn(key="CompletedRequestCount", header="Completed Requests", type="integer"),
            ReportColumn(key="TotalActualCost", header="Total Cost", type="currency"),
            ReportColumn(key="AverageActualCost", header="Average Cost", type="currency"),
        ]
        totals = {
            "CompletedRequestCount": sum(row["CompletedRequestCount"] for row in rows),
            "TotalActualCost": _sum(rows, "TotalActualCost"),
        }
        return ReportResponse(
            ReportKey="maintenance-costs-by-property",
            Title="Maintenance Costs by Property",
            Description="Actual completed-maintenance spend per active property - estimates on open requests are excluded.",
            Columns=columns,
            Rows=rows,
            Totals=totals,
            GeneratedAt=utc_now(),
        )

    def get_property_income(self, *, period_start: date | None, period_end: date | None, landlord_id: int | None) -> ReportResponse:
        if period_start is None or period_end is None:
            period_start, period_end = _year_to_date_range()
        rows = self.repository.property_income(period_start=period_start, period_end=period_end, landlord_id=landlord_id)
        columns = [
            ReportColumn(key="PropertyReference", header="Property", type="string"),
            ReportColumn(key="PropertyAddress", header="Address", type="string"),
            ReportColumn(key="LandlordName", header="Landlord", type="string"),
            ReportColumn(key="TotalRentDue", header="Rent Due", type="currency"),
            ReportColumn(key="TotalRentCollected", header="Rent Collected", type="currency"),
            ReportColumn(key="CollectionRatePercent", header="Collection Rate", type="percent"),
            ReportColumn(key="TotalMaintenanceCost", header="Maintenance Cost", type="currency"),
            ReportColumn(key="NetIncome", header="Net Income", type="currency"),
        ]
        totals = {
            "TotalRentDue": _sum(rows, "TotalRentDue"),
            "TotalRentCollected": _sum(rows, "TotalRentCollected"),
            "TotalMaintenanceCost": _sum(rows, "TotalMaintenanceCost"),
            "NetIncome": _sum(rows, "NetIncome"),
        }
        return ReportResponse(
            ReportKey="property-income",
            Title="Property Income and Performance",
            Description="Rent due vs. collected and completed maintenance cost per active property over the selected period.",
            Columns=columns,
            Rows=rows,
            Totals=totals,
            GeneratedAt=utc_now(),
        )
