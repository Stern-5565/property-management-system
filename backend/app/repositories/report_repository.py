"""Database access for the Reports module (Prompt 25).

Every method here mirrors one of the 10 MVP reports in
database/07-report-queries.sql exactly - same filters, same NULL
handling, same sargable date-range comparisons - translated into
SQLAlchemy. That file's own comment blocks explain the *business*
reasoning (why exclude Cancelled, why LEFT JOIN instead of INNER JOIN,
why a sargable range beats wrapping a column in a function); this file
only notes where the SQLAlchemy translation itself needed a different
shape than the raw SQL:

- SQL Server's OUTER APPLY (a correlated per-row subquery) has no direct
  SQLAlchemy equivalent that reads as cleanly as the raw T-SQL. Report 6
  and Report 10 use a GROUP BY subquery LEFT JOINed back to the outer
  query instead - the standard, portable SQL pattern for "aggregate per
  key, then attach that aggregate back to each row" - which is exactly
  what OUTER APPLY was doing here (it was never doing true per-row
  correlation beyond a simple aggregate).
- SQL Server's `SUM(COUNT(*)) OVER ()` window function (Report 5a's
  percentage-of-portfolio column) is computed in Python instead, same
  "small result set, easier to test" reasoning DashboardService already
  uses for its own percentage math (see safe_percentage there) - this
  module has its own copy of that same tiny pure function rather than
  importing across modules for a 3-line helper.
- Every `COALESCE(CompanyName, FirstName + LastName)` landlord-name
  build and `AddressLine1 + ', ' + City` address build happens in Python
  after the fetch, not via func.concat/func.coalesce - same reasoning as
  every other module's response-building code (e.g.
  MaintenanceRequestResponse.from_request's "FirstName LastName" combos):
  simpler to read, and avoids SQL Server's NULL-propagates-through-+
  behavior needing yet another ISNULL wrapper.
- Any query joining both Tenant and Landlord in one SELECT (only Report 2
  does this) explicitly `.label()`s the Landlord side's FirstName/
  LastName - both models have columns with those exact names, and
  Core's Row would otherwise have two same-named columns with only the
  last one addressable by attribute.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.landlord import Landlord
from app.models.maintenance_request import MaintenanceRequest
from app.models.property import Property
from app.models.rent_payment import RentPayment
from app.models.tenancy import Tenancy
from app.models.tenant import Tenant

_MAINTENANCE_PRIORITY_RANK = {"Emergency": 1, "High": 2, "Medium": 3, "Low": 4}


def _landlord_name(company_name: str | None, first_name: str | None, last_name: str | None) -> str:
    return company_name or f"{first_name} {last_name}"


def _current_month_range() -> tuple[date, date]:
    today = date.today()
    month_start = today.replace(day=1)
    return month_start, _shift_months(month_start, 1)


def _shift_months(start: date, offset: int) -> date:
    zero_based_month = start.month - 1 + offset
    year = start.year + zero_based_month // 12
    month = zero_based_month % 12 + 1
    return date(year, month, 1)


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- Report 1: Rent due this month ----------

    def rent_due_this_month(self, *, property_id: int | None) -> list[dict]:
        month_start, next_month_start = _current_month_range()
        stmt = (
            select(
                RentPayment.RentPaymentId,
                Property.PropertyReference,
                Property.AddressLine1,
                Property.City,
                Tenant.FirstName,
                Tenant.LastName,
                RentPayment.DueDate,
                RentPayment.AmountDue,
                RentPayment.AmountPaid,
                RentPayment.PaymentStatus,
            )
            .join(Tenancy, Tenancy.TenancyId == RentPayment.TenancyId)
            .join(Property, Property.PropertyId == Tenancy.PropertyId)
            .join(Tenant, Tenant.TenantId == Tenancy.TenantId)
            .where(
                RentPayment.PaymentStatus != "Cancelled",
                RentPayment.DueDate >= month_start,
                RentPayment.DueDate < next_month_start,
            )
            .order_by(RentPayment.DueDate, Property.PropertyReference)
        )
        if property_id is not None:
            stmt = stmt.where(Tenancy.PropertyId == property_id)
        rows = self.db.execute(stmt).all()
        return [
            {
                "RentPaymentId": r.RentPaymentId,
                "PropertyReference": r.PropertyReference,
                "PropertyAddress": f"{r.AddressLine1}, {r.City}",
                "TenantName": f"{r.FirstName} {r.LastName}",
                "DueDate": r.DueDate,
                "AmountDue": r.AmountDue,
                "AmountPaid": r.AmountPaid,
                "AmountOutstanding": r.AmountDue - r.AmountPaid,
                "PaymentStatus": r.PaymentStatus,
            }
            for r in rows
        ]

    # ---------- Report 2: Overdue rent ----------

    def overdue_rent(self, *, property_id: int | None, landlord_id: int | None) -> list[dict]:
        today = date.today()
        stmt = (
            select(
                RentPayment.RentPaymentId,
                Property.PropertyReference,
                Tenant.FirstName,
                Tenant.LastName,
                Landlord.CompanyName,
                Landlord.FirstName.label("LandlordFirstName"),
                Landlord.LastName.label("LandlordLastName"),
                RentPayment.DueDate,
                RentPayment.AmountDue,
                RentPayment.AmountPaid,
            )
            .join(Tenancy, Tenancy.TenancyId == RentPayment.TenancyId)
            .join(Property, Property.PropertyId == Tenancy.PropertyId)
            .join(Tenant, Tenant.TenantId == Tenancy.TenantId)
            .join(Landlord, Landlord.LandlordId == Property.LandlordId)
            .where(
                RentPayment.PaymentStatus != "Cancelled",
                RentPayment.DueDate < today,
                RentPayment.AmountPaid < RentPayment.AmountDue,
            )
        )
        if property_id is not None:
            stmt = stmt.where(Tenancy.PropertyId == property_id)
        if landlord_id is not None:
            stmt = stmt.where(Property.LandlordId == landlord_id)
        rows = self.db.execute(stmt).all()
        result = [
            {
                "RentPaymentId": r.RentPaymentId,
                "PropertyReference": r.PropertyReference,
                "TenantName": f"{r.FirstName} {r.LastName}",
                "LandlordName": _landlord_name(r.CompanyName, r.LandlordFirstName, r.LandlordLastName),
                "DueDate": r.DueDate,
                "DaysOverdue": (today - r.DueDate).days,
                "AmountDue": r.AmountDue,
                "AmountPaid": r.AmountPaid,
                "AmountOutstanding": r.AmountDue - r.AmountPaid,
            }
            for r in rows
        ]
        result.sort(key=lambda row: row["DaysOverdue"], reverse=True)
        return result

    # ---------- Report 3: Monthly rent collected ----------

    def monthly_rent_collected(self, *, period_start: date | None, period_end: date | None) -> list[dict]:
        year_col = func.year(RentPayment.PaymentDate)
        month_col = func.month(RentPayment.PaymentDate)
        stmt = (
            select(
                year_col.label("PaymentYear"),
                month_col.label("PaymentMonth"),
                func.count().label("PaymentCount"),
                func.coalesce(func.sum(RentPayment.AmountPaid), 0).label("TotalCollected"),
            )
            .where(RentPayment.PaymentStatus.in_(("Paid", "Partially Paid")), RentPayment.PaymentDate.is_not(None))
            .group_by(year_col, month_col)
            .order_by(year_col, month_col)
        )
        if period_start is not None:
            stmt = stmt.where(RentPayment.PaymentDate >= period_start)
        if period_end is not None:
            stmt = stmt.where(RentPayment.PaymentDate < period_end)
        rows = self.db.execute(stmt).all()
        return [
            {
                "MonthLabel": f"{calendar.month_name[r.PaymentMonth]} {r.PaymentYear}",
                "PaymentCount": r.PaymentCount,
                "TotalCollected": r.TotalCollected,
            }
            for r in rows
        ]

    # ---------- Report 4: Rent collected by landlord ----------

    def rent_by_landlord(self, *, period_start: date, period_end: date, landlord_id: int | None) -> list[dict]:
        total_collected = func.coalesce(func.sum(RentPayment.AmountPaid), 0)
        stmt = (
            select(
                Landlord.CompanyName,
                Landlord.FirstName,
                Landlord.LastName,
                func.count(func.distinct(Property.PropertyId)).label("PropertyCount"),
                total_collected.label("TotalCollected"),
            )
            .outerjoin(Property, (Property.LandlordId == Landlord.LandlordId) & (Property.IsActive == True))  # noqa: E712
            .outerjoin(Tenancy, Tenancy.PropertyId == Property.PropertyId)
            .outerjoin(
                RentPayment,
                (RentPayment.TenancyId == Tenancy.TenancyId)
                & (RentPayment.PaymentStatus.in_(("Paid", "Partially Paid")))
                & (RentPayment.PaymentDate >= period_start)
                & (RentPayment.PaymentDate < period_end),
            )
            .where(Landlord.IsActive == True)  # noqa: E712
            .group_by(Landlord.LandlordId, Landlord.CompanyName, Landlord.FirstName, Landlord.LastName)
            .order_by(total_collected.desc())
        )
        if landlord_id is not None:
            stmt = stmt.where(Landlord.LandlordId == landlord_id)
        rows = self.db.execute(stmt).all()
        return [
            {
                "LandlordName": _landlord_name(r.CompanyName, r.FirstName, r.LastName),
                "PropertyCount": r.PropertyCount,
                "TotalCollected": r.TotalCollected,
            }
            for r in rows
        ]

    # ---------- Report 5: Occupancy ----------

    def occupancy(self) -> tuple[list[dict], dict]:
        stmt = (
            select(Property.PropertyStatus, func.count().label("PropertyCount"))
            .where(Property.IsActive == True)  # noqa: E712
            .group_by(Property.PropertyStatus)
            .order_by(func.count().desc())
        )
        breakdown = self.db.execute(stmt).all()
        total = sum(row.PropertyCount for row in breakdown)
        rows = [
            {
                "PropertyStatus": row.PropertyStatus,
                "PropertyCount": row.PropertyCount,
                "PercentageOfPortfolio": round(row.PropertyCount * 100.0 / total, 1) if total else 0.0,
            }
            for row in breakdown
        ]
        occupied = next((row.PropertyCount for row in breakdown if row.PropertyStatus == "Occupied"), 0)
        totals = {
            "PropertyCount": total,
            "OccupancyRatePercent": round(occupied * 100.0 / total, 1) if total else 0.0,
        }
        return rows, totals

    # ---------- Report 6: Vacant properties ----------

    def vacant_properties(self, *, landlord_id: int | None) -> list[dict]:
        last_end_subq = (
            select(Tenancy.PropertyId.label("PropertyId"), func.max(Tenancy.EndDate).label("LastEndDate"))
            .where(Tenancy.TenancyStatus.in_(("Ended", "Cancelled")))
            .group_by(Tenancy.PropertyId)
            .subquery()
        )
        stmt = (
            select(
                Property.PropertyReference,
                Property.AddressLine1,
                Property.City,
                Property.Postcode,
                Property.PropertyType,
                Property.Bedrooms,
                Property.Bathrooms,
                Property.MonthlyRent,
                Property.DateAcquired,
                Landlord.CompanyName,
                Landlord.FirstName,
                Landlord.LastName,
                Landlord.Phone,
                Landlord.Email,
                last_end_subq.c.LastEndDate,
            )
            .join(Landlord, Landlord.LandlordId == Property.LandlordId)
            .outerjoin(last_end_subq, last_end_subq.c.PropertyId == Property.PropertyId)
            .where(Property.PropertyStatus == "Vacant", Property.IsActive == True)  # noqa: E712
        )
        if landlord_id is not None:
            stmt = stmt.where(Property.LandlordId == landlord_id)
        rows = self.db.execute(stmt).all()
        today = date.today()
        result = []
        for r in rows:
            reference_date = r.LastEndDate or r.DateAcquired
            days_vacant = (today - reference_date).days if reference_date else None
            result.append(
                {
                    "PropertyReference": r.PropertyReference,
                    "Address": f"{r.AddressLine1}, {r.City}, {r.Postcode}",
                    "PropertyType": r.PropertyType,
                    "Bedrooms": r.Bedrooms,
                    "Bathrooms": r.Bathrooms,
                    "MonthlyRent": r.MonthlyRent,
                    "LandlordName": _landlord_name(r.CompanyName, r.FirstName, r.LastName),
                    "LandlordPhone": r.Phone,
                    "LandlordEmail": r.Email,
                    "DaysVacant": days_vacant,
                }
            )
        result.sort(key=lambda row: (row["DaysVacant"] is None, -(row["DaysVacant"] or 0)))
        return result

    # ---------- Report 7: Tenancies ending within N days ----------

    def tenancies_ending_soon(self, *, days_ahead: int, property_id: int | None) -> list[dict]:
        today = date.today()
        cutoff = today + timedelta(days=days_ahead)
        stmt = (
            select(
                Tenancy.AgreementReference,
                Property.PropertyReference,
                Property.AddressLine1,
                Property.City,
                Tenant.FirstName,
                Tenant.LastName,
                Tenancy.EndDate,
                Tenancy.TenancyStatus,
            )
            .join(Property, Property.PropertyId == Tenancy.PropertyId)
            .join(Tenant, Tenant.TenantId == Tenancy.TenantId)
            .where(
                Tenancy.TenancyStatus.in_(("Active", "Ending Soon")),
                Tenancy.EndDate.is_not(None),
                Tenancy.EndDate >= today,
                Tenancy.EndDate < cutoff,
            )
            .order_by(Tenancy.EndDate)
        )
        if property_id is not None:
            stmt = stmt.where(Tenancy.PropertyId == property_id)
        rows = self.db.execute(stmt).all()
        return [
            {
                "AgreementReference": r.AgreementReference,
                "PropertyReference": r.PropertyReference,
                "PropertyAddress": f"{r.AddressLine1}, {r.City}",
                "TenantName": f"{r.FirstName} {r.LastName}",
                "EndDate": r.EndDate,
                "DaysUntilEnd": (r.EndDate - today).days,
                "TenancyStatus": r.TenancyStatus,
            }
            for r in rows
        ]

    # ---------- Report 8: Open maintenance by status and priority ----------

    def maintenance_by_status(self) -> list[dict]:
        stmt = (
            select(MaintenanceRequest.MaintenanceStatus, MaintenanceRequest.Priority, func.count().label("RequestCount"))
            .where(MaintenanceRequest.MaintenanceStatus.notin_(("Completed", "Cancelled")))
            .group_by(MaintenanceRequest.MaintenanceStatus, MaintenanceRequest.Priority)
        )
        rows = self.db.execute(stmt).all()
        sorted_rows = sorted(rows, key=lambda r: (_MAINTENANCE_PRIORITY_RANK.get(r.Priority, 5), r.MaintenanceStatus))
        return [
            {"MaintenanceStatus": r.MaintenanceStatus, "Priority": r.Priority, "RequestCount": r.RequestCount}
            for r in sorted_rows
        ]

    # ---------- Report 9: Maintenance costs by property ----------

    def maintenance_costs_by_property(self, *, landlord_id: int | None) -> list[dict]:
        total_cost = func.coalesce(func.sum(MaintenanceRequest.ActualCost), 0)
        avg_cost = func.coalesce(func.avg(MaintenanceRequest.ActualCost), 0)
        stmt = (
            select(
                Property.PropertyReference,
                Property.AddressLine1,
                Property.City,
                Landlord.CompanyName,
                Landlord.FirstName,
                Landlord.LastName,
                func.count(MaintenanceRequest.MaintenanceRequestId).label("CompletedRequestCount"),
                total_cost.label("TotalActualCost"),
                avg_cost.label("AverageActualCost"),
            )
            .join(Landlord, Landlord.LandlordId == Property.LandlordId)
            .outerjoin(
                MaintenanceRequest,
                (MaintenanceRequest.PropertyId == Property.PropertyId)
                & (MaintenanceRequest.MaintenanceStatus == "Completed"),
            )
            .where(Property.IsActive == True)  # noqa: E712
            .group_by(
                Property.PropertyId,
                Property.PropertyReference,
                Property.AddressLine1,
                Property.City,
                Landlord.CompanyName,
                Landlord.FirstName,
                Landlord.LastName,
            )
            .order_by(total_cost.desc())
        )
        if landlord_id is not None:
            stmt = stmt.where(Property.LandlordId == landlord_id)
        rows = self.db.execute(stmt).all()
        return [
            {
                "PropertyReference": r.PropertyReference,
                "PropertyAddress": f"{r.AddressLine1}, {r.City}",
                "LandlordName": _landlord_name(r.CompanyName, r.FirstName, r.LastName),
                "CompletedRequestCount": r.CompletedRequestCount,
                "TotalActualCost": r.TotalActualCost,
                # SQL Server's AVG() on a NUMERIC(10,2) column returns
                # extra decimal places (e.g. 112.500000) - round back to
                # money precision rather than exposing that to the client.
                "AverageActualCost": round(r.AverageActualCost, 2),
            }
            for r in rows
        ]

    # ---------- Report 10: Property income and performance ----------

    def property_income(self, *, period_start: date, period_end: date, landlord_id: int | None) -> list[dict]:
        rent_subq = (
            select(
                Tenancy.PropertyId.label("PropertyId"),
                func.sum(RentPayment.AmountDue).label("TotalRentDue"),
                func.sum(RentPayment.AmountPaid).label("TotalRentCollected"),
            )
            .join(RentPayment, RentPayment.TenancyId == Tenancy.TenancyId)
            .where(
                RentPayment.PaymentStatus != "Cancelled",
                RentPayment.DueDate >= period_start,
                RentPayment.DueDate < period_end,
            )
            .group_by(Tenancy.PropertyId)
            .subquery()
        )
        maint_subq = (
            select(
                MaintenanceRequest.PropertyId.label("PropertyId"),
                func.sum(MaintenanceRequest.ActualCost).label("TotalMaintenanceCost"),
            )
            .where(
                MaintenanceRequest.MaintenanceStatus == "Completed",
                MaintenanceRequest.CompletedDate >= period_start,
                MaintenanceRequest.CompletedDate < period_end,
            )
            .group_by(MaintenanceRequest.PropertyId)
            .subquery()
        )
        stmt = (
            select(
                Property.PropertyReference,
                Property.AddressLine1,
                Property.City,
                Landlord.CompanyName,
                Landlord.FirstName,
                Landlord.LastName,
                rent_subq.c.TotalRentDue,
                rent_subq.c.TotalRentCollected,
                maint_subq.c.TotalMaintenanceCost,
            )
            .join(Landlord, Landlord.LandlordId == Property.LandlordId)
            .outerjoin(rent_subq, rent_subq.c.PropertyId == Property.PropertyId)
            .outerjoin(maint_subq, maint_subq.c.PropertyId == Property.PropertyId)
            .where(Property.IsActive == True)  # noqa: E712
        )
        if landlord_id is not None:
            stmt = stmt.where(Property.LandlordId == landlord_id)
        rows = self.db.execute(stmt).all()
        result = []
        for r in rows:
            total_due = r.TotalRentDue or Decimal("0.00")
            total_collected = r.TotalRentCollected or Decimal("0.00")
            maint_cost = r.TotalMaintenanceCost or Decimal("0.00")
            collection_rate = round(float(total_collected) * 100.0 / float(total_due), 1) if total_due else 0.0
            result.append(
                {
                    "PropertyReference": r.PropertyReference,
                    "PropertyAddress": f"{r.AddressLine1}, {r.City}",
                    "LandlordName": _landlord_name(r.CompanyName, r.FirstName, r.LastName),
                    "TotalRentDue": total_due,
                    "TotalRentCollected": total_collected,
                    "CollectionRatePercent": collection_rate,
                    "TotalMaintenanceCost": maint_cost,
                    "NetIncome": total_collected - maint_cost,
                }
            )
        result.sort(key=lambda row: row["NetIncome"], reverse=True)
        return result
