"""HTTP routes for the Tenancy module.

Routes handle HTTP concerns only - see TenancyService for business rules
and the transaction-handling explanation.

Route order matters here: /expiring is declared BEFORE /{tenancy_id}.
FastAPI/Starlette matches routes in declaration order, and a literal path
like /expiring must be checked before a parameterized one like
/{tenancy_id} or (depending on the path converter) it could be swallowed
by the parameterized route instead of reaching this one.

Unlike the other modules' routes, several of these use
`current_user: User = Depends(require_roles(...))` as an actual parameter,
not just a bare `dependencies=[...]` entry - the route needs the
authenticated user's ID to pass through to the service for audit logging,
not just the permission check itself.

Permission model: same shape as Landlords/Properties/Tenants -
Administrator/PropertyManager manage, ReadOnly views, MaintenanceEmployee
has no access.
"""

from __future__ import annotations

from math import ceil

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.auth import require_roles
from app.api.dependencies.tenancy import get_tenancy_service
from app.core.roles import CAN_MANAGE_TENANCIES, CAN_VIEW_TENANCIES
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.tenancy import (
    TenancyCreate,
    TenancyEndRequest,
    TenancyListItem,
    TenancyResponse,
    TenancyStatusValue,
    TenancyUpdate,
)
from app.services.tenancy_service import TenancyService

router = APIRouter(prefix="/tenancies", tags=["tenancies"])


@router.get(
    "/expiring",
    response_model=list[TenancyListItem],
    dependencies=[Depends(require_roles(*CAN_VIEW_TENANCIES))],
)
def list_expiring_tenancies(
    days: int = Query(30, ge=1, le=365, description="30, 60 or 90 are the typical windows"),
    service: TenancyService = Depends(get_tenancy_service),
) -> list[TenancyListItem]:
    tenancies = service.list_expiring(days=days)
    return [TenancyListItem.from_tenancy(t) for t in tenancies]


@router.get(
    "",
    response_model=PaginatedResponse[TenancyListItem],
    dependencies=[Depends(require_roles(*CAN_VIEW_TENANCIES))],
)
def list_tenancies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    property_id: int | None = Query(None),
    tenant_id: int | None = Query(None),
    tenancy_status: TenancyStatusValue | None = Query(None),
    service: TenancyService = Depends(get_tenancy_service),
) -> PaginatedResponse[TenancyListItem]:
    items, total_items = service.list_tenancies(
        page=page, page_size=page_size, property_id=property_id, tenant_id=tenant_id, tenancy_status=tenancy_status
    )
    total_pages = ceil(total_items / page_size) if total_items else 0
    return PaginatedResponse[TenancyListItem](
        items=[TenancyListItem.from_tenancy(t) for t in items],
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


@router.get(
    "/{tenancy_id}",
    response_model=TenancyResponse,
    dependencies=[Depends(require_roles(*CAN_VIEW_TENANCIES))],
)
def get_tenancy(tenancy_id: int, service: TenancyService = Depends(get_tenancy_service)) -> TenancyResponse:
    tenancy = service.get_tenancy(tenancy_id)
    return TenancyResponse.from_tenancy(tenancy)


@router.post("", response_model=TenancyResponse, status_code=status.HTTP_201_CREATED)
def create_tenancy(
    data: TenancyCreate,
    current_user: User = Depends(require_roles(*CAN_MANAGE_TENANCIES)),
    service: TenancyService = Depends(get_tenancy_service),
) -> TenancyResponse:
    tenancy = service.create_draft_tenancy(data, user_id=current_user.UserId)
    return TenancyResponse.from_tenancy(tenancy)


@router.put("/{tenancy_id}", response_model=TenancyResponse)
def update_tenancy(
    tenancy_id: int,
    data: TenancyUpdate,
    current_user: User = Depends(require_roles(*CAN_MANAGE_TENANCIES)),
    service: TenancyService = Depends(get_tenancy_service),
) -> TenancyResponse:
    tenancy = service.update_tenancy(tenancy_id, data, user_id=current_user.UserId)
    return TenancyResponse.from_tenancy(tenancy)


@router.post("/{tenancy_id}/activate", response_model=TenancyResponse)
def activate_tenancy(
    tenancy_id: int,
    current_user: User = Depends(require_roles(*CAN_MANAGE_TENANCIES)),
    service: TenancyService = Depends(get_tenancy_service),
) -> TenancyResponse:
    tenancy = service.activate_tenancy(tenancy_id, user_id=current_user.UserId)
    return TenancyResponse.from_tenancy(tenancy)


@router.post("/{tenancy_id}/end", response_model=TenancyResponse)
def end_tenancy(
    tenancy_id: int,
    data: TenancyEndRequest,
    current_user: User = Depends(require_roles(*CAN_MANAGE_TENANCIES)),
    service: TenancyService = Depends(get_tenancy_service),
) -> TenancyResponse:
    tenancy = service.end_tenancy(tenancy_id, end_date=data.EndDate, user_id=current_user.UserId)
    return TenancyResponse.from_tenancy(tenancy)


@router.post("/{tenancy_id}/cancel", response_model=TenancyResponse)
def cancel_tenancy(
    tenancy_id: int,
    current_user: User = Depends(require_roles(*CAN_MANAGE_TENANCIES)),
    service: TenancyService = Depends(get_tenancy_service),
) -> TenancyResponse:
    tenancy = service.cancel_tenancy(tenancy_id, user_id=current_user.UserId)
    return TenancyResponse.from_tenancy(tenancy)
