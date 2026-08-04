"""HTTP routes for the Dashboard module.

All read-only (no request bodies, no write actions) - routes just parse
query parameters and call one DashboardService method. See that file for
what each figure means and how empty-database/division-by-zero cases are
handled.

Permission model: Administrator/PropertyManager/ReadOnly can view;
MaintenanceEmployee cannot (the dashboard mixes in financial figures) -
see app/core/roles.py's CAN_VIEW_DASHBOARD comment.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.auth import require_roles
from app.api.dependencies.dashboard import get_dashboard_service
from app.core.roles import CAN_VIEW_DASHBOARD
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    MaintenanceSummaryResponse,
    OccupancyResponse,
    RecentActivityResponse,
    RentSummaryResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(
    prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(require_roles(*CAN_VIEW_DASHBOARD))]
)


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_summary(service: DashboardService = Depends(get_dashboard_service)) -> DashboardSummaryResponse:
    return service.get_summary()


@router.get("/rent-summary", response_model=RentSummaryResponse)
def get_rent_summary(
    months_back: int = Query(6, ge=1, le=24, description="How many months (including the current one) the chart covers"),
    service: DashboardService = Depends(get_dashboard_service),
) -> RentSummaryResponse:
    return service.get_rent_summary(months_back=months_back)


@router.get("/occupancy", response_model=OccupancyResponse)
def get_occupancy(service: DashboardService = Depends(get_dashboard_service)) -> OccupancyResponse:
    return service.get_occupancy()


@router.get("/maintenance-summary", response_model=MaintenanceSummaryResponse)
def get_maintenance_summary(service: DashboardService = Depends(get_dashboard_service)) -> MaintenanceSummaryResponse:
    return service.get_maintenance_summary()


@router.get("/recent-activity", response_model=RecentActivityResponse)
def get_recent_activity(
    limit: int = Query(10, ge=1, le=100),
    service: DashboardService = Depends(get_dashboard_service),
) -> RecentActivityResponse:
    return service.get_recent_activity(limit=limit)
