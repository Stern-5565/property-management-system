"""Pydantic schemas for the Employee module.

Same Create/Update/Response split as Landlord/Property/Tenant - see
schemas/landlord.py for the full reasoning. Role assignment (RoleName in
the scope doc's "suggested fields" list, section 5.7) isn't a field here:
the actual schema puts roles on Users/UserRoles (many-to-many, see
auth_service.py), not on Employees directly, so an Employee row alone
never carries a role - that's a Users-module concern, not built yet (see
documentation/progress-log.md's "Next steps").
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.common import PaginatedResponse


class EmployeeWriteBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    FirstName: str = Field(min_length=1, max_length=50)
    LastName: str = Field(min_length=1, max_length=50)
    Email: EmailStr = Field(max_length=256)
    Phone: str | None = Field(default=None, max_length=30)
    JobTitle: str | None = Field(default=None, max_length=100)
    Department: str | None = Field(default=None, max_length=100)
    HireDate: date

    @field_validator("HireDate")
    @classmethod
    def hire_date_not_in_future(cls, value: date) -> date:
        # Same reasoning as TenantWriteBase.date_of_birth_not_in_future:
        # this can't live in a SQL Server CHECK constraint (no GETDATE()
        # allowed there), so Pydantic is where it has to live instead.
        if value > date.today():
            raise ValueError("Hire date cannot be in the future.")
        return value


class EmployeeCreate(EmployeeWriteBase):
    """Request body for POST /api/employees."""


class EmployeeUpdate(EmployeeWriteBase):
    """Request body for PUT /api/employees/{id} - a full replace of the
    editable fields, same convention as LandlordUpdate/TenantUpdate.
    Activating or deactivating is a separate action - see
    EmployeeStatusUpdate."""


class EmployeeStatusUpdate(BaseModel):
    """Request body for PATCH /api/employees/{id}/status."""

    model_config = ConfigDict(extra="forbid")

    IsActive: bool


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    EmployeeId: int
    FirstName: str
    LastName: str
    Email: str
    Phone: str | None
    JobTitle: str | None
    Department: str | None
    HireDate: date
    IsActive: bool
    CreatedAt: datetime
    UpdatedAt: datetime


class EmployeeListItem(BaseModel):
    """Lighter-weight representation used in GET /api/employees list results."""

    model_config = ConfigDict(from_attributes=True)

    EmployeeId: int
    FirstName: str
    LastName: str
    Email: str
    JobTitle: str | None
    Department: str | None
    IsActive: bool


EmployeeListResponse = PaginatedResponse[EmployeeListItem]
