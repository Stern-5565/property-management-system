"""Business rules for the Maintenance module.

Permission shape, and why it's more involved than every previous module:

MaintenanceEmployee is the one role (besides Administrator/PropertyManager)
with real write access here (see documentation/project-scope.md section 4),
but only to requests currently assigned to them, and only for a specific
subset of actions (status, notes, costs, completion) - never create/edit/
assign/change-priority/cancel, which stay Administrator/PropertyManager
only. app/core/roles.py's CAN_UPDATE_MAINTENANCE_WORK tuple gets a
MaintenanceEmployee past the route's role check, but the "is this actually
YOUR assigned request" check only happens here, in
_assert_can_update_work - a route-level role check alone can't express
"this role, but only for their own rows".

Terminal states (Completed, Cancelled) are, same as RentPayment/Tenancy,
a one-way door: once a request reaches either one, no further edits/
status changes/reassignment are accepted - only cost corrections remain
possible (see enter_costs).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.roles import ADMINISTRATOR, MAINTENANCE_EMPLOYEE, PROPERTY_MANAGER, READ_ONLY
from app.models.maintenance_note import MaintenanceNote
from app.models.maintenance_request import MaintenanceRequest
from app.models.user import User
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.maintenance_repository import MaintenanceRepository
from app.repositories.property_repository import PropertyRepository
from app.repositories.tenancy_repository import TenancyRepository
from app.repositories.tenant_repository import TenantRepository
from app.schemas.maintenance import MaintenanceRequestCreate, MaintenanceRequestUpdate
from app.services.audit_service import AuditService
from app.utilities.datetime_utils import utc_now

_TERMINAL_STATUSES = ("Completed", "Cancelled")
_FULL_ACCESS_ROLES = frozenset({ADMINISTRATOR, PROPERTY_MANAGER})


class MaintenanceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = MaintenanceRepository(db)
        self.property_repository = PropertyRepository(db)
        self.tenancy_repository = TenancyRepository(db)
        self.tenant_repository = TenantRepository(db)
        self.employee_repository = EmployeeRepository(db)
        self.audit_service = AuditService(db)

    # ---------- Read ----------

    def list_requests(
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
        sort_by,
        sort_dir,
        viewer: User,
    ):
        if self._is_restricted_to_own_work(viewer):
            # MaintenanceEmployee: "View maintenance requests assigned to
            # them" - whatever filter they asked for, it's narrowed to
            # their own EmployeeId, never widened.
            assigned_employee_id = viewer.EmployeeId

        return self.repository.list(
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
        )

    def get_request(self, request_id: int, *, viewer: User) -> MaintenanceRequest:
        request = self._get_or_404(request_id)
        if self._is_restricted_to_own_work(viewer) and request.AssignedEmployeeId != viewer.EmployeeId:
            raise AppError(
                "MAINTENANCE_NOT_ASSIGNED_TO_YOU", "You are not assigned to this maintenance request.", status_code=403
            )
        return request

    def get_workload(self):
        return self.repository.list_workload()

    # ---------- Management actions (Administrator/PropertyManager only - enforced by the route) ----------

    def create_request(self, data: MaintenanceRequestCreate, *, user_id: int) -> MaintenanceRequest:
        self._ensure_property_exists(data.PropertyId)
        self._ensure_tenancy_exists_if_given(data.TenancyId)
        self._ensure_tenant_exists_if_given(data.TenantId)
        self._ensure_reference_not_taken(data.RequestReference, exclude_request_id=None)

        request = MaintenanceRequest(**data.model_dump(), MaintenanceStatus="Reported")
        self.repository.add(request)

        self.audit_service.log(
            user_id=user_id,
            action="CREATE",
            entity_name="MaintenanceRequest",
            entity_id=request.MaintenanceRequestId,
            new_values={"PropertyId": request.PropertyId, "Title": request.Title, "Priority": request.Priority},
        )

        self.db.commit()
        self.db.refresh(request)
        return request

    def update_request(self, request_id: int, data: MaintenanceRequestUpdate, *, user_id: int) -> MaintenanceRequest:
        request = self._get_or_404(request_id)
        self._assert_not_terminal(request)

        self._ensure_property_exists(data.PropertyId)
        self._ensure_tenancy_exists_if_given(data.TenancyId)
        self._ensure_tenant_exists_if_given(data.TenantId)
        self._ensure_reference_not_taken(data.RequestReference, exclude_request_id=request_id)

        old_values = {"Title": request.Title, "Priority": request.Priority, "Category": request.Category}
        for field, value in data.model_dump().items():
            setattr(request, field, value)
        request.UpdatedAt = utc_now()

        self.audit_service.log(
            user_id=user_id,
            action="UPDATE",
            entity_name="MaintenanceRequest",
            entity_id=request.MaintenanceRequestId,
            old_values=old_values,
            new_values={"Title": request.Title, "Priority": request.Priority, "Category": request.Category},
        )

        self.db.commit()
        self.db.refresh(request)
        return request

    def assign_employee(self, request_id: int, employee_id: int, *, user_id: int) -> MaintenanceRequest:
        request = self._get_or_404(request_id)
        self._assert_not_terminal(request)

        employee = self.employee_repository.get_by_id(employee_id)
        if employee is None:
            raise AppError("EMPLOYEE_NOT_FOUND", f"No employee found with id {employee_id}.", status_code=404)
        if not employee.IsActive:
            raise AppError(
                "EMPLOYEE_INACTIVE", "Inactive employees cannot receive new maintenance assignments.", status_code=409
            )

        old_employee_id = request.AssignedEmployeeId
        request.AssignedEmployeeId = employee_id
        if request.MaintenanceStatus == "Reported":
            request.MaintenanceStatus = "Assigned"
        request.UpdatedAt = utc_now()

        self.audit_service.log(
            user_id=user_id,
            action="ASSIGN",
            entity_name="MaintenanceRequest",
            entity_id=request.MaintenanceRequestId,
            old_values={"AssignedEmployeeId": old_employee_id},
            new_values={"AssignedEmployeeId": employee_id},
        )

        self.db.commit()
        self.db.refresh(request)
        return request

    def change_priority(self, request_id: int, priority: str, *, user_id: int) -> MaintenanceRequest:
        request = self._get_or_404(request_id)
        self._assert_not_terminal(request)

        old_priority = request.Priority
        request.Priority = priority
        request.UpdatedAt = utc_now()

        self.audit_service.log(
            user_id=user_id,
            action="CHANGE_PRIORITY",
            entity_name="MaintenanceRequest",
            entity_id=request.MaintenanceRequestId,
            old_values={"Priority": old_priority},
            new_values={"Priority": priority},
        )

        self.db.commit()
        self.db.refresh(request)
        return request

    def cancel_request(self, request_id: int, *, notes: str | None, user_id: int) -> MaintenanceRequest:
        request = self._get_or_404(request_id)
        if request.MaintenanceStatus == "Completed":
            raise AppError("MAINTENANCE_ALREADY_COMPLETED", "A completed request cannot be cancelled.", status_code=409)
        if request.MaintenanceStatus == "Cancelled":
            raise AppError("MAINTENANCE_ALREADY_CANCELLED", "This request has already been cancelled.", status_code=409)

        old_status = request.MaintenanceStatus
        request.MaintenanceStatus = "Cancelled"
        if notes:
            request.ResolutionNotes = notes
        request.UpdatedAt = utc_now()

        self.audit_service.log(
            user_id=user_id,
            action="CANCEL",
            entity_name="MaintenanceRequest",
            entity_id=request.MaintenanceRequestId,
            old_values={"MaintenanceStatus": old_status},
            new_values={"MaintenanceStatus": "Cancelled"},
        )

        self.db.commit()
        self.db.refresh(request)
        return request

    # ---------- Hands-on-the-job actions (Administrator/PropertyManager, or the assigned MaintenanceEmployee) ----------

    def change_status(self, request_id: int, new_status: str, *, actor: User) -> MaintenanceRequest:
        request = self._get_or_404(request_id)
        self._assert_can_update_work(request, actor)
        self._assert_not_terminal(request)

        old_status = request.MaintenanceStatus
        request.MaintenanceStatus = new_status
        request.UpdatedAt = utc_now()

        self.audit_service.log(
            user_id=actor.UserId,
            action="CHANGE_STATUS",
            entity_name="MaintenanceRequest",
            entity_id=request.MaintenanceRequestId,
            old_values={"MaintenanceStatus": old_status},
            new_values={"MaintenanceStatus": new_status},
        )

        self.db.commit()
        self.db.refresh(request)
        return request

    def add_note(self, request_id: int, note_text: str, *, actor: User) -> MaintenanceRequest:
        request = self._get_or_404(request_id)
        self._assert_can_update_work(request, actor)

        note = MaintenanceNote(MaintenanceRequestId=request_id, EmployeeId=actor.EmployeeId, NoteText=note_text)
        self.repository.add_note(note)

        self.audit_service.log(
            user_id=actor.UserId,
            action="ADD_NOTE",
            entity_name="MaintenanceRequest",
            entity_id=request.MaintenanceRequestId,
            new_values={"NoteText": note_text},
        )

        self.db.commit()
        self.db.refresh(request)
        return request

    def enter_costs(
        self, request_id: int, *, estimated_cost, actual_cost, actor: User
    ) -> MaintenanceRequest:
        request = self._get_or_404(request_id)
        self._assert_can_update_work(request, actor)
        if request.MaintenanceStatus == "Cancelled":
            raise AppError("MAINTENANCE_ALREADY_CANCELLED", "Cannot record costs on a cancelled request.", status_code=409)

        old_values = {"EstimatedCost": request.EstimatedCost, "ActualCost": request.ActualCost}
        if estimated_cost is not None:
            request.EstimatedCost = estimated_cost
        if actual_cost is not None:
            request.ActualCost = actual_cost
        request.UpdatedAt = utc_now()

        self.audit_service.log(
            user_id=actor.UserId,
            action="ENTER_COSTS",
            entity_name="MaintenanceRequest",
            entity_id=request.MaintenanceRequestId,
            old_values=old_values,
            new_values={"EstimatedCost": request.EstimatedCost, "ActualCost": request.ActualCost},
        )

        self.db.commit()
        self.db.refresh(request)
        return request

    def complete_request(
        self,
        request_id: int,
        *,
        completed_date: date | None,
        resolution_notes: str,
        actual_cost,
        actor: User,
    ) -> MaintenanceRequest:
        request = self._get_or_404(request_id)
        self._assert_can_update_work(request, actor)
        if request.MaintenanceStatus == "Completed":
            raise AppError("MAINTENANCE_ALREADY_COMPLETED", "This request has already been completed.", status_code=409)
        if request.MaintenanceStatus == "Cancelled":
            raise AppError("MAINTENANCE_ALREADY_CANCELLED", "A cancelled request cannot be completed.", status_code=409)

        resolved_completed_date = completed_date or date.today()
        if resolved_completed_date < request.ReportedDate:
            raise AppError(
                "MAINTENANCE_INVALID_COMPLETION_DATE",
                "Completion date cannot be earlier than the date the request was reported.",
                status_code=409,
            )

        old_status = request.MaintenanceStatus
        request.MaintenanceStatus = "Completed"
        request.CompletedDate = resolved_completed_date
        request.ResolutionNotes = resolution_notes
        if actual_cost is not None:
            request.ActualCost = actual_cost
        request.UpdatedAt = utc_now()

        self.audit_service.log(
            user_id=actor.UserId,
            action="COMPLETE",
            entity_name="MaintenanceRequest",
            entity_id=request.MaintenanceRequestId,
            old_values={"MaintenanceStatus": old_status},
            new_values={"MaintenanceStatus": "Completed", "CompletedDate": resolved_completed_date},
        )

        self.db.commit()
        self.db.refresh(request)
        return request

    # ---------- Internal helpers ----------

    def _get_or_404(self, request_id: int) -> MaintenanceRequest:
        request = self.repository.get_by_id(request_id)
        if request is None:
            raise AppError(
                "MAINTENANCE_REQUEST_NOT_FOUND", f"No maintenance request found with id {request_id}.", status_code=404
            )
        return request

    def _assert_not_terminal(self, request: MaintenanceRequest) -> None:
        if request.MaintenanceStatus in _TERMINAL_STATUSES:
            raise AppError(
                "MAINTENANCE_REQUEST_CLOSED",
                f"This request is {request.MaintenanceStatus.lower()} and can no longer be modified this way.",
                status_code=409,
            )

    def _is_restricted_to_own_work(self, user: User) -> bool:
        role_names = {role.RoleName for role in user.Roles}
        if role_names & (_FULL_ACCESS_ROLES | {READ_ONLY}):
            return False
        return MAINTENANCE_EMPLOYEE in role_names

    def _assert_can_update_work(self, request: MaintenanceRequest, actor: User) -> None:
        role_names = {role.RoleName for role in actor.Roles}
        if role_names & _FULL_ACCESS_ROLES:
            return
        if MAINTENANCE_EMPLOYEE in role_names and request.AssignedEmployeeId == actor.EmployeeId:
            return
        raise AppError(
            "MAINTENANCE_NOT_ASSIGNED_TO_YOU", "You are not assigned to this maintenance request.", status_code=403
        )

    def _ensure_property_exists(self, property_id: int) -> None:
        if self.property_repository.get_by_id(property_id) is None:
            raise AppError("PROPERTY_NOT_FOUND", f"No property found with id {property_id}.", status_code=404)

    def _ensure_tenancy_exists_if_given(self, tenancy_id: int | None) -> None:
        if tenancy_id is not None and self.tenancy_repository.get_by_id(tenancy_id) is None:
            raise AppError("TENANCY_NOT_FOUND", f"No tenancy found with id {tenancy_id}.", status_code=404)

    def _ensure_tenant_exists_if_given(self, tenant_id: int | None) -> None:
        if tenant_id is not None and self.tenant_repository.get_by_id(tenant_id) is None:
            raise AppError("TENANT_NOT_FOUND", f"No tenant found with id {tenant_id}.", status_code=404)

    def _ensure_reference_not_taken(self, reference: str, *, exclude_request_id: int | None) -> None:
        existing = self.repository.get_by_reference(reference)
        if existing is not None and existing.MaintenanceRequestId != exclude_request_id:
            raise AppError(
                "DUPLICATE_REQUEST_REFERENCE",
                f"A maintenance request with reference '{reference}' already exists.",
                status_code=409,
            )
