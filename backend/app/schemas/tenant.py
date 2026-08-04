"""Pydantic schemas for the Tenant module.

Same Create/Update/Response split as Landlord and Property - see
schemas/landlord.py for the full reasoning.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.common import PaginatedResponse

# Named EmploymentStatusValue, not EmploymentStatus: see schemas/property.py
# for why a module-level type alias must never share a name with a class
# field below it (a real Python 3.14 bug hit while building schemas/landlord.py).
EmploymentStatusValue = Literal["Employed", "Self-Employed", "Unemployed", "Student", "Retired", "Other"]


class TenantWriteBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    FirstName: str = Field(min_length=1, max_length=50)
    LastName: str = Field(min_length=1, max_length=50)
    Email: EmailStr | None = Field(default=None, max_length=256)
    Phone: str | None = Field(default=None, max_length=30)
    DateOfBirth: date | None = None
    PreviousAddress: str | None = Field(default=None, max_length=250)
    EmergencyContactName: str | None = Field(default=None, max_length=100)
    EmergencyContactPhone: str | None = Field(default=None, max_length=30)
    IdentificationReference: str | None = Field(default=None, max_length=50)
    EmploymentStatus: EmploymentStatusValue | None = None
    Notes: str | None = Field(default=None, max_length=1000)

    @field_validator("DateOfBirth")
    @classmethod
    def date_of_birth_not_in_future(cls, value: date | None) -> date | None:
        # This is exactly the check that CANNOT live in a SQL Server CHECK
        # constraint (no non-deterministic functions like GETDATE() allowed
        # there) - see database-design.md, section 0. Pydantic is where it
        # has to live instead.
        if value is not None and value > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return value


class TenantCreate(TenantWriteBase):
    """Request body for POST /api/tenants."""


class TenantUpdate(TenantWriteBase):
    """Request body for PUT /api/tenants/{id} - a full replace of the
    editable fields, same convention as LandlordUpdate/PropertyUpdate."""


class TenantStatusUpdate(BaseModel):
    """Request body for PATCH /api/tenants/{id}/status."""

    model_config = ConfigDict(extra="forbid")

    IsActive: bool


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    TenantId: int
    FirstName: str
    LastName: str
    Email: str | None
    Phone: str | None
    DateOfBirth: date | None
    PreviousAddress: str | None
    EmergencyContactName: str | None
    EmergencyContactPhone: str | None
    IdentificationReference: str | None
    EmploymentStatus: str | None
    Notes: str | None
    IsActive: bool
    CreatedAt: datetime
    UpdatedAt: datetime


class TenantListItem(BaseModel):
    """Lighter-weight representation used in GET /api/tenants list results."""

    model_config = ConfigDict(from_attributes=True)

    TenantId: int
    FirstName: str
    LastName: str
    Email: str | None
    Phone: str | None
    IsActive: bool


TenantListResponse = PaginatedResponse[TenantListItem]
