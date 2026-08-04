"""HTTP routes for the Landlord module.

Routes handle HTTP concerns only: parse the request, call one method on
LandlordService, convert the result to a response schema. All business
rules live in LandlordService - see that file for the full request-flow
explanation and for what each of these calls actually does.

Note: none of these routes are permission-protected yet. Role-based access
control (Administrator / PropertyManager can manage landlords; ReadOnly can
only view) is added once authentication exists - see Prompt 10.
"""

from __future__ import annotations

from math import ceil

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.landlord import get_landlord_service
from app.schemas.common import PaginatedResponse
from app.schemas.landlord import (
    LandlordCreate,
    LandlordListItem,
    LandlordResponse,
    LandlordStatusUpdate,
    LandlordUpdate,
)
from app.services.landlord_service import LandlordService

router = APIRouter(prefix="/landlords", tags=["landlords"])


@router.get("", response_model=PaginatedResponse[LandlordListItem])
def list_landlords(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Matches name, company, email or phone"),
    is_active: bool | None = Query(None),
    service: LandlordService = Depends(get_landlord_service),
) -> PaginatedResponse[LandlordListItem]:
    items, total_items = service.list_landlords(page=page, page_size=page_size, search=search, is_active=is_active)
    total_pages = ceil(total_items / page_size) if total_items else 0
    return PaginatedResponse[LandlordListItem](
        items=[LandlordListItem.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


@router.get("/{landlord_id}", response_model=LandlordResponse)
def get_landlord(landlord_id: int, service: LandlordService = Depends(get_landlord_service)) -> LandlordResponse:
    landlord = service.get_landlord(landlord_id)
    return LandlordResponse.model_validate(landlord)


@router.post("", response_model=LandlordResponse, status_code=status.HTTP_201_CREATED)
def create_landlord(
    data: LandlordCreate, service: LandlordService = Depends(get_landlord_service)
) -> LandlordResponse:
    landlord = service.create_landlord(data)
    return LandlordResponse.model_validate(landlord)


@router.put("/{landlord_id}", response_model=LandlordResponse)
def update_landlord(
    landlord_id: int,
    data: LandlordUpdate,
    service: LandlordService = Depends(get_landlord_service),
) -> LandlordResponse:
    landlord = service.update_landlord(landlord_id, data)
    return LandlordResponse.model_validate(landlord)


@router.patch("/{landlord_id}/status", response_model=LandlordResponse)
def set_landlord_status(
    landlord_id: int,
    data: LandlordStatusUpdate,
    service: LandlordService = Depends(get_landlord_service),
) -> LandlordResponse:
    landlord = service.set_active_status(landlord_id, data.IsActive)
    return LandlordResponse.model_validate(landlord)


@router.delete("/{landlord_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_landlord(landlord_id: int, service: LandlordService = Depends(get_landlord_service)) -> None:
    service.deactivate_landlord(landlord_id)
