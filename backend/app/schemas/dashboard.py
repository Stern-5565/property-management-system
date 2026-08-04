"""Pydantic schemas for the Dashboard module.

No Create/Update schemas here - the dashboard is entirely read-only, so
every schema below is a response shape. Every numeric field is
non-Optional with a concrete default (0, 0.0, or an empty list) rather
than nullable: DashboardService computes those defaults itself (see its
module docstring on empty-database handling), so a client never has to
null-check a dashboard figure - "predictable response schemas" per the
scope doc's Prompt 17 requirements.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DashboardSummaryResponse(BaseModel):
    """GET /api/dashboard/summary - the headline KPI cards."""

    TotalActiveProperties: int
    OccupiedProperties: int
    VacantProperties: int
    OccupancyPercentage: float
    ActiveTenancies: int
    RentDueThisMonth: Decimal
    RentCollectedThisMonth: Decimal
    OutstandingRent: Decimal
    OpenMaintenanceRequests: int
    EmergencyMaintenanceRequests: int
    TenanciesEndingSoon: int


class MonthlyCollectionPoint(BaseModel):
    """One bar in the "rent collected by month" chart."""

    Year: int
    Month: int
    MonthLabel: str
    PaymentCount: int
    TotalCollected: Decimal


class RentSummaryResponse(BaseModel):
    """GET /api/dashboard/rent-summary."""

    RentDueThisMonth: Decimal
    RentCollectedThisMonth: Decimal
    OutstandingRent: Decimal
    CollectionRatePercent: float
    MonthlyCollection: list[MonthlyCollectionPoint]


class PropertyStatusBreakdownItem(BaseModel):
    PropertyStatus: str
    PropertyCount: int
    PercentageOfPortfolio: float


class OccupancyResponse(BaseModel):
    """GET /api/dashboard/occupancy."""

    TotalProperties: int
    OccupiedCount: int
    VacantCount: int
    OccupancyRatePercent: float
    StatusBreakdown: list[PropertyStatusBreakdownItem]


class MaintenanceStatusBreakdownItem(BaseModel):
    MaintenanceStatus: str
    Priority: str
    RequestCount: int


class MaintenanceSummaryResponse(BaseModel):
    """GET /api/dashboard/maintenance-summary."""

    OpenRequests: int
    EmergencyRequests: int
    StatusBreakdown: list[MaintenanceStatusBreakdownItem]


class RecentActivityItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    AuditLogId: int
    UserId: int | None
    UserName: str | None
    Action: str
    EntityName: str
    EntityId: int
    CreatedAt: datetime

    @classmethod
    def from_log(cls, log) -> RecentActivityItem:
        # log.User is None for system-generated entries; a User always has
        # an Employee (non-nullable FK - see models/user.py), so no further
        # None-check is needed once log.User itself is present.
        user_name = f"{log.User.Employee.FirstName} {log.User.Employee.LastName}" if log.User else None
        return cls(
            AuditLogId=log.AuditLogId,
            UserId=log.UserId,
            UserName=user_name,
            Action=log.Action,
            EntityName=log.EntityName,
            EntityId=log.EntityId,
            CreatedAt=log.CreatedAt,
        )


RecentActivityResponse = list[RecentActivityItem]
