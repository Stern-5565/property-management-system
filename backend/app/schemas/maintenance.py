"""Pydantic schemas for the Maintenance module.

Unlike RentPayment/Tenancy (one lifecycle, a handful of transitions),
Maintenance has several independent axes that change separately -
priority, assignment, status, cost, notes - so each gets its own small
action schema rather than one big "update anything" PUT. This also lets
permissions differ per action: MaintenanceEmployee can change status/
enter costs/add notes/complete but not assign an employee, edit the
request itself, change priority, or cancel it - see
MaintenanceService for the enforcement, app/core/roles.py for the role
groups.

MaintenanceStatus is deliberately NOT settable to "Completed" or
"Cancelled" via ChangeStatusRequest - those go through the dedicated
/complete and /cancel actions instead, which enforce their own required
fields (CompletedDate + ResolutionNotes for Completed - see the
CK_MaintenanceRequests_CompletionRequiresDetail DB constraint). Same
reasoning as RentPayment not exposing a generic status PATCH.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import PaginatedResponse

CategoryValue = Literal["Plumbing", "Electrical", "Heating", "Appliance", "Structural", "Security", "Cleaning", "General", "Other"]
PriorityValue = Literal["Low", "Medium", "High", "Emergency"]
MaintenanceStatusValue = Literal[
    "Reported", "Assigned", "In Progress", "Waiting for Parts", "Waiting for Approval", "Completed", "Cancelled"
]
# Subset ChangeStatusRequest accepts - Completed/Cancelled are excluded on
# purpose, see module docstring.
ChangeableStatusValue = Literal["Reported", "Assigned", "In Progress", "Waiting for Parts", "Waiting for Approval"]


class MaintenanceRequestCreate(BaseModel):
    """Request body for POST /api/maintenance-requests. MaintenanceStatus
    always starts as "Reported", ReportedDate defaults server-side, and
    AssignedEmployeeId/costs/completion fields are never client-settable
    here - each has its own dedicated action endpoint."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    PropertyId: int
    TenancyId: int | None = None
    TenantId: int | None = None
    RequestReference: str = Field(min_length=1, max_length=30)
    Title: str = Field(min_length=1, max_length=150)
    Description: str | None = Field(default=None, max_length=2000)
    Category: CategoryValue
    Priority: PriorityValue
    ScheduledDate: date | None = None


class MaintenanceRequestUpdate(MaintenanceRequestCreate):
    """Request body for PUT /api/maintenance-requests/{id} - the "edit
    request" action, Administrator/PropertyManager only. Editing the
    property/tenancy/tenant/reference/title/description/category/priority/
    schedule is a management decision, distinct from the hands-on-the-job
    actions (status, notes, costs, completion) available to the assigned
    MaintenanceEmployee too."""


class AssignEmployeeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    EmployeeId: int


class ChangePriorityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    Priority: PriorityValue


class ChangeStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    MaintenanceStatus: ChangeableStatusValue


class AddNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    NoteText: str = Field(min_length=1, max_length=2000)


class EnterCostsRequest(BaseModel):
    """At least one of EstimatedCost/ActualCost must be given - an empty
    request wouldn't change anything and is more likely a client bug than
    an intentional no-op call."""

    model_config = ConfigDict(extra="forbid")

    EstimatedCost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    ActualCost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)

    @model_validator(mode="after")
    def require_at_least_one_cost(self) -> EnterCostsRequest:
        if self.EstimatedCost is None and self.ActualCost is None:
            raise ValueError("Provide EstimatedCost, ActualCost, or both.")
        return self


class CompleteRequest(BaseModel):
    """Request body for POST /api/maintenance-requests/{id}/complete.
    ResolutionNotes is required here (not just optional-with-a-DB-check) so
    the client gets a clear 422 instead of discovering the rule via a 500
    from the database CHECK constraint."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    CompletedDate: date | None = Field(default=None, description="Defaults to today if omitted.")
    ResolutionNotes: str = Field(min_length=1, max_length=2000)
    ActualCost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)


class CancelRequest(BaseModel):
    """Notes here is optional and, if given, is stored in ResolutionNotes
    as the cancellation reason - MaintenanceRequests has no separate
    "cancellation notes" column, and ResolutionNotes is otherwise unused
    for a cancelled request (the DB CHECK constraint only requires it for
    Completed)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    Notes: str | None = Field(default=None, max_length=2000)


class MaintenanceNoteResponse(BaseModel):
    MaintenanceNoteId: int
    MaintenanceRequestId: int
    EmployeeId: int
    EmployeeName: str
    NoteText: str
    CreatedAt: datetime

    @classmethod
    def from_note(cls, note) -> MaintenanceNoteResponse:
        return cls(
            MaintenanceNoteId=note.MaintenanceNoteId,
            MaintenanceRequestId=note.MaintenanceRequestId,
            EmployeeId=note.EmployeeId,
            EmployeeName=f"{note.Employee.FirstName} {note.Employee.LastName}",
            NoteText=note.NoteText,
            CreatedAt=note.CreatedAt,
        )


class MaintenanceRequestResponse(BaseModel):
    """Not built via from_attributes=True: PropertyReference/AgreementReference/
    TenantName/AssignedEmployeeName need relationship traversal, and
    IsEmergency is derived from Priority rather than stored, so a request
    is unambiguously flagged regardless of how a client filters/sorts (see
    the scope doc's "Emergency requests must be easy to identify")."""

    MaintenanceRequestId: int
    PropertyId: int
    PropertyReference: str
    TenancyId: int | None
    AgreementReference: str | None
    TenantId: int | None
    TenantName: str | None
    AssignedEmployeeId: int | None
    AssignedEmployeeName: str | None
    RequestReference: str
    Title: str
    Description: str | None
    Category: str
    Priority: str
    IsEmergency: bool
    MaintenanceStatus: str
    ReportedDate: date
    ScheduledDate: date | None
    CompletedDate: date | None
    EstimatedCost: Decimal | None
    ActualCost: Decimal | None
    ResolutionNotes: str | None
    Notes: list[MaintenanceNoteResponse]
    CreatedAt: datetime
    UpdatedAt: datetime

    @classmethod
    def from_request(cls, request) -> MaintenanceRequestResponse:
        return cls(
            MaintenanceRequestId=request.MaintenanceRequestId,
            PropertyId=request.PropertyId,
            PropertyReference=request.Property.PropertyReference,
            TenancyId=request.TenancyId,
            AgreementReference=request.Tenancy.AgreementReference if request.Tenancy else None,
            TenantId=request.TenantId,
            TenantName=f"{request.Tenant.FirstName} {request.Tenant.LastName}" if request.Tenant else None,
            AssignedEmployeeId=request.AssignedEmployeeId,
            AssignedEmployeeName=(
                f"{request.AssignedEmployee.FirstName} {request.AssignedEmployee.LastName}" if request.AssignedEmployee else None
            ),
            RequestReference=request.RequestReference,
            Title=request.Title,
            Description=request.Description,
            Category=request.Category,
            Priority=request.Priority,
            IsEmergency=request.Priority == "Emergency",
            MaintenanceStatus=request.MaintenanceStatus,
            ReportedDate=request.ReportedDate,
            ScheduledDate=request.ScheduledDate,
            CompletedDate=request.CompletedDate,
            EstimatedCost=request.EstimatedCost,
            ActualCost=request.ActualCost,
            ResolutionNotes=request.ResolutionNotes,
            Notes=[MaintenanceNoteResponse.from_note(n) for n in sorted(request.MaintenanceNotes, key=lambda n: n.CreatedAt)],
            CreatedAt=request.CreatedAt,
            UpdatedAt=request.UpdatedAt,
        )


class MaintenanceRequestListItem(BaseModel):
    """Lighter-weight representation used in list results - no notes,
    no full description."""

    MaintenanceRequestId: int
    RequestReference: str
    PropertyReference: str
    Title: str
    Category: str
    Priority: str
    IsEmergency: bool
    MaintenanceStatus: str
    AssignedEmployeeId: int | None
    AssignedEmployeeName: str | None
    ReportedDate: date
    ScheduledDate: date | None

    @classmethod
    def from_request(cls, request) -> MaintenanceRequestListItem:
        return cls(
            MaintenanceRequestId=request.MaintenanceRequestId,
            RequestReference=request.RequestReference,
            PropertyReference=request.Property.PropertyReference,
            Title=request.Title,
            Category=request.Category,
            Priority=request.Priority,
            IsEmergency=request.Priority == "Emergency",
            MaintenanceStatus=request.MaintenanceStatus,
            AssignedEmployeeId=request.AssignedEmployeeId,
            AssignedEmployeeName=(
                f"{request.AssignedEmployee.FirstName} {request.AssignedEmployee.LastName}" if request.AssignedEmployee else None
            ),
            ReportedDate=request.ReportedDate,
            ScheduledDate=request.ScheduledDate,
        )


MaintenanceRequestListResponse = PaginatedResponse[MaintenanceRequestListItem]


class EmployeeWorkloadItem(BaseModel):
    """One row per employee who currently has at least one open (not
    Completed/Cancelled) request assigned - used by GET
    /api/maintenance-requests/workload to answer "who's busy, and with
    what" without loading every request's full detail."""

    EmployeeId: int
    EmployeeName: str
    IsActive: bool
    OpenRequestCount: int
    EmergencyOpenCount: int


EmployeeWorkloadResponse = list[EmployeeWorkloadItem]
