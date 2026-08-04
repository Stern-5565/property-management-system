"""Database access for the Employee module - no business rules here."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.maintenance_request import MaintenanceRequest
from app.repositories.maintenance_repository import OPEN_STATUSES


class EmployeeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, employee_id: int) -> Employee | None:
        return self.db.get(Employee, employee_id)

    def get_by_email(self, email: str) -> Employee | None:
        stmt = select(Employee).where(Employee.Email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        is_active: bool | None,
    ) -> tuple[Sequence[Employee], int]:
        stmt = select(Employee)
        conditions = []

        if is_active is not None:
            conditions.append(Employee.IsActive == is_active)  # noqa: E712 - see landlord_repository.py

        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(
                    Employee.FirstName.ilike(pattern),
                    Employee.LastName.ilike(pattern),
                    Employee.Email.ilike(pattern),
                    Employee.Phone.ilike(pattern),
                    Employee.JobTitle.ilike(pattern),
                    Employee.Department.ilike(pattern),
                )
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        stmt = stmt.order_by(Employee.LastName, Employee.FirstName).offset((page - 1) * page_size).limit(page_size)
        items = self.db.execute(stmt).scalars().all()
        return items, total_items

    def has_open_maintenance_assignments(self, employee_id: int) -> bool:
        """Backs the "an employee assigned to open maintenance requests
        should normally be reassigned before deactivation" rule (scope doc
        section 5.7). Reuses MaintenanceRepository.OPEN_STATUSES as the
        single source of truth for what "open" means, rather than
        redefining the status list here."""
        stmt = (
            select(func.count())
            .select_from(MaintenanceRequest)
            .where(
                MaintenanceRequest.AssignedEmployeeId == employee_id,
                MaintenanceRequest.MaintenanceStatus.in_(OPEN_STATUSES),
            )
        )
        return self.db.execute(stmt).scalar_one() > 0

    def add(self, employee: Employee) -> Employee:
        self.db.add(employee)
        self.db.flush()  # assigns EmployeeId via IDENTITY without committing
        return employee
