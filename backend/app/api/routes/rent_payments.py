"""HTTP routes for the RentPayment module.

Routes handle HTTP concerns only - see RentPaymentService for business
rules and the "why status is computed live" explanation.

Route order matters: /overdue and /due are declared BEFORE /{payment_id},
same reasoning as Tenancy's /expiring - see tenancies.py.

Permission model: same shape as every other module - Administrator/
PropertyManager manage, ReadOnly views, MaintenanceEmployee has no access.
"""

from __future__ import annotations

from datetime import date
from math import ceil

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.auth import require_roles
from app.api.dependencies.rent_payment import get_rent_payment_service
from app.core.roles import CAN_MANAGE_RENT_PAYMENTS, CAN_VIEW_RENT_PAYMENTS
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.rent_payment import (
    CancelPaymentRequest,
    PaymentStatusValue,
    RecordPaymentRequest,
    RentPaymentCreate,
    RentPaymentListItem,
    RentPaymentResponse,
    RentPaymentUpdate,
)
from app.services.rent_payment_service import RentPaymentService

router = APIRouter(prefix="/rent-payments", tags=["rent-payments"])


@router.get(
    "/overdue",
    response_model=list[RentPaymentListItem],
    dependencies=[Depends(require_roles(*CAN_VIEW_RENT_PAYMENTS))],
)
def list_overdue_payments(service: RentPaymentService = Depends(get_rent_payment_service)) -> list[RentPaymentListItem]:
    payments = service.list_overdue()
    return [RentPaymentListItem.from_payment(p, live_status=service.get_live_status(p)) for p in payments]


@router.get(
    "/due",
    response_model=list[RentPaymentListItem],
    dependencies=[Depends(require_roles(*CAN_VIEW_RENT_PAYMENTS))],
)
def list_payments_due_this_month(
    service: RentPaymentService = Depends(get_rent_payment_service),
) -> list[RentPaymentListItem]:
    payments = service.list_due_this_month()
    return [RentPaymentListItem.from_payment(p, live_status=service.get_live_status(p)) for p in payments]


@router.get(
    "",
    response_model=PaginatedResponse[RentPaymentListItem],
    dependencies=[Depends(require_roles(*CAN_VIEW_RENT_PAYMENTS))],
)
def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenancy_id: int | None = Query(None),
    property_id: int | None = Query(None),
    tenant_id: int | None = Query(None),
    payment_status: PaymentStatusValue | None = Query(
        None, description="Filters on last-known status - use /overdue for a guaranteed-live overdue list"
    ),
    due_date_from: date | None = Query(None),
    due_date_to: date | None = Query(None),
    service: RentPaymentService = Depends(get_rent_payment_service),
) -> PaginatedResponse[RentPaymentListItem]:
    items, total_items = service.list_payments(
        page=page,
        page_size=page_size,
        tenancy_id=tenancy_id,
        property_id=property_id,
        tenant_id=tenant_id,
        payment_status=payment_status,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
    )
    total_pages = ceil(total_items / page_size) if total_items else 0
    return PaginatedResponse[RentPaymentListItem](
        items=[RentPaymentListItem.from_payment(p, live_status=service.get_live_status(p)) for p in items],
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


@router.get(
    "/{payment_id}",
    response_model=RentPaymentResponse,
    dependencies=[Depends(require_roles(*CAN_VIEW_RENT_PAYMENTS))],
)
def get_payment(payment_id: int, service: RentPaymentService = Depends(get_rent_payment_service)) -> RentPaymentResponse:
    payment = service.get_payment(payment_id)
    return RentPaymentResponse.from_payment(payment, live_status=service.get_live_status(payment))


@router.post("", response_model=RentPaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    data: RentPaymentCreate,
    current_user: User = Depends(require_roles(*CAN_MANAGE_RENT_PAYMENTS)),
    service: RentPaymentService = Depends(get_rent_payment_service),
) -> RentPaymentResponse:
    payment = service.create_payment(data, created_by_employee_id=current_user.EmployeeId, user_id=current_user.UserId)
    return RentPaymentResponse.from_payment(payment, live_status=service.get_live_status(payment))


@router.put("/{payment_id}", response_model=RentPaymentResponse)
def update_payment(
    payment_id: int,
    data: RentPaymentUpdate,
    current_user: User = Depends(require_roles(*CAN_MANAGE_RENT_PAYMENTS)),
    service: RentPaymentService = Depends(get_rent_payment_service),
) -> RentPaymentResponse:
    payment = service.update_payment(payment_id, data, user_id=current_user.UserId)
    return RentPaymentResponse.from_payment(payment, live_status=service.get_live_status(payment))


@router.post("/{payment_id}/record-payment", response_model=RentPaymentResponse)
def record_payment(
    payment_id: int,
    data: RecordPaymentRequest,
    current_user: User = Depends(require_roles(*CAN_MANAGE_RENT_PAYMENTS)),
    service: RentPaymentService = Depends(get_rent_payment_service),
) -> RentPaymentResponse:
    payment = service.record_payment(
        payment_id,
        amount_paid=data.AmountPaid,
        payment_date=data.PaymentDate,
        payment_method=data.PaymentMethod,
        notes=data.Notes,
        user_id=current_user.UserId,
    )
    return RentPaymentResponse.from_payment(payment, live_status=service.get_live_status(payment))


@router.post("/{payment_id}/cancel", response_model=RentPaymentResponse)
def cancel_payment(
    payment_id: int,
    data: CancelPaymentRequest,
    current_user: User = Depends(require_roles(*CAN_MANAGE_RENT_PAYMENTS)),
    service: RentPaymentService = Depends(get_rent_payment_service),
) -> RentPaymentResponse:
    payment = service.cancel_payment(payment_id, notes=data.Notes, user_id=current_user.UserId)
    return RentPaymentResponse.from_payment(payment, live_status=service.get_live_status(payment))
