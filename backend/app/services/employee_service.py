"""Business rules for the Employee module. Same shape as LandlordService -
see that file for the full request-flow explanation.

Deactivation cascades to the linked User account (if one exists):
deactivating an Employee also sets their User.IsActive = False, so
"Inactive employees cannot log in" (scope doc section 5.7) actually holds
- login (app/api/dependencies/auth.py::get_current_user) checks
User.IsActive, not Employee.IsActive, and those are two different rows.
This is deliberately ONE-WAY: reactivating an Employee does NOT
automatically restore their User account's access. Account access is a
more sensitive action that the scope doc gives to Administrator as its
own separate capability ("Create and deactivate user accounts", distinct
from "Manage employees") - a full Users admin module isn't built yet (see
documentation/progress-log.md), so auto-restoring login on employee
reactivation would grant access through a side door that bypasses that
still-to-be-built, more deliberate control.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.employee import Employee
from app.models.user import User
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.utilities.datetime_utils import utc_now


class EmployeeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = EmployeeRepository(db)

    def list_employees(
        self, *, page: int, page_size: int, search: str | None, is_active: bool | None
    ) -> tuple[Sequence[Employee], int]:
        return self.repository.list(page=page, page_size=page_size, search=search, is_active=is_active)

    def get_employee(self, employee_id: int) -> Employee:
        employee = self.repository.get_by_id(employee_id)
        if employee is None:
            raise AppError("EMPLOYEE_NOT_FOUND", f"No employee found with id {employee_id}.", status_code=404)
        return employee

    def create_employee(self, data: EmployeeCreate) -> Employee:
        self._ensure_email_not_taken(data.Email, exclude_employee_id=None)

        employee = Employee(**data.model_dump(), IsActive=True)
        self.repository.add(employee)
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def update_employee(self, employee_id: int, data: EmployeeUpdate) -> Employee:
        employee = self.get_employee(employee_id)
        self._ensure_email_not_taken(data.Email, exclude_employee_id=employee_id)

        for field, value in data.model_dump().items():
            setattr(employee, field, value)
        employee.UpdatedAt = utc_now()

        self.db.commit()
        self.db.refresh(employee)
        return employee

    def set_active_status(self, employee_id: int, is_active: bool) -> Employee:
        employee = self.get_employee(employee_id)

        if not is_active:
            if self.repository.has_open_maintenance_assignments(employee_id):
                raise AppError(
                    "EMPLOYEE_HAS_OPEN_MAINTENANCE_ASSIGNMENTS",
                    "This employee has open maintenance requests assigned to them and cannot be deactivated. "
                    "Reassign those requests first.",
                    status_code=409,
                )
            self._deactivate_linked_user(employee_id)

        employee.IsActive = is_active
        employee.UpdatedAt = utc_now()

        self.db.commit()
        self.db.refresh(employee)
        return employee

    def deactivate_employee(self, employee_id: int) -> Employee:
        """Handles DELETE /api/employees/{id}. Same soft-delete-only
        philosophy as LandlordService.deactivate_landlord - never a real
        SQL DELETE, since Employees is referenced from Users, RentPayments,
        MaintenanceRequests and MaintenanceNotes."""
        return self.set_active_status(employee_id, False)

    def _deactivate_linked_user(self, employee_id: int) -> None:
        user = self.db.execute(select(User).where(User.EmployeeId == employee_id)).scalar_one_or_none()
        if user is not None and user.IsActive:
            user.IsActive = False
            user.UpdatedAt = utc_now()

    def _ensure_email_not_taken(self, email: str, *, exclude_employee_id: int | None) -> None:
        existing = self.repository.get_by_email(email)
        if existing is not None and existing.EmployeeId != exclude_employee_id:
            raise AppError(
                "DUPLICATE_EMAIL",
                f"An employee with the email '{email}' already exists.",
                status_code=409,
            )
