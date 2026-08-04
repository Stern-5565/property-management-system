"""HTTP routes for the Property module.

Routes handle HTTP concerns only - see PropertyService for business rules
and the full request-flow explanation (landlords.py has the detailed
version; the pattern is identical here).

Permission model: same shape as Landlords - Administrator/PropertyManager
manage, ReadOnly views, MaintenanceEmployee has no access. See
app/core/roles.py.

Deliberately NOT implemented yet: GET /api/properties/{id}/tenancies,
/maintenance, and /payments (listed in the scope doc's section 8). Each
needs a response schema for a module that doesn't exist yet (Tenancy,
MaintenanceRequest, RentPayment respectively) - building those schemas here
would mean guessing at shapes those modules haven't defined for themselves
yet. They're added once each respective module exists, same reasoning as
deferring GET /api/landlords/{id}/properties until this module existed.
"""

from __future__ import annotations

from math import ceil

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.auth import require_roles
from app.api.dependencies.property import get_property_service
from app.core.roles import CAN_MANAGE_PROPERTIES, CAN_VIEW_PROPERTIES
from app.repositories.property_repository import SortDirection, SortField
from app.schemas.common import PaginatedResponse
from app.schemas.property import (
    PropertyCreate,
    PropertyListItem,
    PropertyResponse,
    PropertyStatusUpdate,
    PropertyStatusValue,
    PropertyTypeValue,
    PropertyUpdate,
)
from app.services.property_service import PropertyService

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get(
    "",
    response_model=PaginatedResponse[PropertyListItem],
    dependencies=[Depends(require_roles(*CAN_VIEW_PROPERTIES))],
)
def list_properties(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Matches reference or address"),
    landlord_id: int | None = Query(None),
    city: str | None = Query(None),
    property_type: PropertyTypeValue | None = Query(None),
    property_status: PropertyStatusValue | None = Query(None),
    is_active: bool | None = Query(None),
    sort_by: SortField = Query("PropertyReference"),
    sort_dir: SortDirection = Query("asc"),
    service: PropertyService = Depends(get_property_service),
) -> PaginatedResponse[PropertyListItem]:
    items, total_items = service.list_properties(
        page=page,
        page_size=page_size,
        search=search,
        landlord_id=landlord_id,
        city=city,
        property_type=property_type,
        property_status=property_status,
        is_active=is_active,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    total_pages = ceil(total_items / page_size) if total_items else 0
    return PaginatedResponse[PropertyListItem](
        items=[PropertyListItem.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


@router.get(
    "/{property_id}",
    response_model=PropertyResponse,
    dependencies=[Depends(require_roles(*CAN_VIEW_PROPERTIES))],
)
def get_property(property_id: int, service: PropertyService = Depends(get_property_service)) -> PropertyResponse:
    property_ = service.get_property(property_id)
    return PropertyResponse.model_validate(property_)


@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*CAN_MANAGE_PROPERTIES))],
)
def create_property(
    data: PropertyCreate, service: PropertyService = Depends(get_property_service)
) -> PropertyResponse:
    property_ = service.create_property(data)
    return PropertyResponse.model_validate(property_)


@router.put(
    "/{property_id}",
    response_model=PropertyResponse,
    dependencies=[Depends(require_roles(*CAN_MANAGE_PROPERTIES))],
)
def update_property(
    property_id: int,
    data: PropertyUpdate,
    service: PropertyService = Depends(get_property_service),
) -> PropertyResponse:
    property_ = service.update_property(property_id, data)
    return PropertyResponse.model_validate(property_)


@router.patch(
    "/{property_id}/status",
    response_model=PropertyResponse,
    dependencies=[Depends(require_roles(*CAN_MANAGE_PROPERTIES))],
)
def set_property_status(
    property_id: int,
    data: PropertyStatusUpdate,
    service: PropertyService = Depends(get_property_service),
) -> PropertyResponse:
    property_ = service.set_property_status(property_id, data.PropertyStatus)
    return PropertyResponse.model_validate(property_)


@router.delete(
    "/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*CAN_MANAGE_PROPERTIES))],
)
def delete_property(property_id: int, service: PropertyService = Depends(get_property_service)) -> None:
    service.deactivate_property(property_id)
