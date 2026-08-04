"""Pydantic schemas for the Tenancy module.

Unlike Landlord/Property/Tenant, there is no TenancyStatusUpdate schema -
status only ever changes through the dedicated activate/end/cancel actions
(POST /api/tenancies/{id}/activate, /end, /cancel), never a generic PATCH.
A tenancy's status is a lifecycle, not a free toggle: which transitions are
even legal depends on the current status (see TenancyService), so a single
"set any status" endpoint would let a client skip straight from Draft to
Ended, which shouldn't be possible.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import PaginatedResponse

TenancyStatusValue = Literal["Draft", "Upcoming", "Active", "Ending Soon", "Ended", "Cancelled"]


class TenancyCreate(BaseModel):
    """Request body for POST /api/tenancies - always creates a Draft."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    PropertyId: int
    TenantId: int
    StartDate: date
    EndDate: date | None = None
    # Tenancies require MonthlyRent strictly > 0 (CK_Tenancies_MonthlyRent)
    # - unlike Properties, where 0 is allowed for a not-yet-priced listing.
    MonthlyRent: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    DepositAmount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)
    PaymentDueDay: int = Field(ge=1, le=28)
    AgreementReference: str | None = Field(default=None, max_length=30)
    Notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_date_order(self) -> TenancyCreate:
        # Mirrors CK_Tenancies_DateOrder: EndDate IS NULL OR EndDate > StartDate.
        if self.EndDate is not None and self.EndDate <= self.StartDate:
            raise ValueError("End date must be after the start date.")
        return self


class TenancyUpdate(TenancyCreate):
    """Request body for PUT /api/tenancies/{id} - only permitted while the
    tenancy is still Draft. See TenancyService.update_tenancy."""


class TenancyEndRequest(BaseModel):
    """Request body for POST /api/tenancies/{id}/end.

    EndDate is optional: it's the actual move-out date, which may differ
    from the tenancy's originally planned EndDate (e.g. a tenant leaves
    early, or a periodic tenancy with no planned end date finally
    concludes). Omitting it defaults to today - see TenancyService.end_tenancy.
    """

    model_config = ConfigDict(extra="forbid")

    EndDate: date | None = None


class TenancyResponse(BaseModel):
    """Not built via from_attributes=True: PropertyReference and TenantName
    come from relationship traversal (tenancy.Property / tenancy.Tenant),
    which needs the same explicit-reshaping approach as
    CurrentUserResponse.from_user - see schemas/auth.py."""

    TenancyId: int
    PropertyId: int
    PropertyReference: str
    TenantId: int
    TenantName: str
    StartDate: date
    EndDate: date | None
    MonthlyRent: Decimal
    DepositAmount: Decimal
    PaymentDueDay: int
    TenancyStatus: str
    CheckInDate: date | None
    CheckOutDate: date | None
    AgreementReference: str | None
    Notes: str | None
    CreatedAt: datetime
    UpdatedAt: datetime

    @classmethod
    def from_tenancy(cls, tenancy) -> TenancyResponse:
        return cls(
            TenancyId=tenancy.TenancyId,
            PropertyId=tenancy.PropertyId,
            PropertyReference=tenancy.Property.PropertyReference,
            TenantId=tenancy.TenantId,
            TenantName=f"{tenancy.Tenant.FirstName} {tenancy.Tenant.LastName}",
            StartDate=tenancy.StartDate,
            EndDate=tenancy.EndDate,
            MonthlyRent=tenancy.MonthlyRent,
            DepositAmount=tenancy.DepositAmount,
            PaymentDueDay=tenancy.PaymentDueDay,
            TenancyStatus=tenancy.TenancyStatus,
            CheckInDate=tenancy.CheckInDate,
            CheckOutDate=tenancy.CheckOutDate,
            AgreementReference=tenancy.AgreementReference,
            Notes=tenancy.Notes,
            CreatedAt=tenancy.CreatedAt,
            UpdatedAt=tenancy.UpdatedAt,
        )


class TenancyListItem(BaseModel):
    """Lighter-weight representation used in list results."""

    TenancyId: int
    PropertyReference: str
    TenantName: str
    StartDate: date
    EndDate: date | None
    MonthlyRent: Decimal
    TenancyStatus: str

    @classmethod
    def from_tenancy(cls, tenancy) -> TenancyListItem:
        return cls(
            TenancyId=tenancy.TenancyId,
            PropertyReference=tenancy.Property.PropertyReference,
            TenantName=f"{tenancy.Tenant.FirstName} {tenancy.Tenant.LastName}",
            StartDate=tenancy.StartDate,
            EndDate=tenancy.EndDate,
            MonthlyRent=tenancy.MonthlyRent,
            TenancyStatus=tenancy.TenancyStatus,
        )


TenancyListResponse = PaginatedResponse[TenancyListItem]
