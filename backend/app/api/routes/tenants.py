"""HTTP routes for the Tenant module.

Routes handle HTTP concerns only - see TenantService for business rules.
Same pattern as landlords.py/properties.py.

Permission model: same shape as Landlords/Properties - Administrator/
PropertyManager manage, ReadOnly views, MaintenanceEmployee has no access.

Deliberately NOT implemented yet: GET /api/tenants/{id}/tenancies and
/payment-history (scope doc, section 8) - each needs a response schema for
a module that doesn't exist yet (Tenancy, RentPayment). Same reasoning as
the deferred sub-resources on Landlords and Properties.
"""

from __future__ import annotations

from math import ceil

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.auth import require_roles
from app.api.dependencies.tenant import get_tenant_service
from app.core.roles import CAN_MANAGE_TENANTS, CAN_VIEW_TENANTS
from app.schemas.common import PaginatedResponse
from app.schemas.tenant import (
    TenantCreate,
    TenantListItem,
    TenantResponse,
    TenantStatusUpdate,
    TenantUpdate,
)
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get(
    "",
    response_model=PaginatedResponse[TenantListItem],
    dependencies=[Depends(require_roles(*CAN_VIEW_TENANTS))],
)
def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Matches name, email or phone"),
    is_active: bool | None = Query(None),
    service: TenantService = Depends(get_tenant_service),
) -> PaginatedResponse[TenantListItem]:
    items, total_items = service.list_tenants(page=page, page_size=page_size, search=search, is_active=is_active)
    total_pages = ceil(total_items / page_size) if total_items else 0
    return PaginatedResponse[TenantListItem](
        items=[TenantListItem.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    dependencies=[Depends(require_roles(*CAN_VIEW_TENANTS))],
)
def get_tenant(tenant_id: int, service: TenantService = Depends(get_tenant_service)) -> TenantResponse:
    tenant = service.get_tenant(tenant_id)
    return TenantResponse.model_validate(tenant)


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*CAN_MANAGE_TENANTS))],
)
def create_tenant(data: TenantCreate, service: TenantService = Depends(get_tenant_service)) -> TenantResponse:
    tenant = service.create_tenant(data)
    return TenantResponse.model_validate(tenant)


@router.put(
    "/{tenant_id}",
    response_model=TenantResponse,
    dependencies=[Depends(require_roles(*CAN_MANAGE_TENANTS))],
)
def update_tenant(
    tenant_id: int,
    data: TenantUpdate,
    service: TenantService = Depends(get_tenant_service),
) -> TenantResponse:
    tenant = service.update_tenant(tenant_id, data)
    return TenantResponse.model_validate(tenant)


@router.patch(
    "/{tenant_id}/status",
    response_model=TenantResponse,
    dependencies=[Depends(require_roles(*CAN_MANAGE_TENANTS))],
)
def set_tenant_status(
    tenant_id: int,
    data: TenantStatusUpdate,
    service: TenantService = Depends(get_tenant_service),
) -> TenantResponse:
    tenant = service.set_active_status(tenant_id, data.IsActive)
    return TenantResponse.model_validate(tenant)


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*CAN_MANAGE_TENANTS))],
)
def delete_tenant(tenant_id: int, service: TenantService = Depends(get_tenant_service)) -> None:
    service.deactivate_tenant(tenant_id)
