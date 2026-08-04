"""Business rules for the Tenancy module - the module with the strongest
validation requirements in the MVP.

Transaction handling when tenancy and property records change together:

Activating, ending, or cancelling a tenancy can also change the linked
property's status (Vacant <-> Occupied) and always writes an audit log
entry. All three changes - the tenancy row, the property row, and the
audit log row - are made against the SAME SQLAlchemy Session, and are only
sent to SQL Server by the ONE db.commit() call at the end of each method.
SQLAlchemy's Session already IS a transaction: nothing is durably written
until commit() runs, no matter how many objects were added or mutated
first. Every validation (status checks, active-property/tenant checks,
the overlap check) happens BEFORE any attribute is touched, so a rejected
request never stages a partial change in the first place; and if
something unexpected failed between staging the changes and commit(), none
of it would reach the database. A property can never end up marked
Occupied by a tenancy that failed to activate, because both changes live
in one atomic unit of work with a single commit point.

Two things this module deliberately does NOT do yet, both flagged as
future/scheduled work rather than silently missing:

- An Upcoming tenancy does not automatically flip to Active (and its
  property to Occupied) the day its StartDate arrives - and an Active
  tenancy does not automatically flip to "Ending Soon" as its EndDate
  approaches. Both would need a scheduled sweep job (the same category of
  future work as RentPayments' Pending -> Overdue transition).
- Overlap prevention only runs at ACTIVATION, not at Draft creation or
  editing. Multiple Draft tenancies covering the same dates on the same
  property are allowed to coexist (e.g. comparing two prospective
  tenants) - the conflict only matters once one of them is about to
  become real.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.property import Property
from app.models.tenancy import Tenancy
from app.models.tenant import Tenant
from app.repositories.property_repository import PropertyRepository
from app.repositories.tenancy_repository import TenancyRepository
from app.repositories.tenant_repository import TenantRepository
from app.schemas.tenancy import TenancyCreate, TenancyUpdate
from app.services.audit_service import AuditService
from app.utilities.datetime_utils import utc_now


class TenancyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TenancyRepository(db)
        self.property_repository = PropertyRepository(db)
        self.tenant_repository = TenantRepository(db)
        self.audit_service = AuditService(db)

    def list_tenancies(
        self, *, page: int, page_size: int, property_id: int | None, tenant_id: int | None, tenancy_status: str | None
    ) -> tuple[Sequence[Tenancy], int]:
        return self.repository.list(
            page=page, page_size=page_size, property_id=property_id, tenant_id=tenant_id, tenancy_status=tenancy_status
        )

    def list_expiring(self, *, days: int) -> Sequence[Tenancy]:
        return self.repository.list_expiring(days=days)

    def get_tenancy(self, tenancy_id: int) -> Tenancy:
        tenancy = self.repository.get_by_id(tenancy_id)
        if tenancy is None:
            raise AppError("TENANCY_NOT_FOUND", f"No tenancy found with id {tenancy_id}.", status_code=404)
        return tenancy

    def create_draft_tenancy(self, data: TenancyCreate, *, user_id: int) -> Tenancy:
        # Existence only here, not "must be active" - a Draft is just a
        # proposal and doesn't commit the property or tenant to anything
        # yet. "Must be active" is enforced at activation instead, below.
        self._get_property_or_404(data.PropertyId)
        self._get_tenant_or_404(data.TenantId)
        self._ensure_agreement_reference_not_taken(data.AgreementReference, exclude_tenancy_id=None)

        tenancy = Tenancy(**data.model_dump(), TenancyStatus="Draft")
        self.repository.add(tenancy)

        self.audit_service.log(
            user_id=user_id,
            action="CREATE",
            entity_name="Tenancy",
            entity_id=tenancy.TenancyId,
            new_values={
                "PropertyId": tenancy.PropertyId,
                "TenantId": tenancy.TenantId,
                "StartDate": tenancy.StartDate,
                "EndDate": tenancy.EndDate,
                "TenancyStatus": tenancy.TenancyStatus,
            },
        )

        self.db.commit()
        self.db.refresh(tenancy)
        return tenancy

    def update_tenancy(self, tenancy_id: int, data: TenancyUpdate, *, user_id: int) -> Tenancy:
        tenancy = self.get_tenancy(tenancy_id)
        if tenancy.TenancyStatus != "Draft":
            raise AppError(
                "TENANCY_NOT_EDITABLE",
                "Only a Draft tenancy can be edited directly. Activate, end, or cancel it instead.",
                status_code=409,
            )

        self._get_property_or_404(data.PropertyId)
        self._get_tenant_or_404(data.TenantId)
        self._ensure_agreement_reference_not_taken(data.AgreementReference, exclude_tenancy_id=tenancy_id)

        old_values = {
            "PropertyId": tenancy.PropertyId,
            "TenantId": tenancy.TenantId,
            "StartDate": tenancy.StartDate,
            "EndDate": tenancy.EndDate,
            "MonthlyRent": tenancy.MonthlyRent,
        }
        for field, value in data.model_dump().items():
            setattr(tenancy, field, value)
        tenancy.UpdatedAt = utc_now()

        self.audit_service.log(
            user_id=user_id,
            action="UPDATE",
            entity_name="Tenancy",
            entity_id=tenancy.TenancyId,
            old_values=old_values,
            new_values={
                "PropertyId": tenancy.PropertyId,
                "TenantId": tenancy.TenantId,
                "StartDate": tenancy.StartDate,
                "EndDate": tenancy.EndDate,
                "MonthlyRent": tenancy.MonthlyRent,
            },
        )

        self.db.commit()
        self.db.refresh(tenancy)
        return tenancy

    def activate_tenancy(self, tenancy_id: int, *, user_id: int) -> Tenancy:
        tenancy = self.get_tenancy(tenancy_id)
        if tenancy.TenancyStatus != "Draft":
            raise AppError("TENANCY_NOT_DRAFT", "Only a Draft tenancy can be activated.", status_code=409)

        property_ = self._get_active_property_or_error(tenancy.PropertyId)
        self._get_active_tenant_or_error(tenancy.TenantId)

        overlap = self.repository.find_overlapping_tenancy(
            property_id=tenancy.PropertyId,
            exclude_tenancy_id=tenancy.TenancyId,
            start_date=tenancy.StartDate,
            end_date=tenancy.EndDate,
        )
        if overlap is not None:
            raise AppError(
                "TENANCY_DATE_CONFLICT",
                "This property already has a tenancy covering those dates.",
                status_code=409,
                details={"conflicting_tenancy_id": overlap.TenancyId},
            )

        old_status = tenancy.TenancyStatus
        starts_now_or_earlier = tenancy.StartDate <= date.today()
        tenancy.TenancyStatus = "Active" if starts_now_or_earlier else "Upcoming"
        tenancy.UpdatedAt = utc_now()

        if starts_now_or_earlier:
            tenancy.CheckInDate = tenancy.StartDate
            property_.PropertyStatus = "Occupied"
            property_.UpdatedAt = utc_now()

        self.audit_service.log(
            user_id=user_id,
            action="ACTIVATE",
            entity_name="Tenancy",
            entity_id=tenancy.TenancyId,
            old_values={"TenancyStatus": old_status},
            new_values={"TenancyStatus": tenancy.TenancyStatus},
        )

        self.db.commit()
        self.db.refresh(tenancy)
        return tenancy

    def end_tenancy(self, tenancy_id: int, *, end_date: date | None, user_id: int) -> Tenancy:
        tenancy = self.get_tenancy(tenancy_id)
        if tenancy.TenancyStatus not in ("Active", "Ending Soon"):
            raise AppError("TENANCY_NOT_ACTIVE", "Only an Active tenancy can be ended.", status_code=409)

        actual_end_date = end_date or date.today()
        # Mirrors CK_Tenancies_DateOrder (EndDate must be strictly after
        # StartDate). Caught here deliberately, before it ever reaches SQL
        # Server: a tenancy that started today and is ended "today" (the
        # default when no end_date is given) would otherwise hit the
        # database's CHECK constraint at commit time and surface as a raw
        # 500 error instead of a clear, actionable 409.
        if actual_end_date <= tenancy.StartDate:
            raise AppError(
                "TENANCY_INVALID_END_DATE",
                "The end date must be after the tenancy's start date.",
                status_code=409,
            )

        old_status = tenancy.TenancyStatus
        tenancy.TenancyStatus = "Ended"
        tenancy.EndDate = actual_end_date
        tenancy.CheckOutDate = actual_end_date
        tenancy.UpdatedAt = utc_now()

        # Vacate the property UNLESS another tenancy is already lined up for
        # it (an Upcoming or Active tenancy that isn't this one) - matches
        # "ending a tenancy should update the property to Vacant unless
        # another tenancy begins immediately" from the scope doc.
        property_ = self.property_repository.get_by_id(tenancy.PropertyId)
        if not self.repository.has_other_live_tenancy(property_id=tenancy.PropertyId, exclude_tenancy_id=tenancy.TenancyId):
            property_.PropertyStatus = "Vacant"
            property_.UpdatedAt = utc_now()

        self.audit_service.log(
            user_id=user_id,
            action="END",
            entity_name="Tenancy",
            entity_id=tenancy.TenancyId,
            old_values={"TenancyStatus": old_status},
            new_values={"TenancyStatus": "Ended", "EndDate": actual_end_date},
        )

        self.db.commit()
        self.db.refresh(tenancy)
        return tenancy

    def cancel_tenancy(self, tenancy_id: int, *, user_id: int) -> Tenancy:
        tenancy = self.get_tenancy(tenancy_id)
        if tenancy.TenancyStatus in ("Ended", "Cancelled"):
            raise AppError("TENANCY_ALREADY_FINAL", "This tenancy has already ended or been cancelled.", status_code=409)

        was_occupying_property = tenancy.TenancyStatus == "Active"
        old_status = tenancy.TenancyStatus
        tenancy.TenancyStatus = "Cancelled"
        tenancy.UpdatedAt = utc_now()

        if was_occupying_property:
            property_ = self.property_repository.get_by_id(tenancy.PropertyId)
            if not self.repository.has_other_live_tenancy(
                property_id=tenancy.PropertyId, exclude_tenancy_id=tenancy.TenancyId
            ):
                property_.PropertyStatus = "Vacant"
                property_.UpdatedAt = utc_now()

        self.audit_service.log(
            user_id=user_id,
            action="CANCEL",
            entity_name="Tenancy",
            entity_id=tenancy.TenancyId,
            old_values={"TenancyStatus": old_status},
            new_values={"TenancyStatus": "Cancelled"},
        )

        self.db.commit()
        self.db.refresh(tenancy)
        return tenancy

    def _get_property_or_404(self, property_id: int) -> Property:
        property_ = self.property_repository.get_by_id(property_id)
        if property_ is None:
            raise AppError("PROPERTY_NOT_FOUND", f"No property found with id {property_id}.", status_code=404)
        return property_

    def _get_tenant_or_404(self, tenant_id: int) -> Tenant:
        tenant = self.tenant_repository.get_by_id(tenant_id)
        if tenant is None:
            raise AppError("TENANT_NOT_FOUND", f"No tenant found with id {tenant_id}.", status_code=404)
        return tenant

    def _get_active_property_or_error(self, property_id: int) -> Property:
        property_ = self._get_property_or_404(property_id)
        if not property_.IsActive:
            raise AppError(
                "PROPERTY_INACTIVE", "This property is inactive and cannot be assigned an active tenancy.", status_code=409
            )
        return property_

    def _get_active_tenant_or_error(self, tenant_id: int) -> Tenant:
        tenant = self._get_tenant_or_404(tenant_id)
        if not tenant.IsActive:
            raise AppError(
                "TENANT_INACTIVE", "This tenant is inactive and cannot be assigned an active tenancy.", status_code=409
            )
        return tenant

    def _ensure_agreement_reference_not_taken(self, reference: str | None, *, exclude_tenancy_id: int | None) -> None:
        if not reference:
            return
        existing = self.repository.get_by_agreement_reference(reference)
        if existing is not None and existing.TenancyId != exclude_tenancy_id:
            raise AppError(
                "DUPLICATE_AGREEMENT_REFERENCE",
                f"A tenancy with agreement reference '{reference}' already exists.",
                status_code=409,
            )
