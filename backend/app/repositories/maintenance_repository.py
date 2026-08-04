"""Database access for the Maintenance module - no business rules here."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Literal, NamedTuple

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.maintenance_note import MaintenanceNote
from app.models.maintenance_request import MaintenanceRequest

# Statuses that mean "still open" - used both for the workload aggregation
# below and by MaintenanceService wherever "not finished yet" matters.
OPEN_STATUSES = ("Reported", "Assigned", "In Progress", "Waiting for Parts", "Waiting for Approval")

SortField = Literal["ReportedDate", "ScheduledDate", "RequestReference", "CreatedAt"]
SortDirection = Literal["asc", "desc"]

_SORT_COLUMNS = {
    "ReportedDate": MaintenanceRequest.ReportedDate,
    "ScheduledDate": MaintenanceRequest.ScheduledDate,
    "RequestReference": MaintenanceRequest.RequestReference,
    "CreatedAt": MaintenanceRequest.CreatedAt,
}


class WorkloadRow(NamedTuple):
    EmployeeId: int
    FirstName: str
    LastName: str
    IsActive: bool
    OpenRequestCount: int
    EmergencyOpenCount: int


class MaintenanceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, request_id: int) -> MaintenanceRequest | None:
        return self.db.get(MaintenanceRequest, request_id)

    def get_by_reference(self, reference: str) -> MaintenanceRequest | None:
        stmt = select(MaintenanceRequest).where(MaintenanceRequest.RequestReference == reference)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        property_id: int | None,
        tenant_id: int | None,
        assigned_employee_id: int | None,
        category: str | None,
        priority: str | None,
        maintenance_status: str | None,
        reported_date_from: date | None,
        reported_date_to: date | None,
        sort_by: SortField,
        sort_dir: SortDirection,
    ) -> tuple[Sequence[MaintenanceRequest], int]:
        stmt = select(MaintenanceRequest)
        conditions = []

        if property_id is not None:
            conditions.append(MaintenanceRequest.PropertyId == property_id)
        if tenant_id is not None:
            conditions.append(MaintenanceRequest.TenantId == tenant_id)
        if assigned_employee_id is not None:
            conditions.append(MaintenanceRequest.AssignedEmployeeId == assigned_employee_id)
        if category:
            conditions.append(MaintenanceRequest.Category == category)
        if priority:
            conditions.append(MaintenanceRequest.Priority == priority)
        if maintenance_status:
            conditions.append(MaintenanceRequest.MaintenanceStatus == maintenance_status)
        if reported_date_from is not None:
            conditions.append(MaintenanceRequest.ReportedDate >= reported_date_from)
        if reported_date_to is not None:
            conditions.append(MaintenanceRequest.ReportedDate <= reported_date_to)

        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(
                    MaintenanceRequest.RequestReference.ilike(pattern),
                    MaintenanceRequest.Title.ilike(pattern),
                    MaintenanceRequest.Description.ilike(pattern),
                )
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        total_items = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        sort_column = _SORT_COLUMNS[sort_by]
        order_clause = sort_column.desc() if sort_dir == "desc" else sort_column.asc()
        stmt = stmt.order_by(order_clause).offset((page - 1) * page_size).limit(page_size)

        items = self.db.execute(stmt).scalars().all()
        return items, total_items

    def list_workload(self) -> Sequence[WorkloadRow]:
        """One row per employee with at least one open assignment.
        Aggregated in SQL rather than loading every open request into
        Python, per the dashboard/reporting efficiency guidance in the
        scope doc (section 36 - the same "avoid loading unnecessary full
        records" principle applies here, not just to the dashboard
        endpoint itself).

        Selects individual Employee columns rather than the whole mapped
        entity: SQL Server's GROUP BY (unlike MySQL) requires every
        selected column to be aggregated or grouped-by - it won't infer
        that grouping by the primary key determines every other column -
        so selecting the full Employee object here would need it in the
        GROUP BY too, defeating the point of keeping the grouping key
        minimal.
        """
        emergency_count = func.sum(case((MaintenanceRequest.Priority == "Emergency", 1), else_=0))
        stmt = (
            select(
                Employee.EmployeeId,
                Employee.FirstName,
                Employee.LastName,
                Employee.IsActive,
                func.count(MaintenanceRequest.MaintenanceRequestId),
                emergency_count,
            )
            .join(MaintenanceRequest, MaintenanceRequest.AssignedEmployeeId == Employee.EmployeeId)
            .where(MaintenanceRequest.MaintenanceStatus.in_(OPEN_STATUSES))
            .group_by(Employee.EmployeeId, Employee.FirstName, Employee.LastName, Employee.IsActive)
            .order_by(func.count(MaintenanceRequest.MaintenanceRequestId).desc())
        )
        rows = self.db.execute(stmt).all()
        return [
            WorkloadRow(
                EmployeeId=employee_id,
                FirstName=first_name,
                LastName=last_name,
                IsActive=is_active,
                OpenRequestCount=open_count,
                EmergencyOpenCount=emergency_count,
            )
            for employee_id, first_name, last_name, is_active, open_count, emergency_count in rows
        ]

    def add(self, request: MaintenanceRequest) -> MaintenanceRequest:
        self.db.add(request)
        self.db.flush()  # assigns MaintenanceRequestId via IDENTITY without committing
        return request

    def add_note(self, note: MaintenanceNote) -> MaintenanceNote:
        self.db.add(note)
        self.db.flush()  # assigns MaintenanceNoteId via IDENTITY without committing
        return note
