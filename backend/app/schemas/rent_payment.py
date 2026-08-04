"""Pydantic schemas for the RentPayment module.

Same Create/Update split as previous modules, plus two dedicated action
schemas (RecordPaymentRequest, CancelPaymentRequest) instead of a generic
status-PATCH - same reasoning as Tenancy: which transitions are legal
depends on current state, so a free "set any status" endpoint would let a
client mark a payment Paid without ever recording an actual payment.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse

PaymentMethodValue = Literal["Bank Transfer", "Card", "Cash", "Direct Debit", "Standing Order", "Other"]
PaymentStatusValue = Literal["Pending", "Partially Paid", "Paid", "Overdue", "Cancelled"]


class RentPaymentCreate(BaseModel):
    """Request body for POST /api/rent-payments - creates a rent
    obligation. AmountPaid always starts at 0 and PaymentStatus is always
    computed (Pending or, if DueDate is already in the past, Overdue) -
    neither is client-settable; money is only ever recorded via the
    dedicated POST /{id}/record-payment action.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    TenancyId: int
    PaymentReference: str = Field(min_length=1, max_length=30)
    DueDate: date
    AmountDue: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    ExternalReference: str | None = Field(default=None, max_length=100)
    Notes: str | None = Field(default=None, max_length=1000)


class RentPaymentUpdate(RentPaymentCreate):
    """Request body for PUT /api/rent-payments/{id} - only permitted while
    AmountPaid is still 0 (see RentPaymentService.update_payment). Once any
    money has been recorded, correcting the obligation itself is no longer
    just an edit - cancel it and create a new one instead."""


class RecordPaymentRequest(BaseModel):
    """Request body for POST /api/rent-payments/{id}/record-payment.

    AmountPaid here is the amount being paid NOW, not a new running total -
    it's ADDED to whatever has already been recorded, so multiple partial
    payments accumulate correctly toward AmountDue. See
    RentPaymentService.record_payment.
    """

    model_config = ConfigDict(extra="forbid")

    AmountPaid: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    PaymentDate: date | None = None
    PaymentMethod: PaymentMethodValue
    Notes: str | None = Field(default=None, max_length=1000)


class CancelPaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    Notes: str | None = Field(default=None, max_length=1000)


class RentPaymentResponse(BaseModel):
    """Not built via from_attributes=True: PropertyReference/TenantName
    need relationship traversal (payment.Tenancy.Property /
    payment.Tenancy.Tenant), and PaymentStatus is recalculated live rather
    than trusted from the stored column - see
    RentPaymentService.calculate_payment_status's docstring for why."""

    RentPaymentId: int
    TenancyId: int
    AgreementReference: str | None
    PropertyReference: str
    TenantName: str
    PaymentReference: str
    DueDate: date
    AmountDue: Decimal
    AmountPaid: Decimal
    AmountOutstanding: Decimal
    PaymentDate: date | None
    PaymentMethod: str | None
    PaymentStatus: str
    ExternalReference: str | None
    Notes: str | None
    CreatedByEmployeeId: int | None
    CreatedAt: datetime
    UpdatedAt: datetime

    @classmethod
    def from_payment(cls, payment, *, live_status: str) -> RentPaymentResponse:
        return cls(
            RentPaymentId=payment.RentPaymentId,
            TenancyId=payment.TenancyId,
            AgreementReference=payment.Tenancy.AgreementReference,
            PropertyReference=payment.Tenancy.Property.PropertyReference,
            TenantName=f"{payment.Tenancy.Tenant.FirstName} {payment.Tenancy.Tenant.LastName}",
            PaymentReference=payment.PaymentReference,
            DueDate=payment.DueDate,
            AmountDue=payment.AmountDue,
            AmountPaid=payment.AmountPaid,
            AmountOutstanding=payment.AmountDue - payment.AmountPaid,
            PaymentDate=payment.PaymentDate,
            PaymentMethod=payment.PaymentMethod,
            PaymentStatus=live_status,
            ExternalReference=payment.ExternalReference,
            Notes=payment.Notes,
            CreatedByEmployeeId=payment.CreatedByEmployeeId,
            CreatedAt=payment.CreatedAt,
            UpdatedAt=payment.UpdatedAt,
        )


class RentPaymentListItem(BaseModel):
    """Lighter-weight representation used in list results."""

    RentPaymentId: int
    PropertyReference: str
    TenantName: str
    PaymentReference: str
    DueDate: date
    AmountDue: Decimal
    AmountPaid: Decimal
    AmountOutstanding: Decimal
    PaymentStatus: str

    @classmethod
    def from_payment(cls, payment, *, live_status: str) -> RentPaymentListItem:
        return cls(
            RentPaymentId=payment.RentPaymentId,
            PropertyReference=payment.Tenancy.Property.PropertyReference,
            TenantName=f"{payment.Tenancy.Tenant.FirstName} {payment.Tenancy.Tenant.LastName}",
            PaymentReference=payment.PaymentReference,
            DueDate=payment.DueDate,
            AmountDue=payment.AmountDue,
            AmountPaid=payment.AmountPaid,
            AmountOutstanding=payment.AmountDue - payment.AmountPaid,
            PaymentStatus=live_status,
        )


RentPaymentListResponse = PaginatedResponse[RentPaymentListItem]
