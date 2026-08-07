"""HTTP routes for the Reports module (Prompt 25).

All 10 read-only. One role gate for the whole prefix (`CAN_VIEW_REPORTS`,
set once on the `APIRouter` itself) rather than repeating
`dependencies=[Depends(require_roles(...))]` on every route - same
pattern as `app/api/routes/dashboard.py`, since every report shares the
same view permission (see `app/core/roles.py`'s own comment on why this
module doesn't split "financial" from "operational" reports).

Query params are named to match each report's own filters, not a generic
"filters" blob - `report_key` isn't even a path parameter here (unlike
what a single dynamic `/reports/{key}` endpoint might suggest) because
each report needs a genuinely different filter shape (a landlord_id here,
a days_ahead there, a period_start/period_end elsewhere) that a single
shared query-string contract would just be pretending to unify. The
"reusable pattern" lives in the shared `ReportResponse` shape every one of
these returns (see app/schemas/reports.py and app/services/report_service.py),
not in a single mega-route.

CSV export has no separate endpoint: the frontend calls the exact same
GET here (with whatever filters are currently applied) and turns the
response into a CSV client-side via utilities/csvExport.js - already the
established pattern from Rent Payments. This still satisfies "the backend
must apply filters and create export data" (Prompt 25) because the
exported rows are never anything other than what this endpoint just
returned; the frontend's part is pure formatting (JSON rows -> CSV text),
never re-filtering, re-sorting, or re-aggregating data itself.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.auth import require_roles
from app.api.dependencies.reports import get_report_service
from app.core.roles import CAN_VIEW_REPORTS
from app.schemas.reports import ReportResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_roles(*CAN_VIEW_REPORTS))])


@router.get("/rent-due-this-month", response_model=ReportResponse)
def rent_due_this_month(
    property_id: int | None = Query(None), service: ReportService = Depends(get_report_service)
) -> ReportResponse:
    return service.get_rent_due_this_month(property_id=property_id)


@router.get("/overdue-rent", response_model=ReportResponse)
def overdue_rent(
    property_id: int | None = Query(None),
    landlord_id: int | None = Query(None),
    service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    return service.get_overdue_rent(property_id=property_id, landlord_id=landlord_id)


@router.get("/monthly-rent-collected", response_model=ReportResponse)
def monthly_rent_collected(
    period_start: date | None = Query(None),
    period_end: date | None = Query(None),
    service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    return service.get_monthly_rent_collected(period_start=period_start, period_end=period_end)


@router.get("/rent-by-landlord", response_model=ReportResponse)
def rent_by_landlord(
    period_start: date | None = Query(None),
    period_end: date | None = Query(None),
    landlord_id: int | None = Query(None),
    service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    return service.get_rent_by_landlord(period_start=period_start, period_end=period_end, landlord_id=landlord_id)


@router.get("/occupancy", response_model=ReportResponse)
def occupancy(service: ReportService = Depends(get_report_service)) -> ReportResponse:
    return service.get_occupancy()


@router.get("/vacant-properties", response_model=ReportResponse)
def vacant_properties(
    landlord_id: int | None = Query(None), service: ReportService = Depends(get_report_service)
) -> ReportResponse:
    return service.get_vacant_properties(landlord_id=landlord_id)


@router.get("/tenancies-ending-soon", response_model=ReportResponse)
def tenancies_ending_soon(
    days_ahead: int = Query(30, ge=1, le=365, description="30, 60 or 90 are the typical windows"),
    property_id: int | None = Query(None),
    service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    return service.get_tenancies_ending_soon(days_ahead=days_ahead, property_id=property_id)


@router.get("/maintenance-by-status", response_model=ReportResponse)
def maintenance_by_status(service: ReportService = Depends(get_report_service)) -> ReportResponse:
    return service.get_maintenance_by_status()


@router.get("/maintenance-costs-by-property", response_model=ReportResponse)
def maintenance_costs_by_property(
    landlord_id: int | None = Query(None), service: ReportService = Depends(get_report_service)
) -> ReportResponse:
    return service.get_maintenance_costs_by_property(landlord_id=landlord_id)


@router.get("/property-income", response_model=ReportResponse)
def property_income(
    period_start: date | None = Query(None),
    period_end: date | None = Query(None),
    landlord_id: int | None = Query(None),
    service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    return service.get_property_income(period_start=period_start, period_end=period_end, landlord_id=landlord_id)
