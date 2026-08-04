"""Business rules for the Tenant module. Same shape as LandlordService -
see that file for the full request-flow explanation.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.tenant import Tenant
from app.repositories.tenant_repository import TenantRepository
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.utilities.datetime_utils import utc_now


class TenantService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TenantRepository(db)

    def list_tenants(
        self, *, page: int, page_size: int, search: str | None, is_active: bool | None
    ) -> tuple[Sequence[Tenant], int]:
        return self.repository.list(page=page, page_size=page_size, search=search, is_active=is_active)

    def get_tenant(self, tenant_id: int) -> Tenant:
        tenant = self.repository.get_by_id(tenant_id)
        if tenant is None:
            raise AppError("TENANT_NOT_FOUND", f"No tenant found with id {tenant_id}.", status_code=404)
        return tenant

    def create_tenant(self, data: TenantCreate) -> Tenant:
        self._ensure_email_not_taken(data.Email, exclude_tenant_id=None)

        tenant = Tenant(**data.model_dump(), IsActive=True)
        self.repository.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def update_tenant(self, tenant_id: int, data: TenantUpdate) -> Tenant:
        tenant = self.get_tenant(tenant_id)
        self._ensure_email_not_taken(data.Email, exclude_tenant_id=tenant_id)

        for field, value in data.model_dump().items():
            setattr(tenant, field, value)
        tenant.UpdatedAt = utc_now()

        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def set_active_status(self, tenant_id: int, is_active: bool) -> Tenant:
        tenant = self.get_tenant(tenant_id)
        tenant.IsActive = is_active
        tenant.UpdatedAt = utc_now()

        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def deactivate_tenant(self, tenant_id: int) -> Tenant:
        """Handles DELETE /api/tenants/{id}. Same soft-delete-only
        philosophy as LandlordService.deactivate_landlord."""
        tenant = self.get_tenant(tenant_id)

        if self.repository.has_active_tenancies(tenant_id):
            raise AppError(
                "TENANT_HAS_ACTIVE_TENANCY",
                "This tenant has an active, upcoming, or draft tenancy and cannot be deleted. "
                "End or cancel the tenancy first.",
                status_code=409,
            )

        tenant.IsActive = False
        tenant.UpdatedAt = utc_now()
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def _ensure_email_not_taken(self, email: str | None, *, exclude_tenant_id: int | None) -> None:
        if not email:
            return
        existing = self.repository.get_by_email(email)
        if existing is not None and existing.TenantId != exclude_tenant_id:
            raise AppError(
                "DUPLICATE_EMAIL",
                f"A tenant with the email '{email}' already exists.",
                status_code=409,
            )
