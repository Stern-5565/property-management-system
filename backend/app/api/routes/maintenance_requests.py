"""HTTP routes for the Maintenance module.

Routes handle HTTP concerns only - see MaintenanceService for business
rules and roles.py's comment block for why the permission shape differs
from every earlier module.

Route order matters: /workload is declared BEFORE /{request_id}, same
reasoning as RentPayment's /overdue and /due - see rent_payments.py.

List/get use CAN_ACCESS_MAINTENANCE (includes MaintenanceEmployee) and
pass current_user through as `viewer` so MaintenanceService can narrow
a MaintenanceEmployee's results to their own assigned requests - a plain
`dependencies=[Depends(require_roles(...))]` can gate the ROLE but can't
express "only their own rows", so those two routes need the user object
itself, not just the gate.
"""

from __future__ import annotations

from datetime import date
from math import ceil

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.auth import require_roles
from app.api.dependencies.maintenance import get_maintenance_service
from app.core.roles import CAN_ACCESS_MAINTENANCE, CAN_MANAGE_MAINTENANCE, CAN_UPDATE_MAINTENANCE_WORK, CAN_VIEW_MAINTENANCE
from app.models.user import User
from app.repositories.maintenance_repository import SortDirection, SortField
from app.schemas.maintenance import (
    AddNoteRequest,
    AssignEmployeeRequest,
    CancelRequest,
    CategoryValue,
    ChangePriorityRequest,
    ChangeStatusRequest,
    CompleteRequest,
    EmployeeWorkloadItem,
    EnterCostsRequest,
    MaintenanceRequestCreate,
    MaintenanceRequestListItem,
    MaintenanceRequestResponse,
    MaintenanceRequestUpdate,
    MaintenanceStatusValue,
    PriorityValue,
)
from app.schemas.common import PaginatedResponse
from app.services.maintenance_service import MaintenanceService

router = APIRouter(prefix="/maintenance-requests", tags=["maintenance-requests"])


@router.get(
    "/workload",
    response_model=list[EmployeeWorkloadItem],
    dependencies=[Depends(require_roles(*CAN_VIEW_MAINTENANCE))],
)
def get_employee_workload(service: MaintenanceService = Depends(get_maintenance_service)) -> list[EmployeeWorkloadItem]:
    rows = service.get_workload()
    return [
        EmployeeWorkloadItem(
            EmployeeId=row.EmployeeId,
            EmployeeName=f"{row.FirstName} {row.LastName}",
            IsActive=row.IsActive,
            OpenRequestCount=row.OpenRequestCount,
            EmergencyOpenCount=row.EmergencyOpenCount,
        )
        for row in rows
    ]


@router.get("", response_model=PaginatedResponse[MaintenanceRequestListItem])
def list_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    property_id: int | None = Query(None),
    tenant_id: int | None = Query(None),
    assigned_employee_id: int | None = Query(None),
    category: CategoryValue | None = Query(None),
    priority: PriorityValue | None = Query(None),
    maintenance_status: MaintenanceStatusValue | None = Query(None),
    reported_date_from: date | None = Query(None),
    reported_date_to: date | None = Query(None),
    sort_by: SortField = Query("ReportedDate"),
    sort_dir: SortDirection = Query("desc"),
    current_user: User = Depends(require_roles(*CAN_ACCESS_MAINTENANCE)),
    service: MaintenanceService = Depends(get_maintenance_service),
) -> PaginatedResponse[MaintenanceRequestListItem]:
    items, total_items = service.list_requests(
        page=page,
        page_size=page_size,
        search=search,
        property_id=property_id,
        tenant_id=tenant_id,
        assigned_employee_id=assigned_employee_id,
        category=category,
        priority=priority,
        maintenance_status=maintenance_status,
        reported_date_from=reported_date_from,
        reported_date_to=reported_date_to,
        sort_by=sort_by,
        sort_dir=sort_dir,
        viewer=current_user,
    )
    total_pages = ceil(total_items / page_size) if total_items else 0
    return PaginatedResponse[MaintenanceRequestListItem](
        items=[MaintenanceRequestListItem.from_request(r) for r in items],
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


@router.get("/{request_id}", response_model=MaintenanceRequestResponse)
def get_request(
    request_id: int,
    current_user: User = Depends(require_roles(*CAN_ACCESS_MAINTENANCE)),
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenanceRequestResponse:
    request = service.get_request(request_id, viewer=current_user)
    return MaintenanceRequestResponse.from_request(request)


@router.post("", response_model=MaintenanceRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    data: MaintenanceRequestCreate,
    current_user: User = Depends(require_roles(*CAN_MANAGE_MAINTENANCE)),
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenanceRequestResponse:
    request = service.create_request(data, user_id=current_user.UserId)
    return MaintenanceRequestResponse.from_request(request)


@router.put("/{request_id}", response_model=MaintenanceRequestResponse)
def update_request(
    request_id: int,
    data: MaintenanceRequestUpdate,
    current_user: User = Depends(require_roles(*CAN_MANAGE_MAINTENANCE)),
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenanceRequestResponse:
    request = service.update_request(request_id, data, user_id=current_user.UserId)
    return MaintenanceRequestResponse.from_request(request)


@router.post("/{request_id}/assign", response_model=MaintenanceRequestResponse)
def assign_employee(
    request_id: int,
    data: AssignEmployeeRequest,
    current_user: User = Depends(require_roles(*CAN_MANAGE_MAINTENANCE)),
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenanceRequestResponse:
    request = service.assign_employee(request_id, data.EmployeeId, user_id=current_user.UserId)
    return MaintenanceRequestResponse.from_request(request)


@router.post("/{request_id}/change-priority", response_model=MaintenanceRequestResponse)
def change_priority(
    request_id: int,
    data: ChangePriorityRequest,
    current_user: User = Depends(require_roles(*CAN_MANAGE_MAINTENANCE)),
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenanceRequestResponse:
    request = service.change_priority(request_id, data.Priority, user_id=current_user.UserId)
    return MaintenanceRequestResponse.from_request(request)


@router.post("/{request_id}/cancel", response_model=MaintenanceRequestResponse)
def cancel_request(
    request_id: int,
    data: CancelRequest,
    current_user: User = Depends(require_roles(*CAN_MANAGE_MAINTENANCE)),
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenanceRequestResponse:
    request = service.cancel_request(request_id, notes=data.Notes, user_id=current_user.UserId)
    return MaintenanceRequestResponse.from_request(request)


@router.post("/{request_id}/change-status", response_model=MaintenanceRequestResponse)
def change_status(
    request_id: int,
    data: ChangeStatusRequest,
    current_user: User = Depends(require_roles(*CAN_UPDATE_MAINTENANCE_WORK)),
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenanceRequestResponse:
    request = service.change_status(request_id, data.MaintenanceStatus, actor=current_user)
    return MaintenanceRequestResponse.from_request(request)


@router.post("/{request_id}/notes", response_model=MaintenanceRequestResponse)
def add_note(
    request_id: int,
    data: AddNoteRequest,
    current_user: User = Depends(require_roles(*CAN_UPDATE_MAINTENANCE_WORK)),
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenanceRequestResponse:
    request = service.add_note(request_id, data.NoteText, actor=current_user)
    return MaintenanceRequestResponse.from_request(request)


@router.post("/{request_id}/costs", response_model=MaintenanceRequestResponse)
def enter_costs(
    request_id: int,
    data: EnterCostsRequest,
    current_user: User = Depends(require_roles(*CAN_UPDATE_MAINTENANCE_WORK)),
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenanceRequestResponse:
    request = service.enter_costs(
        request_id, estimated_cost=data.EstimatedCost, actual_cost=data.ActualCost, actor=current_user
    )
    return MaintenanceRequestResponse.from_request(request)


@router.post("/{request_id}/complete", response_model=MaintenanceRequestResponse)
def complete_request(
    request_id: int,
    data: CompleteRequest,
    current_user: User = Depends(require_roles(*CAN_UPDATE_MAINTENANCE_WORK)),
    service: MaintenanceService = Depends(get_maintenance_service),
) -> MaintenanceRequestResponse:
    request = service.complete_request(
        request_id,
        completed_date=data.CompletedDate,
        resolution_notes=data.ResolutionNotes,
        actual_cost=data.ActualCost,
        actor=current_user,
    )
    return MaintenanceRequestResponse.from_request(request)
