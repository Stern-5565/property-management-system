"""Database access for the Employee module.

Deliberately minimal: the full Employee module (list/create/edit/
activate-deactivate) is a separate, not-yet-built piece of work (see
documentation/progress-log.md's "Next steps"). This repository exists
only so MaintenanceService can look up an employee by id to validate an
assignment, following the same repository pattern as every other module
rather than querying the Employee model directly from service code.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.employee import Employee


class EmployeeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, employee_id: int) -> Employee | None:
        return self.db.get(Employee, employee_id)
