"""HTTP routes for the Employee module.

Routes handle HTTP concerns only - see EmployeeService for business rules.

Permission model (documentation/project-scope.md, section 4): only
Administrator can manage employees (create/edit/deactivate); Administrator
and PropertyManager can both view them (PropertyManager needs this to pick
an employee when assigning maintenance work); ReadOnly and
MaintenanceEmployee have no access - see app/core/roles.py's comment block
for the full reasoning.
"""

from __future__ import annotations

from math import ceil

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.auth import require_roles
from app.api.dependencies.employee import get_employee_service
from app.core.roles import CAN_MANAGE_EMPLOYEES, CAN_VIEW_EMPLOYEES
from app.schemas.common import PaginatedResponse
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeListItem,
    EmployeeResponse,
    EmployeeStatusUpdate,
    EmployeeUpdate,
)
from app.services.employee_service import EmployeeService

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get(
    "",
    response_model=PaginatedResponse[EmployeeListItem],
    dependencies=[Depends(require_roles(*CAN_VIEW_EMPLOYEES))],
)
def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Matches name, email, phone, job title or department"),
    is_active: bool | None = Query(None),
    service: EmployeeService = Depends(get_employee_service),
) -> PaginatedResponse[EmployeeListItem]:
    items, total_items = service.list_employees(page=page, page_size=page_size, search=search, is_active=is_active)
    total_pages = ceil(total_items / page_size) if total_items else 0
    return PaginatedResponse[EmployeeListItem](
        items=[EmployeeListItem.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
    dependencies=[Depends(require_roles(*CAN_VIEW_EMPLOYEES))],
)
def get_employee(employee_id: int, service: EmployeeService = Depends(get_employee_service)) -> EmployeeResponse:
    employee = service.get_employee(employee_id)
    return EmployeeResponse.model_validate(employee)


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*CAN_MANAGE_EMPLOYEES))],
)
def create_employee(data: EmployeeCreate, service: EmployeeService = Depends(get_employee_service)) -> EmployeeResponse:
    employee = service.create_employee(data)
    return EmployeeResponse.model_validate(employee)


@router.put(
    "/{employee_id}",
    response_model=EmployeeResponse,
    dependencies=[Depends(require_roles(*CAN_MANAGE_EMPLOYEES))],
)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    employee = service.update_employee(employee_id, data)
    return EmployeeResponse.model_validate(employee)


@router.patch(
    "/{employee_id}/status",
    response_model=EmployeeResponse,
    dependencies=[Depends(require_roles(*CAN_MANAGE_EMPLOYEES))],
)
def set_employee_status(
    employee_id: int,
    data: EmployeeStatusUpdate,
    service: EmployeeService = Depends(get_employee_service),
) -> EmployeeResponse:
    employee = service.set_active_status(employee_id, data.IsActive)
    return EmployeeResponse.model_validate(employee)


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*CAN_MANAGE_EMPLOYEES))],
)
def delete_employee(employee_id: int, service: EmployeeService = Depends(get_employee_service)) -> None:
    service.deactivate_employee(employee_id)
